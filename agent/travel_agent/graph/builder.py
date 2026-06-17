"""
旅行 Agent 状态机组装与执行入口模块。

本模块的核心职责是将各个独立节点（意图识别、策略路由、计划生成、工具执行、
结果验证、回答生成等）组装成一张完整的 LangGraph 状态机图，并提供同步/异步、
流式等多种调用方式。

类比理解：
    如果把旅行 Agent 比作一条流水线，那么本模块就是"车间主任"——
    它不负责具体的加工工序（那是 nodes.py 的工作），而是决定每道工序的
    先后顺序、在哪些位置需要分流/汇合，以及整条流水线的启动方式。

主要组件：
    - TravelAgentGraph：状态机图封装类，负责构建、编译和运行图
    - build_travel_agent：工厂函数，快速创建并返回图实例
"""

from __future__ import annotations  # 允许在类型注解中使用尚未定义的类型（前向引用）

import asyncio      # 异步 I/O 框架，用于 async/await 和事件循环
import logging      # 日志记录
import threading    # 多线程，用于异步转同步桥接
from typing import Any, Callable, Optional

from langchain_core.runnables import Runnable  # LangChain 可运行对象基类，LLM 和 Chain 都实现此接口
from langchain_core.tools import Tool           # LangChain 工具定义基类
# StateGraph：LangGraph 的核心类，用于定义状态机图
#   - 状态机图由"节点"（处理函数）和"边"（流转规则）组成
#   - 每个"节点"接收并返回一个状态字典（AgentState）
#   - "边"决定执行完当前节点后跳转到哪个节点
# END：LangGraph 内置的终止标记，表示图的执行结束
from langgraph.graph import END, StateGraph

from .nodes import AgentNodes          # 节点集合类，包含所有状态机节点的具体实现
from .runtime_config import get_runtime_config  # 运行时配置获取（如 stream_events 版本号）
from .state import AgentState, TRAVEL_AGENT_SYSTEM_PROMPT  # 状态定义与默认系统提示词

logger = logging.getLogger(__name__)


def _resolve_stream_events_version() -> str:
    """解析当前运行环境配置的 LangGraph stream-events 版本号。

    LangGraph 的 astream_events API 在不同版本间存在不兼容的变更
    （如 v1 → v2 的事件结构差异），此函数从运行时配置中读取版本号，
    确保事件流的解析方式与当前 LangGraph 版本匹配。

    Returns:
        str: 版本号字符串，如 "v1" 或 "v2"
    """
    return get_runtime_config().stream_events_version


class TravelAgentGraph:
    """旅行 Agent 状态机图封装类。

    职责：
        1. 将各节点（意图识别、策略路由、计划生成等）组装为 LangGraph 状态机
        2. 编译状态机为可执行图
        3. 提供同步/异步/流式等多种调用入口

    典型使用方式：
        graph = TravelAgentGraph(llm=my_llm, tools=my_tools)
        result = await graph.ainvoke({"messages": [...], "session_id": "xxx"})
    """

    def __init__(
        self,
        llm: Runnable,
        tools: list[Tool],
        system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
        checkpointer: Any = None,
        routing_llm: Optional[Runnable] = None,
    ):
        """初始化旅行 Agent 图封装实例。

        Args:
            llm: 主推理模型（Runnable 是 LangChain 的可运行对象接口），
                 用于意图识别、策略路由、回答生成等核心推理环节。
                 例：ChatOpenAI(model="gpt-4o")
            tools: 已注册的工具列表，供 execute 节点调用。
                 例：[TavilySearchResults(...), WeatherTool(...)]
            system_prompt: 系统提示词，注入到模型上下文的开头，
                 定义 Agent 的角色和行为规范。默认使用 TRAVEL_AGENT_SYSTEM_PROMPT。
            planner_hooks: 计划器钩子，可选。用于在测试或实验中覆盖计划器行为。
                 键为钩子名称，值为接收状态字典、返回计划步骤列表的回调函数。
                 例：{"override_plan": lambda state: [{"tool": "search", "query": "..."}]}
            checkpointer: LangGraph 检查点存储器，可选。用于持久化每个会话的图状态，
                 实现多轮对话记忆。例：SqliteSaver(conn)
            routing_llm: 路由模型，可选。当意图/策略路由需要使用与主模型不同的
                 LLM 时指定（如用轻量模型做路由以降低延迟）。默认与 llm 相同。
        """
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.nodes = AgentNodes(llm, tools, system_prompt, planner_hooks=planner_hooks, routing_llm=routing_llm)
        self.checkpointer = checkpointer
        self._graph: Optional[StateGraph] = None  # 编译后的图实例，初始为 None（懒加载）

    def build(self) -> StateGraph:
        """【核心】构建并编译旅行 Agent 的 LangGraph 状态机图。

        本方法定义了所有节点的注册、边的连接和条件分支，
        是整个 Agent 运行流程的"蓝图"。

        执行路径（流程图）：

            ┌─────────────────────────────────────────────────────────┐
            │                      入口: intent                       │
            │              （意图识别：解析用户想做什么）                │
            └──────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
            ┌─────────────────────────────────────────────────────────┐
            │                    strategy                             │
            │          （策略路由：判断复杂度，选择执行路径）            │
            └──────┬──────────────┬──────────────┬───────────────────┘
                   │              │              │
              direct          plan           react
              (简单)        (有计划)        (无计划/反应式)
                   │              │              │
                   ▼              ▼              ▼
            ┌──────────┐  ┌───────────┐  ┌───────────┐
            │direct_   │  │   plan    │  │   react   │
            │answer    │  │(生成执行  │  │(反应式    │
            │(直接回答)│  │ 计划)     │  │ 推理)     │
            └────┬─────┘  └─────┬─────┘  └─────┬─────┘
                 │              │              │
                 │              └──────┬───────┘
                 │                     ▼
                 │            ┌─────────────────┐
                 │            │    execute      │◄──┐
                 │            │ (执行工具调用)   │   │
                 │            └────────┬────────┘   │
                 │                     │            │
                 │              ┌──────▼──────┐     │
                 │              │should_continue│   │
                 │              │(继续执行？)   │   │
                 │              └──┬───────┬──┘     │
                 │           继续  │       │ 完成   │
                 │                 │       │        │
                 │                 └───┐   ▼        │
                 │                     │ verify     │
                 │                     │(验证结果   │
                 │                     │ 是否充分)  │
                 │                     └──┬────┬───┘
                 │                  不充分  │    │ 充分
                 │                        │    ▼
                 │                        │  answer
                 │                        │ (生成最终
                 │                        │  回答)
                 │                        │    │
                 └────────────────────────┴────┘
                                 │
                                 ▼
                         ┌──────────────┐
                         │  self_check  │
                         │ (自检：格式、│
                         │  安全性检查)  │
                         └──────┬───────┘
                                │
                                ▼
                              [END]

        节点说明：
            - intent：意图识别节点，解析用户输入的旅行需求
            - strategy：策略路由节点，根据复杂度选择执行路径
            - plan：计划生成节点，为复杂请求生成多步执行计划
            - react：反应式推理节点，无预设计划，边推理边执行
            - execute：工具执行节点，调用搜索/天气等外部工具
            - verify：结果验证节点，判断工具返回是否足以回答用户
            - answer：回答生成节点，基于收集的信息生成最终回复
            - direct_answer：直接回答节点，简单问题无需工具直接回复
            - self_check：自检节点，对最终回答做格式和安全性检查

        条件边说明：
            - strategy → routing_decision：三路分支
                · "plan"：有明确计划路径（如"帮我规划5天日本行程"）
                · "react"：需要探索式推理（如"东京有什么好玩的地方"）
                · "direct"：简单问答无需工具（如"你好"、"旅行小贴士"）
            - execute → should_continue：循环/前进分支
                · "execute"：继续调用工具收集信息
                · "answer"：信息充分，进入验证
            - verify → verify_decision：重试/完成分支
                · "execute"：验证不通过，返回继续执行
                · "answer"：验证通过，生成最终回答

        Returns:
            StateGraph: 编译后的 LangGraph 状态机实例
        """
        # 创建以 AgentState 为状态模式的状态机图
        graph = StateGraph(AgentState)

        # ── 注册所有节点 ──────────────────────────────────────────
        graph.add_node("intent", self.nodes.intent_node)            # 意图识别
        graph.add_node("strategy", self.nodes.strategy_node)        # 策略路由
        graph.add_node("plan", self.nodes.plan_node)                # 计划生成
        graph.add_node("react", self.nodes.plan_node)               # 反应式推理（复用 plan_node 逻辑）
        graph.add_node("execute", self.nodes.execute_node)          # 工具执行
        graph.add_node("verify", self.nodes.verify_node)            # 结果验证
        graph.add_node("answer", self.nodes.answer_node)            # 回答生成
        graph.add_node("direct_answer", self.nodes.direct_answer_node)  # 直接回答
        graph.add_node("self_check", self.nodes.self_check_node)    # 自检

        # ── 设置入口点 ──────────────────────────────────────────
        graph.set_entry_point("intent")  # 用户请求首先进入意图识别

        # ── 定义边（执行流转规则）──────────────────────────────────
        # 固定边：intent → strategy（意图识别后必然进入策略路由）
        graph.add_edge("intent", "strategy")

        # 条件边：strategy 是第一个主要分支点
        # 简单请求可直接回答，复杂请求在计划式和反应式之间选择
        graph.add_conditional_edges(
            "strategy",
            self.nodes.routing_decision,  # 路由决策函数，返回 "plan"/"react"/"direct"
            {"plan": "plan", "react": "react", "direct": "direct_answer"},
        )

        # plan 和 react 汇合到 execute（无论有无计划，最终都要执行工具）
        graph.add_edge("plan", "execute")
        graph.add_edge("react", "execute")

        # 条件边：execute 可能循环执行（收集更多证据），
        # 也可能前进到 verify（判断当前工具结果是否足够充分）
        graph.add_conditional_edges(
            "execute",
            self.nodes.should_continue,  # 继续判断函数，返回 "execute"/"answer"
            {"execute": "execute", "answer": "verify"},
        )

        # 条件边：verify 决定是返回 execute 继续收集信息，还是进入 answer 生成回答
        graph.add_conditional_edges(
            "verify",
            self.nodes.verify_decision,  # 验证决策函数，返回 "execute"/"answer"
            {"execute": "execute", "answer": "answer"},
        )

        # answer 和 direct_answer 都汇合到 self_check（最终自检）
        graph.add_edge("answer", "self_check")
        graph.add_edge("direct_answer", "self_check")

        # 自检完成后，图执行结束
        graph.add_edge("self_check", END)

        # ── 编译图 ──────────────────────────────────────────────
        # 编译会将上述声明式的图定义转化为可执行的状态机
        # 如果提供了 checkpointer，编译后的图会支持会话持久化
        compile_kwargs = {}
        if self.checkpointer is not None:
            compile_kwargs["checkpointer"] = self.checkpointer

        self._graph = graph.compile(**compile_kwargs)
        logger.info("[Graph Builder] Graph built successfully")
        return self._graph

    @property  # @property 装饰器将方法变为属性访问方式，如 graph.xxx 而非 graph.xxx()
    def graph(self) -> StateGraph:
        """返回编译后的图实例，首次访问时自动构建（懒加载模式）。

        懒加载（Lazy Loading）说明：
            图的构建和编译是相对耗时的操作。使用懒加载可以：
            1. 延迟构建时机——只在真正需要运行图时才编译
            2. 避免在 __init__ 中做重活——实例化更快
            3. 允许在构建前修改配置（如动态添加 checkpointer）

        用法示例：
            agent = TravelAgentGraph(llm, tools)  # 此时图尚未构建
            result = agent.graph.invoke(state)     # 首次访问 .graph 触发构建

        Returns:
            StateGraph: 编译后的 LangGraph 状态机实例
        """
        if self._graph is None:
            self.build()
        return self._graph

    def _build_thread_config(self, state: dict) -> dict[str, dict[str, str]]:
        """构建会话级别的线程配置，确保检查点和事件流按会话隔离。

        LangGraph 使用 thread_id 来区分不同的对话会话：
            - 同一 thread_id 的多次调用共享检查点状态（实现多轮对话记忆）
            - 不同 thread_id 的调用互不干扰

        应用场景举例：
            用户 A 和用户 B 同时使用 Agent：
            - 用户 A 的 session_id="user_a_001"，所有状态保存在此线程下
            - 用户 B 的 session_id="user_b_002"，状态独立存储
            - 即使两人问同样的问题，也不会互相影响

        Args:
            state: LangGraph 状态字典，需包含 "session_id" 字段

        Returns:
            dict[str, dict[str, str]]: 嵌套配置字典，格式为
                {"configurable": {"thread_id": "xxx"}}
                若 state 中无 session_id，返回空字典 {}
        """
        session_id = state.get("session_id")
        if not session_id:
            return {}
        return {"configurable": {"thread_id": str(session_id)}}

    def invoke(self, state: dict) -> dict:
        """同步调用图执行，遇到纯异步节点时自动降级为异步执行。

        执行流程：
            1. 构建会话配置
            2. 尝试同步调用 graph.invoke()
            3. 若节点中包含纯异步函数（如 async def 定义的节点），
               同步调用会抛出 TypeError，此时降级到 _run_ainvoke_sync()

        应用场景举例：
            在 Flask 等同步 Web 框架中调用 Agent：
                @app.route("/ask")
                def ask():
                    result = agent.invoke({"messages": [...], "session_id": "s1"})

        Args:
            state: LangGraph 状态字典，包含 messages、session_id 等字段

        Returns:
            dict: 图执行完成后的最终状态字典
        """
        config = self._build_thread_config(state)
        resolved_config = config if config else None
        try:
            return self.graph.invoke(state, config=resolved_config)
        except TypeError as exc:
            # 仅处理"无同步函数"的特定错误，其他 TypeError 正常抛出
            if "No synchronous function provided" not in str(exc):
                raise
            logger.info("[Graph Builder] Falling back to async invoke due to async-only node execution")
            return self._run_ainvoke_sync(state, resolved_config)

    async def ainvoke(self, state: dict) -> dict:
        """异步调用图执行，返回最终合并后的状态快照。

        与 invoke() 的区别：
            - invoke() 是同步方法，会阻塞当前线程直到图执行完毕
            - ainvoke() 是异步方法（async def），使用 await 调用，
              不会阻塞事件循环，适合高并发场景

        应用场景举例：
            在 FastAPI 等异步 Web 框架中调用 Agent：
                @app.post("/ask")
                async def ask(request):
                    result = await agent.ainvoke({"messages": [...], "session_id": "s1"})

        Args:
            state: LangGraph 状态字典，包含 messages、session_id 等字段

        Returns:
            dict: 图执行完成后的最终状态字典
        """
        config = self._build_thread_config(state)
        return await self.graph.ainvoke(state, config=config if config else None)

    async def astream(self, state: dict):
        """以"值模式"流式输出图的逐步状态更新，用于渐进式 UI 渲染。

        stream_mode="values" 的含义：
            每当图执行完一个节点，就 yield 一次当前的完整状态快照。
            调用方可以逐步获取状态变化，实现打字机效果等渐进式展示。

        async for 说明：
            async for 是 Python 的异步迭代语法，用于遍历异步生成器。
            与普通 for 的区别：每次迭代前会 await 等待下一个值就绪，
            不会阻塞事件循环中的其他协程。

        应用场景举例：
            前端聊天界面需要逐步展示 Agent 的思考过程：
                async for chunk in agent.astream(state):
                    # chunk 是执行完某节点后的完整状态
                    # 可提取其中的回答片段，实时推送到前端
                    update_ui(chunk)

        Args:
            state: LangGraph 状态字典

        Yields:
            dict: 每个节点执行后的完整状态快照
        """
        config = self._build_thread_config(state)
        async for chunk in self.graph.astream(state, stream_mode="values", config=config if config else None):
            yield chunk

    async def astream_events(self, state: dict):
        """以"事件模式"流式输出结构化图事件，用于遥测、阶段更新和 SSE 传输。

        与 astream() 的区别：
            - astream()：输出节点级别的状态快照（粗粒度）
            - astream_events()：输出更细粒度的事件，如 LLM token 生成、
              工具调用开始/结束等，适合需要实时展示中间过程的场景

        SSE（Server-Sent Events）场景说明：
            SSE 是一种服务器向浏览器单向推送数据的技术，常用于 AI 聊天的
            实时流式输出。前端通过 EventSource API 接收事件流：
                // 前端代码示例
                const es = new EventSource("/api/chat/stream");
                es.onmessage = (e) => {
                    // e.data 是 Agent 产生的一个事件
                    appendToChat(e.data);
                };

            后端将 astream_events 的事件逐个通过 SSE 推送到前端：
                async def stream_endpoint(request):
                    async for event in agent.astream_events(state):
                        yield f"data: {json.dumps(event)}\\n\\n"

        version 参数说明：
            LangGraph 的 astream_events API 有 v1 和 v2 两个版本，
            事件结构不同。通过 _resolve_stream_events_version() 自动适配。

        Args:
            state: LangGraph 状态字典

        Yields:
            dict: 结构化事件字典，包含事件类型、数据、元信息等
        """
        config = self._build_thread_config(state)
        async for event in self.graph.astream_events(
            state,
            version=_resolve_stream_events_version(),
            config=config if config else None,
        ):
            yield event

    def _run_ainvoke_sync(self, state: dict, config: dict | None) -> dict:
        """将异步图执行桥接到同步调用点，同时保证事件循环安全。

        为什么需要这个方法？
            当 invoke() 遇到纯异步节点时，无法直接同步执行。
            但直接调用 asyncio.run() 在已有事件循环时会报错
            （"Cannot run the event loop while another loop is running"），
            所以需要分两种情况处理。

        两种场景：
            1. 无运行中的事件循环（如普通脚本）：
               直接 asyncio.run() 执行异步图
            2. 已有运行中的事件循环（如 Jupyter Notebook、FastAPI 中间件）：
               启动新线程，在新线程中运行 asyncio.run()，避免事件循环冲突

        Args:
            state: LangGraph 状态字典
            config: 可选的调用配置（含 thread_id 等）

        Returns:
            dict: 图执行完成后的最终状态字典
        """
        try:
            asyncio.get_running_loop()  # 检测是否已有运行中的事件循环
        except RuntimeError:
            # 场景1：无事件循环，直接用 asyncio.run() 执行
            return asyncio.run(self.graph.ainvoke(state, config=config))

        # 场景2：已有事件循环，在新线程中启动独立的事件循环
        result_holder: dict[str, Any] = {}    # 存储执行结果
        error_holder: dict[str, Exception] = {}  # 存储异常信息

        def _runner() -> None:
            """在桥接线程中运行异步图调用。"""
            try:
                result_holder["result"] = asyncio.run(self.graph.ainvoke(state, config=config))
            except Exception as inner_exc:  # pragma: no cover - 防御性桥接
                error_holder["error"] = inner_exc

        # 创建守护线程执行异步调用（daemon=True 表示主线程退出时自动终止）
        thread = threading.Thread(target=_runner, name="travel-agent-ainvoke-bridge", daemon=True)
        thread.start()
        thread.join()  # 阻塞等待线程执行完毕

        if "error" in error_holder:
            raise error_holder["error"]
        return dict(result_holder.get("result") or {})


def build_travel_agent(
    llm: Runnable,
    tools: list[Tool],
    system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
    planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
    checkpointer: Any = None,
    routing_llm: Optional[Runnable] = None,
) -> TravelAgentGraph:
    """工厂函数：创建并返回旅行 Agent 图实例。

    工厂模式说明：
        使用工厂函数而非直接调用 TravelAgentGraph() 的好处：
        1. 隐藏构建细节——调用方无需了解类名和参数
        2. 便于替换实现——未来可在此函数中切换不同的图实现
        3. 统一入口——所有外部模块通过此函数获取图实例

    应用场景举例：
        # 最简用法：只需提供 LLM 和工具
        agent = build_travel_agent(llm=my_llm, tools=my_tools)

        # 带会话记忆：添加 checkpointer
        from langgraph.checkpoint.sqlite import SqliteSaver
        agent = build_travel_agent(
            llm=my_llm,
            tools=my_tools,
            checkpointer=SqliteSaver(conn),
        )

        # 使用轻量路由模型：降低路由延迟
        agent = build_travel_agent(
            llm=ChatOpenAI(model="gpt-4o"),
            tools=my_tools,
            routing_llm=ChatOpenAI(model="gpt-4o-mini"),
        )

    Args:
        llm: 主推理模型
        tools: 已注册的工具列表
        system_prompt: 系统提示词，默认使用 TRAVEL_AGENT_SYSTEM_PROMPT
        planner_hooks: 计划器钩子，可选
        checkpointer: 检查点存储器，可选
        routing_llm: 路由模型，可选

    Returns:
        TravelAgentGraph: 初始化完成（但尚未构建图）的旅行 Agent 图封装实例
    """
    return TravelAgentGraph(
        llm,
        tools,
        system_prompt,
        planner_hooks=planner_hooks,
        checkpointer=checkpointer,
        routing_llm=routing_llm,
    )

# 从 runtime_flow 模块导入运行时流程函数，供外部直接使用
# noqa: E402 表示忽略"模块级导入不在文件顶部"的 lint 警告
# （因为此导入位于 build_travel_agent 之后，属于延迟导入）
from .runtime_flow import (  # noqa: E402
    _extract_text_from_chunk,              # 从流式块中提取文本
    generate_plan_preview_with_memory,     # 带记忆的计划预览生成
    get_tool_health_diagnostics,           # 工具健康诊断
    run_travel_agent,                      # 运行旅行 Agent（无记忆）
    run_travel_agent_streaming,            # 流式运行旅行 Agent（无记忆）
    run_travel_agent_streaming_with_memory,  # 流式运行旅行 Agent（带记忆）
    run_travel_agent_with_memory,          # 运行旅行 Agent（带记忆）
)
