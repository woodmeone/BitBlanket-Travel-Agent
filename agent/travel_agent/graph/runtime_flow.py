"""图执行入口模块 —— 将图组装逻辑与实际运行流程解耦。

本模块提供旅行 Agent 图（Graph）的各类运行入口函数，包括：
- 流式/非流式执行
- 带记忆上下文的执行
- 计划预览（Plan Preview）生成
- 工具健康诊断

所有函数均从外部调用方（如 API 层）进入，内部通过 GraphRuntimeSource
等数据源对象驱动 LangGraph 图的执行与事件流处理。

典型场景：用户发起"成都3日游"请求后，API 层调用本模块的
stream_supervisor_run，图依次经过意图识别→行程规划→工具调用→
答案生成等节点，最终将结构化行程流式返回给前端。
"""

from __future__ import annotations  # 允许在类型注解中使用尚未定义的类型（前向引用）

from typing import Any, Callable

from langchain_core.runnables import Runnable  # LangChain 可运行对象基类，LLM 和 Chain 均实现此接口
from langchain_core.tools import Tool  # LangChain 工具基类，用于定义可被 Agent 调用的工具

from ..contracts import (
    SupervisorPlanPreview,  # 计划预览结果的数据契约
    SupervisorPlanPreviewRequest,  # 计划预览请求的数据契约
    SupervisorRunRequest,  # 监督者运行请求的数据契约
    SupervisorRuntimeContext,  # 监督者运行时上下文的数据契约
    SupervisorToolHealthDiagnostics,  # 工具健康诊断结果的数据契约
)
from ..runtime_event_emitters import SupervisorEventEmitter  # 事件发射器，将原始图事件转换为前端可消费的标准化事件
from ..runtime_sources import (
    GraphRuntimeSource,  # 图运行数据源基类，封装 agent、初始状态、记忆管理器等
    PlanPreviewSource,  # 计划预览专用数据源
    build_memory_graph_source,  # 构建带记忆的图运行数据源
    build_memory_plan_preview_source,  # 构建带记忆的计划预览数据源
    build_supervisor_plan_preview_source,  # 构建监督者计划预览数据源
    build_supervisor_streaming_source,  # 构建监督者流式运行数据源
    create_default_checkpointer,  # 创建默认的检查点持久化器（用于保存对话状态）
)
from .nodes import AgentNodes  # Agent 图节点集合，包含意图识别、规划、执行等节点
from .runtime_config import get_runtime_config  # 获取运行时配置（从环境变量读取）
from .state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state  # 系统提示词与初始状态工厂


async def stream_supervisor_run(
    *,
    request: SupervisorRunRequest,  # 运行请求，包含用户消息、会话ID等
    context: SupervisorRuntimeContext,  # 运行时上下文，包含LLM、工具列表等
):
    """【核心】运行一次监督者流式请求，通过图执行流程逐步产出事件。

    典型场景：用户问"成都3日游怎么安排？"，本函数将请求构建为
    图运行数据源，然后流式产出节点启动、工具调用、文本片段等事件，
    前端可据此实时渲染进度与答案。

    Args:
        request: 监督者运行请求（含 user_message、session_id 等）
        context: 运行时上下文（含 llm、tools 等）

    Yields:
        标准化的监督者事件字典
    """
    source = build_supervisor_streaming_source(request=request, context=context)
    async for event in _stream_graph_source(
        source=source,
        user_message=request.user_message,
        session_id=request.session_id,
        persist_memory=request.persist_memory,
        run_id=request.run_id,
    ):
        yield event


def generate_supervisor_plan_preview(
    *,
    request: SupervisorPlanPreviewRequest,  # 预览请求，包含用户消息等
    context: SupervisorRuntimeContext,  # 运行时上下文
) -> SupervisorPlanPreview:
    """【核心】运行一次监督者计划预览请求，返回结构化计划但不执行工具。

    典型场景：用户输入"成都3日游"，本函数仅执行意图识别和行程规划节点，
    返回计划概览（如"第1天：宽窄巷子→武侯祠→锦里"），但不调用任何工具。

    Args:
        request: 计划预览请求
        context: 运行时上下文

    Returns:
        SupervisorPlanPreview: 结构化的计划预览结果
    """
    source = build_supervisor_plan_preview_source(request=request, context=context)
    return SupervisorPlanPreview.from_dict(_generate_plan_preview_from_source(source))


def collect_supervisor_tool_health_diagnostics() -> SupervisorToolHealthDiagnostics:
    """返回图执行流程暴露的工具健康诊断数据。

    用于监控端点，汇总运行时配置和各工具的健康快照。

    Returns:
        SupervisorToolHealthDiagnostics: 工具健康诊断结果
    """
    return SupervisorToolHealthDiagnostics.from_dict(get_tool_health_diagnostics())


def _extract_text_from_chunk(chunk: Any) -> str:
    """将 LangChain 1.x 的 chunk 负载归一化为纯文本字符串。

    LangChain 的流式输出 chunk 格式多样（字符串、列表、字典等），
    本函数统一提取其中的文本内容。

    Args:
        chunk: LangChain 流式输出的原始 chunk 对象

    Returns:
        提取到的纯文本，无法提取时返回空字符串
    """
    if chunk is None:
        return ""

    content = getattr(chunk, "content", chunk)  # 优先取 chunk.content 属性，否则直接用 chunk
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # 列表格式：逐项提取文本，如 [{"text": "成都"}, {"text": "3日游"}]
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        # 字典格式：直接取 "text" 键
        text = content.get("text")
        if isinstance(text, str):
            return text
    return str(content)  # 兜底：转为字符串


async def _persist_memory_snapshot(
    *,
    memory_manager: Any,  # 记忆管理器，提供 add_message 方法持久化对话
    session_id: str,  # 会话ID，区分不同用户的对话
    user_message: str,  # 用户消息原文
    answer: str,  # Agent 生成的回答
) -> None:
    """当记忆管理器可用时，持久化一轮用户/助手对话交换。

    典型场景：用户完成"成都3日游"对话后，将用户问题和Agent回答
    保存到记忆存储，下次同会话对话时可注入历史上下文。

    Args:
        memory_manager: 记忆管理器实例，为 None 时跳过
        session_id: 会话唯一标识
        user_message: 用户输入的消息
        answer: Agent 生成的回答
    """

    if memory_manager is None:
        return
    await memory_manager.add_message(session_id, "user", user_message)
    await memory_manager.add_message(session_id, "assistant", answer)


async def _stream_graph_source(
    *,
    source: GraphRuntimeSource,  # 预构建的图运行数据源
    user_message: str,  # 用户消息
    session_id: str,  # 会话ID
    persist_memory: bool,  # 是否持久化记忆快照
    run_id: str | None,  # 运行ID，用于追踪和关联事件
):
    """【核心】从一个预构建的图数据源中流式产出标准化监督者事件。

    执行流程：
    1. 发射初始事件（告知前端图开始运行）
    2. 监听图事件流，按事件类型分发处理：
       - on_node_start: 节点启动（如"意图识别节点开始"）
       - on_chat_model_stream: LLM 文本片段（流式输出答案）
       - on_tool_start: 工具调用开始（如调用"天气查询"工具）
       - on_tool_end: 工具调用结束（返回查询结果）
       - on_chain_end: 链结束（记录输出供记忆使用）
    3. 异常时尝试保存已有回答到记忆
    4. 正常结束后保存完整对话到记忆，发射完成事件

    典型场景：用户问"成都3日游"，图依次触发：
    意图识别→行程规划→天气查询工具→酒店查询工具→答案生成，
    每个阶段都通过本函数流式通知前端。

    Args:
        source: 图运行数据源（含 agent、initial_state、memory_manager 等）
        user_message: 用户消息原文
        session_id: 会话唯一标识
        persist_memory: 是否在执行结束后持久化对话记忆
        run_id: 本次运行的唯一标识

    Yields:
        标准化的监督者事件字典
    """

    emitter = SupervisorEventEmitter(session_id=session_id, run_id=run_id)

    try:
        yield emitter.emit_initial()  # 发射初始事件，告知前端图开始运行
        async for event in source.agent.astream_events(source.initial_state):
            event_type = event.get("event")

            if event_type == "on_node_start":
                # 节点启动事件，如"意图识别节点"或"规划节点"开始执行
                node_name = str(event.get("name", ""))
                for stage_event in emitter.emit_node_start(node_name):
                    yield stage_event

            elif event_type == "on_chat_model_stream":
                # LLM 流式文本片段，如逐步生成"成都3日游建议第1天..."
                content = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
                chunk_event = emitter.emit_chat_chunk(content)
                if chunk_event:
                    yield chunk_event

            elif event_type == "on_tool_start":
                # 工具调用开始，如开始查询"成都天气预报"
                tool_name = str(event.get("name", ""))
                for stage_event in emitter.emit_tool_start(tool_name):
                    yield stage_event

            elif event_type == "on_tool_end":
                # 工具调用结束，返回查询结果
                tool_name = str(event.get("name", ""))
                result = (event.get("data") or {}).get("output")
                yield emitter.emit_tool_end(tool_name, result)

            elif event_type == "on_chain_end":
                # 链执行结束，记录输出供后续记忆持久化使用
                output = (event.get("data") or {}).get("output")
                emitter.record_chain_output(output)

    except Exception:
        # 异常时尝试保存已有回答到记忆（即使中断也保留部分对话）
        if persist_memory:
            try:
                await _persist_memory_snapshot(
                    memory_manager=source.memory_manager,
                    session_id=session_id,
                    user_message=user_message,
                    answer=emitter.interrupted_answer(),  # 获取中断前的部分回答
                )
            except Exception:
                pass
        raise

    # 正常结束后持久化完整对话记忆
    if persist_memory:
        await _persist_memory_snapshot(
            memory_manager=source.memory_manager,
            session_id=session_id,
            user_message=user_message,
            answer=emitter.persisted_answer(),  # 获取完整回答
        )

    # 发射完成事件，告知前端图执行结束
    for completion_event in emitter.emit_completion_events():
        yield completion_event


def _generate_plan_preview_from_source(source: PlanPreviewSource) -> dict[str, Any]:
    """从一个预构建的预览数据源中生成标准化的计划预览。

    仅执行意图识别和行程规划两个节点，不触发工具调用。
    典型场景：用户输入"成都3日游"，返回计划概览：
    - intent: "itinerary"
    - plan: [{day:1, "宽窄巷子→武侯祠→锦里"}, ...]

    Args:
        source: 计划预览数据源

    Returns:
        包含 plan_id、intent、plan 等字段的字典
    """

    intent_state = dict(source.initial_state)
    intent_state.update(source.nodes.intent_node(intent_state))  # 执行意图识别节点
    plan_state = dict(intent_state)
    plan_state.update(source.nodes.plan_node(intent_state))  # 执行行程规划节点

    return {
        "plan_id": plan_state.get("plan_id"),  # 计划唯一标识
        "intent": plan_state.get("intent"),  # 识别到的意图，如 "itinerary"
        "intent_detail": plan_state.get("intent_detail", {}),  # 意图详情，如目的地、天数等
        "plan_explanation": plan_state.get("plan_explanation"),  # 计划说明
        "validation_status": plan_state.get("validation_status", "pass"),  # 校验状态
        "validation_errors": plan_state.get("validation_errors", []),  # 校验错误列表
        "plan": plan_state.get("plan", []),  # 行程计划步骤列表
    }


async def run_travel_agent(
    user_message: str,  # 用户消息，如"帮我规划成都3日游"
    llm: Runnable,  # 大语言模型实例（LangChain Runnable 接口）
    tools: list[Tool],  # 可用工具列表，如天气查询、酒店搜索等
    session_id: str = "default",  # 会话ID，默认"default"
    system_prompt: str | None = None,  # 自定义系统提示词，为 None 时使用默认
    run_id: str | None = None,  # 运行ID，用于追踪
    chat_mode: str | None = None,  # 聊天模式，如"streaming"/"batch"
    routing_llm: Runnable | None = None,  # 路由用 LLM，用于意图分类等轻量任务
) -> dict:
    """【核心】以非流式模式运行旅行 Agent 图，返回最终答案和结果字段。

    典型场景：用户问"成都3日游"，本函数一次性执行完整个图，
    返回完整答案（如详细行程安排），适合不需要实时流式展示的场景。

    Args:
        user_message: 用户输入的旅行问题
        llm: 大语言模型实例
        tools: 可调用的工具列表
        session_id: 会话唯一标识
        system_prompt: 自定义系统提示词
        run_id: 运行追踪ID
        chat_mode: 聊天模式
        routing_llm: 用于意图路由的轻量 LLM

    Returns:
        包含 success、answer、intent、tools_used、reasoning、messages 的字典
    """
    from .builder import build_travel_agent  # 延迟导入，避免循环依赖

    agent = build_travel_agent(
        llm,
        tools,
        system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=create_default_checkpointer(),  # 创建默认检查点，用于保存对话状态
        routing_llm=routing_llm,
    )
    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        system_message=system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        run_id=run_id,
        chat_mode=chat_mode,
    )
    result = await agent.ainvoke(initial_state)  # 非流式调用，等待完整结果
    return {
        "success": True,
        "answer": result.get("answer", ""),  # Agent 生成的最终回答
        "intent": result.get("intent"),  # 识别到的意图
        "tools_used": result.get("tools_used", []),  # 本次调用使用的工具列表
        "reasoning": result.get("reasoning"),  # 推理过程
        "messages": result.get("messages", []),  # 完整消息历史
    }


async def run_travel_agent_streaming(
    user_message: str,  # 用户消息
    llm: Runnable,  # 大语言模型实例
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话ID
    system_prompt: str | None = None,  # 自定义系统提示词
    run_id: str | None = None,  # 运行ID
    chat_mode: str | None = None,  # 聊天模式
    on_token: Callable | None = None,  # 文本片段回调，每收到一个 token 触发
    on_tool_start: Callable | None = None,  # 工具调用开始回调
    on_tool_end: Callable | None = None,  # 工具调用结束回调
    routing_llm: Runnable | None = None,  # 路由用 LLM
) -> dict:
    """【核心】以流式模式运行旅行 Agent 图，逐步产出标准化文本片段供前端消费。

    典型场景：用户问"成都3日游"，本函数流式输出答案：
    - on_token 回调逐步收到"成都""3日""游建议"等文本片段
    - on_tool_start 回调通知"天气查询"工具开始
    - on_tool_end 回调通知"天气查询"工具返回结果

    Args:
        user_message: 用户输入的旅行问题
        llm: 大语言模型实例
        tools: 可调用的工具列表
        session_id: 会话唯一标识
        system_prompt: 自定义系统提示词
        run_id: 运行追踪ID
        chat_mode: 聊天模式
        on_token: 文本片段回调函数（异步）
        on_tool_start: 工具调用开始回调函数（异步）
        on_tool_end: 工具调用结束回调函数（异步）
        routing_llm: 用于意图路由的轻量 LLM

    Returns:
        包含 success、answer、tools_used、run_id 的字典
    """
    from .builder import build_travel_agent  # 延迟导入，避免循环依赖

    agent = build_travel_agent(
        llm,
        tools,
        system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=create_default_checkpointer(),
        routing_llm=routing_llm,
    )
    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        system_message=system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        run_id=run_id,
        chat_mode=chat_mode,
    )

    answer = ""  # 累积的完整回答文本
    tools_used: list[str] = []  # 本次执行使用的工具名称列表

    async for event in agent.astream_events(initial_state):
        event_type = event.get("event")

        if event_type == "on_chat_model_stream":
            # LLM 流式输出文本片段
            chunk = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
            if chunk:
                answer += chunk
                if on_token:
                    await on_token(chunk)  # 回调通知前端新文本片段

        elif event_type == "on_tool_start":
            # 工具调用开始
            tool_name = event.get("name", "")
            tools_used.append(tool_name)
            if on_tool_start:
                await on_tool_start(tool_name)  # 回调通知前端工具开始

        elif event_type == "on_tool_end":
            # 工具调用结束
            tool_name = event.get("name", "")
            result = (event.get("data") or {}).get("output")
            if on_tool_end:
                await on_tool_end(tool_name, result)  # 回调通知前端工具结果

    return {"success": True, "answer": answer, "tools_used": tools_used, "run_id": run_id}


async def run_travel_agent_with_memory(
    user_message: str,  # 用户消息
    llm: Runnable,  # 大语言模型实例
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话ID
    memory_manager=None,  # 记忆管理器，用于读写对话历史
    system_prompt: str | None = None,  # 自定义系统提示词
    chat_mode: str | None = None,  # 聊天模式
    on_token: Callable | None = None,  # 文本片段回调
    on_tool_start: Callable | None = None,  # 工具调用开始回调
    on_tool_end: Callable | None = None,  # 工具调用结束回调
    persist_memory: bool = True,  # 是否持久化对话记忆，默认 True
    run_id: str | None = None,  # 运行ID
    routing_llm: Runnable | None = None,  # 路由用 LLM
) -> dict:
    """【核心】带记忆上下文注入的非流式图执行。

    与 run_travel_agent 的区别：本函数通过 memory_manager 注入历史对话上下文，
    使 Agent 能理解多轮对话的连贯性。

    典型场景：用户先问"成都有什么好玩的地方"，再问"帮我安排3天行程"，
    第二次调用时 Agent 能通过记忆知道用户对成都感兴趣，直接规划成都3日游。

    Args:
        user_message: 用户输入的旅行问题
        llm: 大语言模型实例
        tools: 可调用的工具列表
        session_id: 会话唯一标识
        memory_manager: 记忆管理器实例
        system_prompt: 自定义系统提示词
        chat_mode: 聊天模式
        on_token: 文本片段回调函数
        on_tool_start: 工具调用开始回调函数
        on_tool_end: 工具调用结束回调函数
        persist_memory: 是否在执行结束后持久化对话记忆
        run_id: 运行追踪ID
        routing_llm: 用于意图路由的轻量 LLM

    Returns:
        包含 success、answer、tools_used、session_id、run_id 的字典
    """

    source = build_memory_graph_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        run_id=run_id,
        routing_llm=routing_llm,
        manager_defaults={"max_history": 10, "summary_threshold": 15},  # 最多保留10轮历史，超过15条时自动摘要
    )

    answer = ""  # 累积的完整回答文本
    tools_used: list[str] = []  # 本次执行使用的工具名称列表
    async for event in source.agent.astream_events(source.initial_state):
        event_type = event.get("event")
        if event_type == "on_chat_model_stream":
            content = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
            if content:
                answer += content
                if on_token:
                    await on_token(content)
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            tools_used.append(tool_name)
            if on_tool_start:
                await on_tool_start(tool_name)
        elif event_type == "on_tool_end":
            tool_name = event.get("name", "")
            result = (event.get("data") or {}).get("output")
            if on_tool_end:
                await on_tool_end(tool_name, result)

    # 执行结束后持久化对话记忆
    if persist_memory:
        await _persist_memory_snapshot(
            memory_manager=source.memory_manager,
            session_id=session_id,
            user_message=user_message,
            answer=answer,
        )

    return {
        "success": True,
        "answer": answer,
        "tools_used": tools_used,
        "session_id": session_id,
        "run_id": run_id,
    }


async def run_travel_agent_streaming_with_memory(
    user_message: str,  # 用户消息
    llm: Runnable,  # 大语言模型实例
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话ID
    memory_manager=None,  # 记忆管理器
    system_prompt: str | None = None,  # 自定义系统提示词
    persist_memory: bool = True,  # 是否持久化记忆
    run_id: str | None = None,  # 运行ID
    chat_mode: str | None = None,  # 聊天模式
    routing_llm: Runnable | None = None,  # 路由用 LLM
):
    """【核心】带记忆上下文和标准化事件负载的流式图执行。

    结合了流式输出和记忆注入两种能力，通过 _stream_graph_source
    统一处理事件流和记忆持久化。

    典型场景：用户在多轮对话中问"帮我安排成都3日游"，本函数：
    1. 从记忆中读取之前讨论过的偏好（如"喜欢美食"）
    2. 流式输出行程安排
    3. 执行结束后将本轮对话保存到记忆

    Args:
        user_message: 用户输入的旅行问题
        llm: 大语言模型实例
        tools: 可调用的工具列表
        session_id: 会话唯一标识
        memory_manager: 记忆管理器实例
        system_prompt: 自定义系统提示词
        persist_memory: 是否持久化对话记忆
        run_id: 运行追踪ID
        chat_mode: 聊天模式
        routing_llm: 用于意图路由的轻量 LLM

    Yields:
        标准化的监督者事件字典
    """

    source = build_memory_graph_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        run_id=run_id,
        routing_llm=routing_llm,
    )
    async for event in _stream_graph_source(
        source=source,
        user_message=user_message,
        session_id=session_id,
        persist_memory=persist_memory,
        run_id=run_id,
    ):
        yield event


def generate_plan_preview_with_memory(
    user_message: str,  # 用户消息
    llm: Runnable,  # 大语言模型实例
    tools: list[Tool],  # 可用工具列表
    session_id: str = "default",  # 会话ID
    memory_manager=None,  # 记忆管理器
    system_prompt: str | None = None,  # 自定义系统提示词
    chat_mode: str | None = None,  # 聊天模式
    routing_llm: Runnable | None = None,  # 路由用 LLM
) -> dict:
    """生成带记忆上下文的计划预览，不执行完整的工具编排。

    典型场景：用户之前讨论过"想去成都吃火锅"，本次输入"3天怎么安排"，
    本函数结合记忆中的偏好，生成包含美食元素的成都3日游计划预览。

    Args:
        user_message: 用户输入的旅行问题
        llm: 大语言模型实例
        tools: 可调用的工具列表
        session_id: 会话唯一标识
        memory_manager: 记忆管理器实例
        system_prompt: 自定义系统提示词
        chat_mode: 聊天模式
        routing_llm: 用于意图路由的轻量 LLM

    Returns:
        包含 plan_id、intent、plan 等字段的字典
    """

    source = build_memory_plan_preview_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        routing_llm=routing_llm,
    )
    return _generate_plan_preview_from_source(source)


def get_tool_health_diagnostics() -> dict[str, Any]:
    """返回聚合的工具健康诊断数据，供监控和健康检查端点使用。

    汇总运行时配置和各工具节点的全局健康快照，
    如工具调用成功率、平均响应时间等。

    Returns:
        包含 runtime_config 和工具健康快照的字典
    """
    return {
        "runtime_config": get_runtime_config().to_dict(),  # 当前运行时配置
        **AgentNodes.get_global_tool_health_snapshot(),  # 各工具节点的健康状态快照
    }
