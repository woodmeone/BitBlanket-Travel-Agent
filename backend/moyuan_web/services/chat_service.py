"""聊天编排门面（Facade），由流式、历史、健康三个 Mixin 组合而成。

Mixin 模式说明：
    Mixin 是一种通过多继承将功能"混入"类的方式。ChatService 继承了
    ChatStreamMixin（流式传输）、ChatHistoryMixin（历史持久化）、
    ChatHealthMixin（健康诊断），每个 Mixin 职责单一，组合后形成完整的
    聊天服务。好处是各 Mixin 可独立测试、独立演进，避免"上帝类"问题。

典型应用场景：
    用户在前端输入"帮我规划一个三亚5日游"，ChatService 接收请求后：
    1. 通过 ChatHistoryMixin 确保会话存在
    2. 通过 ChatStreamMixin 以 SSE 流式返回推理过程和最终回答
    3. 通过 ChatHealthMixin 记录本次请求的健康指标
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from threading import Lock
from typing import Any

from ..repositories.session_repository import SessionRepository
from .chat import ChatHealthMixin, ChatHistoryMixin, ChatStreamMixin

logger = logging.getLogger(__name__)


class ChatService(ChatStreamMixin, ChatHistoryMixin, ChatHealthMixin):
    """聊天应用服务门面，组合流式/历史/健康三个 Mixin 提供端到端聊天编排。

    通过多继承 Mixin 模式，将流式传输（SSE）、消息持久化、健康诊断三大
    职责分离到独立的 Mixin 类中，ChatService 本身只负责初始化和配置。
    """

    VALID_MODES = {"direct", "react", "plan"}  # 支持的聊天模式：direct=直接LLM、react=工具编排、plan=规划预览
    DEFAULT_HEALTH_WINDOW_MINUTES = 60  # 健康指标滑动窗口默认60分钟
    DEFAULT_SLO_THRESHOLDS = {  # SLO（Service Level Objective）默认阈值
        "timeout_rate": 0.1,   # 超时率超过10%则降级
        "failure_rate": 0.2,   # 失败率超过20%则降级
        "fallback_rate": 0.5,  # 降级回退率超过50%则降级
    }

    def __init__(self, repository: SessionRepository):
        """初始化聊天编排的依赖和运行时状态。

        Args:
            repository: 会话持久化仓库，负责会话的 CRUD 操作
        """
        self._repository = repository
        self._init_lock = asyncio.Lock()  # 异步锁，防止并发初始化（双重检查锁定模式）
        self._initialized = False

        # 以下为延迟初始化的运行时组件，在 initialize() 中赋值
        self._llm_adapter: Any = None       # LLM 适配器，封装模型配置和调用
        self._llm: Any = None               # 主聊天模型实例
        self._router_llm: Any = None        # 路由模型实例，用于意图识别和任务分发
        self._tools: list[Any] | None = None  # 旅行工具列表（如搜索酒店、查询天气等）
        self._memory_manager: Any = None    # 记忆管理器，维护对话上下文和摘要
        self._agent_runtime: Any = None     # Agent 运行时，编排工具调用和推理流程
        self._health_window_minutes = self._parse_int_env(  # 健康指标滑动窗口时长（分钟）
            "AGENT_HEALTH_WINDOW_MINUTES",
            self.DEFAULT_HEALTH_WINDOW_MINUTES,
            minimum=5,
        )
        self._slo_thresholds = {  # 从环境变量读取 SLO 阈值，未配置则使用默认值
            "timeout_rate": self._parse_float_env(
                "AGENT_SLO_TIMEOUT_RATE_THRESHOLD",
                self.DEFAULT_SLO_THRESHOLDS["timeout_rate"],
            ),
            "failure_rate": self._parse_float_env(
                "AGENT_SLO_FAILURE_RATE_THRESHOLD",
                self.DEFAULT_SLO_THRESHOLDS["failure_rate"],
            ),
            "fallback_rate": self._parse_float_env(
                "AGENT_SLO_FALLBACK_RATE_THRESHOLD",
                self.DEFAULT_SLO_THRESHOLDS["fallback_rate"],
            ),
        }
        self._health_metrics_lock = Lock()  # 线程锁，保护健康指标 deque 的并发写入
        self._health_metrics: deque[dict[str, Any]] = deque()  # 有界双端队列，存储最近窗口内的健康指标记录

    async def initialize(self) -> None:
        """【核心】延迟初始化 LLM 适配器、路由模型、工具注册表和记忆管理器。

        采用双重检查锁定（Double-Checked Locking）模式：
        1. 先快速检查 _initialized 标志（无锁），避免已初始化后的锁开销
        2. 获取异步锁后再次检查，防止并发场景下重复初始化

        应用场景：首次聊天请求时触发初始化，后续请求直接跳过。
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            from ..bootstrap import ensure_project_paths
            from ..config.runtime import get_llm_config_path
            from agent.travel_agent.graph import TRAVEL_AGENT_SYSTEM_PROMPT
            from agent.travel_agent.llm.langchain_adapter import create_from_yaml_config
            from agent.travel_agent.runtime import AgentRuntime
            from agent.travel_agent.tools.travel_tools import get_travel_tools
            from agent.travel_agent.graph.memory_integration import get_agent_memory_manager

            ensure_project_paths()  # 确保项目路径已注册到 sys.path

            config_path = get_llm_config_path()
            self._llm_adapter = create_from_yaml_config(config_path)  # 从 YAML 配置创建 LLM 适配器
            self._llm = self._llm_adapter.chat_model  # 主聊天模型
            router_cfg = os.getenv("AGENT_ROUTER_LLM_CONFIG", "").strip()  # 路由模型配置路径（可选）
            if router_cfg:
                try:
                    router_adapter = create_from_yaml_config(router_cfg)
                    self._router_llm = router_adapter.chat_model
                except Exception as exc:
                    logger.warning("Failed to initialize router llm from %s: %s", router_cfg, exc)
                    self._router_llm = self._llm  # 路由模型初始化失败时回退到主模型
            else:
                self._router_llm = self._llm  # 未配置路由模型时直接使用主模型
            self._tools = get_travel_tools()  # 注册旅行领域工具（酒店搜索、景点推荐等）
            self._memory_manager = get_agent_memory_manager(  # 初始化记忆管理器
                max_history=10,       # 最多保留10轮对话
                summary_threshold=20, # 超过20条消息时触发摘要压缩
            )
            self._agent_runtime = AgentRuntime(  # 【核心】创建 Agent 运行时，编排推理和工具调用
                llm=self._llm,
                tools=self._tools,
                system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
                memory_manager=self._memory_manager,
                routing_llm=self._router_llm,
            )
            self._initialized = True
            logger.info(
                "Chat runtime initialized with model=%s tools=%d",
                self._llm_adapter.config.get("name"),
                len(self._tools),
            )
