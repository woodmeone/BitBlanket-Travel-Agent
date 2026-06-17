"""
运行时数据源（Runtime Sources）

提供图执行（Graph Execution）和 Supervisor 执行的统一入口，
负责构建编译后的图、初始化状态、管理检查点（checkpoint）后端。

核心概念说明：
  - LangGraph 图（Graph）：由节点（node）和边（edge）组成的有向图，
    节点执行具体逻辑，边控制流转方向，是 Agent 的执行骨架
  - Checkpointer（检查点）：LangGraph 的状态持久化机制，
    支持在图执行过程中保存和恢复状态，实现断点续跑和对话记忆
  - Supervisor：监督者模式，协调多个子 Agent 的执行流程
  - Runnable：LangChain 的可运行对象接口，LLM 和工具都实现此接口

模块职责：
  1. 构建图运行源（GraphRuntimeSource）：编译图 + 初始状态 + 记忆管理器
  2. 构建计划预览源（PlanPreviewSource）：计划节点 + 初始状态 + 记忆管理器
  3. 管理检查点后端（SQLite / PostgreSQL / 内存）：创建、配置、释放
  4. 延迟导入图构建器和节点，避免循环依赖

旅行场景举例：
  用户问"成都3日游" → build_supervisor_streaming_source() 构建运行源
  → 编译图（含意图识别→策略选择→计划生成→工具执行→回答生成等节点）
  → 初始化状态（含用户消息、会话ID、系统提示词）
  → 创建检查点（保存对话状态，支持断点续跑）
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from config import server_config

# TYPE_CHECKING 分支：仅类型检查时导入，运行时不导入，避免循环依赖
# 这是 Python 类型提示的最佳实践：用 TYPE_CHECKING 守卫仅用于类型注解的导入
if TYPE_CHECKING:
    from .contracts import (
        SupervisorPlanPreviewRequest,  # Supervisor 计划预览请求
        SupervisorRunRequest,  # Supervisor 运行请求
        SupervisorRuntimeContext,  # Supervisor 运行时上下文
    )
    from langchain_core.runnables import Runnable  # LangChain 可运行对象接口
    from langchain_core.tools import Tool  # LangChain 工具基类
else:
    SupervisorPlanPreviewRequest = Any
    SupervisorRunRequest = Any
    SupervisorRuntimeContext = Any
    Runnable = Any
    Tool = Any

# 全局缓存的默认检查点实例及其签名，用于避免重复创建
_DEFAULT_CHECKPOINTER = None
_DEFAULT_CHECKPOINTER_SIGNATURE = None


@dataclass(slots=True)
class GraphRuntimeSource:
    """【核心】图运行源，携带一个编译后的图及其初始状态，供运行时执行使用。

    属性：
      agent: 编译后的 LangGraph 图（CompiledGraph），可直接调用 invoke/stream
      initial_state: 图的初始状态字典，包含用户消息、会话ID等
      memory_manager: 记忆管理器，负责对话历史的读写
    """

    agent: Any
    initial_state: dict[str, Any]
    memory_manager: Any


@dataclass(slots=True)
class PlanPreviewSource:
    """计划预览源，携带计划节点适配器和预览状态，供预览执行使用。

    与 GraphRuntimeSource 不同，PlanPreviewSource 使用独立的节点而非完整图，
    适用于仅预览计划而不执行工具的场景。

    属性：
      nodes: Agent 节点集合（AgentNodes 实例）
      initial_state: 初始状态字典
      memory_manager: 记忆管理器
    """

    nodes: AgentNodes
    initial_state: dict[str, Any]
    memory_manager: Any


@dataclass(frozen=True, slots=True)
class CheckpointerConfig:
    """标准化的检查点后端配置，运行时和运维脚本共用。

    属性：
      backend: 后端类型，"sqlite" 或 "postgres"
      target: 存储目标（SQLite 文件路径 或 PostgreSQL 连接字符串）
      max_checkpoints_per_thread_ns: 每个线程的最大检查点数量
      compaction_interval: 压缩间隔（每N个检查点执行一次压缩清理）
      pool_min: 连接池最小连接数（仅 PostgreSQL）
      pool_max: 连接池最大连接数（仅 PostgreSQL）
    """

    backend: str
    target: str
    max_checkpoints_per_thread_ns: int
    compaction_interval: int
    pool_min: int = 1
    pool_max: int = 5

    def signature(self) -> tuple[Any, ...]:
        """返回不可变的缓存键，用于判断配置是否变化。

        当配置签名与缓存的一致时，复用已有的检查点实例，
        避免重复创建数据库连接池等昂贵资源。
        """

        if self.backend == "postgres":
            return (
                self.backend,
                self.target,
                self.pool_min,
                self.pool_max,
                self.max_checkpoints_per_thread_ns,
                self.compaction_interval,
            )
        return (
            self.backend,
            self.target,
            self.max_checkpoints_per_thread_ns,
            self.compaction_interval,
        )


def build_travel_agent(*args, **kwargs):
    """延迟导入图构建器，避免模块循环依赖。

    图构建器依赖节点模块，节点模块又可能反向引用运行时源，
    延迟导入打破这个循环。
    """

    from .graph.builder import build_travel_agent as _build_travel_agent

    return _build_travel_agent(*args, **kwargs)


def get_agent_memory_manager(*, llm, **kwargs):
    """延迟导入记忆管理器工厂，保证可测试性和循环安全。"""

    from .graph.memory_integration import get_agent_memory_manager as _get_agent_memory_manager

    return _get_agent_memory_manager(llm=llm, **kwargs)


class AgentStateWithMemory:
    """延迟代理类，保留测试 monkeypatch 的入口。

    在测试中可以通过替换此类来注入模拟状态，
    而不需要修改实际的图构建逻辑。
    """

    @staticmethod
    def create(*args, **kwargs):
        from .graph.memory_integration import AgentStateWithMemory as _AgentStateWithMemory

        return _AgentStateWithMemory.create(*args, **kwargs)


class AgentNodes:
    """延迟代理类，保留测试 monkeypatch 的入口。

    与 AgentStateWithMemory 类似，延迟导入实际的 AgentNodes 类，
    允许测试中替换节点实现。
    """

    def __new__(cls, *args, **kwargs):
        from .graph.nodes import AgentNodes as _AgentNodes

        return _AgentNodes(*args, **kwargs)


def _default_system_prompt() -> str:
    """获取默认的系统提示词。"""
    from .graph.state import TRAVEL_AGENT_SYSTEM_PROMPT

    return TRAVEL_AGENT_SYSTEM_PROMPT


def _default_sqlite_checkpoint_path() -> str:
    """获取默认的 SQLite 检查点文件路径。

    路径位于项目根目录的 data/ 文件夹下。
    """
    return os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "data",
            "langgraph_checkpoints.sqlite3",
        )
    )


def _parse_positive_int(raw_value: Any, default: int, minimum: int = 1) -> int:
    """将原始值解析为正整数，解析失败或低于最小值时返回默认值。"""
    try:
        parsed = int(raw_value)
    except Exception:
        return default
    return parsed if parsed >= minimum else default


def _normalize_checkpoint_backend(raw_value: Any) -> str:
    """将原始值规范化为合法的检查点后端名称。

    仅接受 "sqlite" 或 "postgres"，其他值默认为 "sqlite"。
    """
    raw = str(raw_value or "").strip().lower()
    return raw if raw in {"sqlite", "postgres"} else "sqlite"


def _infer_checkpoint_backend(target: Any) -> str | None:
    """从连接字符串推断检查点后端类型。

    根据 DSN 前缀判断：
      - "postgresql://" 或 "postgresql+psycopg://" → "postgres"
      - "sqlite" → "sqlite"
      - 其他 → None（无法推断）
    """
    raw = str(target or "").strip().lower()
    if not raw:
        return None
    if raw.startswith("postgresql://") or raw.startswith("postgresql+psycopg://"):
        return "postgres"
    if raw.startswith("sqlite"):
        return "sqlite"
    return None


def _checkpoint_pool_sizes() -> tuple[int, int]:
    """从环境变量和服务器配置中解析数据库连接池大小。"""
    pool_min = _parse_positive_int(os.getenv("MOYUAN_DB_POOL_MIN", server_config.db_pool_min), 1)
    pool_max = _parse_positive_int(os.getenv("MOYUAN_DB_POOL_MAX", server_config.db_pool_max), 5)
    return pool_min, max(pool_min, pool_max)


def resolve_checkpointer_config(
    *,
    backend_override: str | None = None,  # 后端类型覆盖，如 "postgres"
    target_override: str | None = None,  # 存储目标覆盖，如文件路径或 DSN
    dsn_override: str | None = None,  # PostgreSQL 连接字符串覆盖
    max_checkpoints_override: int | None = None,  # 最大检查点数覆盖
    compaction_interval_override: int | None = None,  # 压缩间隔覆盖
    pool_min_override: int | None = None,  # 连接池最小连接数覆盖（仅 PostgreSQL）
    pool_max_override: int | None = None,  # 连接池最大连接数覆盖（仅 PostgreSQL）
) -> CheckpointerConfig:
    """【核心】从覆盖值和默认值中解析出一个标准化的检查点后端配置。

    配置优先级（从高到低）：
      1. 函数参数覆盖（*_override）
      2. 环境变量（AGENT_CHECKPOINT_*）
      3. 服务器配置（server_config）
      4. 内置默认值

    旅行场景举例：
      开发环境：使用 SQLite（默认），检查点保存在 data/ 目录
      生产环境：设置 AGENT_CHECKPOINT_BACKEND=postgres + AGENT_CHECKPOINT_DSN=postgresql://...
    """

    # 解析后端类型：优先使用显式覆盖，其次从 DSN 推断，再从目标推断，最后读环境变量
    backend_source = (
        backend_override
        or ("postgres" if dsn_override else None)
        or _infer_checkpoint_backend(target_override)
        or os.getenv("AGENT_CHECKPOINT_BACKEND", "sqlite")
    )
    backend = _normalize_checkpoint_backend(backend_source)
    max_checkpoints = _parse_positive_int(
        max_checkpoints_override
        if max_checkpoints_override is not None
        else os.getenv("AGENT_CHECKPOINT_MAX_PER_THREAD", "200"),
        200,  # 默认每个线程最多200个检查点
    )
    compaction_interval = _parse_positive_int(
        compaction_interval_override
        if compaction_interval_override is not None
        else os.getenv("AGENT_CHECKPOINT_COMPACTION_INTERVAL", "50"),
        50,  # 默认每50个检查点压缩一次
    )
    if backend == "postgres":
        # PostgreSQL 后端：需要连接字符串
        database_url = str(
            dsn_override
            or target_override
            or os.getenv("AGENT_CHECKPOINT_DSN")
            or os.getenv("MOYUAN_POSTGRES_DSN")
            or server_config.postgres_dsn
        ).strip()
        if not database_url:
            raise ValueError(
                "AGENT_CHECKPOINT_BACKEND=postgres requires AGENT_CHECKPOINT_DSN or database.postgres_dsn"
            )
        default_pool_min, default_pool_max = _checkpoint_pool_sizes()
        pool_min = _parse_positive_int(
            pool_min_override if pool_min_override is not None else default_pool_min,
            default_pool_min,
        )
        pool_max = _parse_positive_int(
            pool_max_override if pool_max_override is not None else default_pool_max,
            default_pool_max,
        )
        return CheckpointerConfig(
            backend="postgres",
            target=database_url,
            pool_min=pool_min,
            pool_max=max(pool_min, pool_max),
            max_checkpoints_per_thread_ns=max_checkpoints,
            compaction_interval=compaction_interval,
        )

    # SQLite 后端：使用文件路径
    db_path = os.path.abspath(str(target_override or os.getenv("AGENT_CHECKPOINT_DB", _default_sqlite_checkpoint_path())))
    return CheckpointerConfig(
        backend="sqlite",
        target=db_path,
        max_checkpoints_per_thread_ns=max_checkpoints,
        compaction_interval=compaction_interval,
    )


def create_checkpointer(config: CheckpointerConfig) -> Any:
    """【核心】根据标准化配置构建一个检查点实例。

    根据后端类型选择不同的持久化实现：
      - "postgres" → PersistentPostgresSaver（PostgreSQL 数据库）
      - "sqlite" → PersistentSqliteSaver（SQLite 文件）
    """

    if config.backend == "postgres":
        from .graph.postgres_checkpointer import PersistentPostgresSaver

        return PersistentPostgresSaver(
            config.target,  # PostgreSQL 连接字符串
            pool_min=config.pool_min,
            pool_max=config.pool_max,
            max_checkpoints_per_thread_ns=config.max_checkpoints_per_thread_ns,
            compaction_interval=config.compaction_interval,
        )

    from .graph.persistent_checkpointer import PersistentSqliteSaver

    return PersistentSqliteSaver(
        db_path=config.target,  # SQLite 文件路径
        max_checkpoints_per_thread_ns=config.max_checkpoints_per_thread_ns,
        compaction_interval=config.compaction_interval,
    )


def _dispose_checkpointer(checkpointer: Any) -> None:
    """释放检查点实例持有的后端资源（如数据库连接池）。"""
    engine = getattr(checkpointer, "_engine", None)
    if engine is None or not hasattr(engine, "dispose"):
        return
    try:
        engine.dispose()
    except Exception:
        return


def close_checkpointer(checkpointer: Any) -> None:
    """释放一个检查点实例持有的后端资源。"""

    _dispose_checkpointer(checkpointer)


def reset_default_checkpointer() -> None:
    """重置缓存的默认检查点实例，使配置变更生效。

    当检查点配置（如后端类型、连接字符串）发生变化时，
    需要调用此函数清除缓存，下次创建时将使用新配置。
    """

    global _DEFAULT_CHECKPOINTER, _DEFAULT_CHECKPOINTER_SIGNATURE
    if _DEFAULT_CHECKPOINTER is not None:
        _dispose_checkpointer(_DEFAULT_CHECKPOINTER)
    _DEFAULT_CHECKPOINTER = None
    _DEFAULT_CHECKPOINTER_SIGNATURE = None


def create_default_checkpointer() -> Any:
    """【核心】创建共享的运行时检查点实例，优先使用持久化后端。

    缓存策略：
      - 若已有实例且配置签名未变 → 直接复用
      - 若配置签名变化 → 释放旧实例，创建新实例
      - 若 SQLite 创建失败 → 降级为内存检查点（InMemorySaver）
      - 若 PostgreSQL 创建失败 → 直接抛出异常（不降级）
    """

    global _DEFAULT_CHECKPOINTER, _DEFAULT_CHECKPOINTER_SIGNATURE
    config = resolve_checkpointer_config()
    signature = config.signature()
    # 配置未变化，复用已有实例
    if _DEFAULT_CHECKPOINTER is not None and signature == _DEFAULT_CHECKPOINTER_SIGNATURE:
        return _DEFAULT_CHECKPOINTER

    # 配置变化，释放旧实例
    if _DEFAULT_CHECKPOINTER is not None:
        _dispose_checkpointer(_DEFAULT_CHECKPOINTER)
        _DEFAULT_CHECKPOINTER = None
        _DEFAULT_CHECKPOINTER_SIGNATURE = None

    try:
        _DEFAULT_CHECKPOINTER = create_checkpointer(config)
        _DEFAULT_CHECKPOINTER_SIGNATURE = signature
        return _DEFAULT_CHECKPOINTER
    except Exception:
        if config.backend == "postgres":
            raise  # PostgreSQL 不降级，直接抛出异常
        # SQLite 创建失败时降级为内存检查点
        try:
            from langgraph.checkpoint.memory import InMemorySaver  # LangGraph 内存检查点，仅用于降级场景

            _DEFAULT_CHECKPOINTER = InMemorySaver()
            _DEFAULT_CHECKPOINTER_SIGNATURE = ("memory",)
            return _DEFAULT_CHECKPOINTER
        except Exception:
            return None


def build_memory_graph_source(
    *,
    user_message: str,  # 用户消息文本，如 "成都3日游怎么安排？"
    llm: Runnable,  # LLM 实例（LangChain Runnable 对象）
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话 ID，用于关联对话
    memory_manager: Any = None,  # 记忆管理器（可选，不提供时自动创建）
    system_prompt: Optional[str] = None,  # 系统提示词（可选，不提供时使用默认值）
    chat_mode: Optional[str] = None,  # 聊天模式（可选）
    run_id: Optional[str] = None,  # 运行 ID（可选，用于追踪单次执行）
    routing_llm: Optional[Runnable] = None,  # 路由 LLM（可选，用于意图路由）
    manager_defaults: dict[str, Any] | None = None,  # 记忆管理器默认参数
) -> GraphRuntimeSource:
    """【核心】构建带记忆的图运行源，供运行时执行使用。

    流程：
      1. 解析系统提示词和记忆管理器
      2. 创建初始状态（含用户消息、会话ID、记忆管理器等）
      3. 编译图（含检查点）
      4. 返回 GraphRuntimeSource

    旅行场景举例：
      source = build_memory_graph_source(
          user_message="成都3日游", llm=llm, tools=tools, session_id="user-123"
      )
      → source.agent 是编译后的图，可直接调用 source.agent.invoke(source.initial_state)
    """

    resolved_system_prompt = system_prompt or _default_system_prompt()
    resolved_manager = memory_manager or get_agent_memory_manager(
        llm=llm,
        **(manager_defaults or {}),
    )
    initial_state = AgentStateWithMemory.create(
        user_message=user_message,
        session_id=session_id,
        memory_manager=resolved_manager,
        system_prompt=resolved_system_prompt,
        chat_mode=chat_mode,
    )
    if run_id:
        initial_state["run_id"] = run_id

    agent = build_travel_agent(
        llm,
        tools,
        resolved_system_prompt,
        checkpointer=create_default_checkpointer(),  # 使用共享的检查点实例
        routing_llm=routing_llm,
    )
    return GraphRuntimeSource(
        agent=agent,
        initial_state=initial_state,
        memory_manager=resolved_manager,
    )


def build_memory_plan_preview_source(
    *,
    user_message: str,  # 用户消息文本
    llm: Runnable,  # LLM 实例
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话 ID
    memory_manager: Any = None,  # 记忆管理器（可选）
    system_prompt: Optional[str] = None,  # 系统提示词（可选）
    chat_mode: Optional[str] = None,  # 聊天模式（可选）
    routing_llm: Optional[Runnable] = None,  # 路由 LLM（可选）
    manager_defaults: dict[str, Any] | None = None,  # 记忆管理器默认参数
) -> PlanPreviewSource:
    """构建带记忆的计划预览源，供预览执行使用。

    与 build_memory_graph_source 类似，但不编译完整图，
    仅创建计划节点，适用于仅预览计划步骤的场景。
    """

    resolved_system_prompt = system_prompt or _default_system_prompt()
    resolved_manager = memory_manager or get_agent_memory_manager(
        llm=llm,
        **(manager_defaults or {}),
    )
    initial_state = AgentStateWithMemory.create(
        user_message=user_message,
        session_id=session_id,
        memory_manager=resolved_manager,
        system_prompt=resolved_system_prompt,
        chat_mode=chat_mode,
    )
    nodes = AgentNodes(llm, tools, resolved_system_prompt, routing_llm=routing_llm)
    return PlanPreviewSource(
        nodes=nodes,
        initial_state=initial_state,
        memory_manager=resolved_manager,
    )


def build_supervisor_streaming_source(
    *,
    request: SupervisorRunRequest,  # Supervisor 运行请求，包含用户消息、会话ID等
    context: SupervisorRuntimeContext,  # Supervisor 运行时上下文，包含 LLM、工具、记忆管理器等
) -> GraphRuntimeSource:
    """【核心】构建 Supervisor 流式执行的记忆感知运行源。

    这是 Supervisor 执行流的统一入口，将请求和上下文转换为图运行源。
    """

    return build_memory_graph_source(
        user_message=request.user_message,
        llm=context.llm,
        tools=context.tools,
        session_id=request.session_id,
        memory_manager=context.memory_manager,
        system_prompt=request.resolved_system_prompt(_default_system_prompt()),
        chat_mode=request.chat_mode,
        run_id=request.run_id,
        routing_llm=context.routing_llm,
    )


def build_supervisor_plan_preview_source(
    *,
    request: SupervisorPlanPreviewRequest,  # Supervisor 计划预览请求
    context: SupervisorRuntimeContext,  # Supervisor 运行时上下文
) -> PlanPreviewSource:
    """构建 Supervisor 计划预览的记忆感知运行源。

    这是 Supervisor 预览流的统一入口，将请求和上下文转换为计划预览源。
    """

    return build_memory_plan_preview_source(
        user_message=request.user_message,
        llm=context.llm,
        tools=context.tools,
        session_id=request.session_id,
        memory_manager=context.memory_manager,
        system_prompt=request.resolved_system_prompt(_default_system_prompt()),
        chat_mode=request.chat_mode,
        routing_llm=context.routing_llm,
    )
