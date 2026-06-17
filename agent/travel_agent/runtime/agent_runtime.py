"""
运行时（Runtime）层 —— Agent 的"发动机"
==========================================

Runtime 层是整个旅行 Agent 系统的执行引擎，负责：
  1. 启动 Agent 的运行流程（流式对话、计划预览、工具诊断等）
  2. 管理子 Agent（Subagent）的生命周期与切换
  3. 将底层图执行引擎产生的事件，翻译为上层应用可消费的标准化事件

打个比方：如果把 Agent 比作一辆汽车，那么：
  - skills（技能）是方向盘、刹车等操控装置
  - subagents（子 Agent）是不同驾驶模式（城市/高速/越野）
  - Runtime 就是发动机 —— 它把燃料（用户请求）转化为动力（执行结果）

本模块是应用层直接面对的 Runtime 包装器，在底层 RuntimeDriver 之上
叠加了技能注册、子 Agent 注册、Artifact（制品）组装等业务逻辑。
"""

from __future__ import annotations  # 启用延迟类型注解求值，允许在类型标注中引用尚未定义的类

from typing import Any, AsyncGenerator, Optional  # Any: 任意类型; AsyncGenerator: 异步生成器; Optional: 可选类型（等价于 T | None）

from langchain_core.runnables import Runnable  # LangChain 可运行对象基类，LLM 和 Chain 都实现此接口
from langchain_core.tools import Tool  # LangChain 工具基类，用于定义 Agent 可调用的外部工具

from ..artifacts import (  # artifacts: 制品构建模块，负责将执行结果组装为前端可渲染的结构化数据
    build_trip_plan_artifact_from_plan_preview,  # 从计划预览构建行程制品
    build_trip_plan_artifact_from_stream_event,  # 从流式事件构建行程制品
)

from ..contracts import (  # contracts: 契约/数据协议模块，定义各层之间传递的数据结构
    ExecutionReceipt,  # 执行回执 —— 记录一次完整运行的所有子 Agent 执行信息
    ExecutionReceiptStage,  # 执行阶段 —— 记录单个阶段（如"搜索中"、"规划中"）
    SubagentExecutionReceipt,  # 子 Agent 执行回执 —— 记录单个子 Agent 的执行详情
    SupervisorPlanPreview,  # 监督者计划预览 —— 规划阶段的预览结果
    SupervisorPlanPreviewRequest,  # 计划预览请求
    SupervisorRunRequest,  # 监督者运行请求 —— 一次完整对话的输入参数
    SupervisorToolHealthDiagnostics,  # 工具健康诊断 —— 检查各工具是否可用
    SupervisorRuntimeContext,  # 运行时上下文 —— 在驱动层之间共享的 LLM、工具等资源
)
from ..graph.state import TRAVEL_AGENT_SYSTEM_PROMPT  # 旅行 Agent 的系统提示词模板
from ..skills import SkillRegistry, build_default_skill_registry  # SkillRegistry: 技能注册表; build_default_skill_registry: 构建默认技能注册表
from ..subagents import SubagentRegistry, build_default_subagent_registry  # SubagentRegistry: 子 Agent 注册表; build_default_subagent_registry: 构建默认子 Agent 注册表
from ..supervisor import SupervisorTravelAgentGraph, build_supervisor_agent  # SupervisorTravelAgentGraph: 监督者图; build_supervisor_agent: 构建监督者 Agent
from .runtime_driver import DefaultRuntimeDriver, RuntimeDriver  # RuntimeDriver: 驱动协议; DefaultRuntimeDriver: 默认驱动实现


class AgentRuntime:
    """【核心】应用层 Runtime 包装器 —— Agent 的"发动机"入口。

    在底层 RuntimeDriver（纯图执行）之上，叠加了三层业务能力：
      1. 技能（Skills）：注册和管理 Agent 可使用的工具技能
      2. 子 Agent（Subagents）：注册和管理不同职能的子 Agent（如规划、搜索、预订）
      3. 制品（Artifacts）：将执行结果组装为前端可直接渲染的结构化数据

    旅行场景举例：用户说"帮我规划一个三亚5日游"，AgentRuntime 会：
      - 通过 stream_with_memory 启动流式对话
      - 自动在"规划子 Agent"和"搜索子 Agent"之间切换
      - 最终输出包含行程安排、酒店推荐等的结构化制品
    """

    def __init__(
        self,
        llm: Runnable,  # 大语言模型实例，如 ChatOpenAI，用于驱动 Agent 的推理和决策
        tools: list[Tool],  # Agent 可调用的工具列表，如搜索工具、酒店查询工具等
        *,
        system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,  # 系统提示词，定义 Agent 的角色和行为准则
        memory_manager: Any = None,  # 记忆管理器，负责对话历史的持久化存储
        routing_llm: Optional[Runnable] = None,  # 路由用 LLM，用于子 Agent 分发决策（为 None 时复用主 LLM）
        skill_registry: Optional[SkillRegistry] = None,  # 技能注册表，为 None 时使用默认注册表
        runtime_driver: Optional[RuntimeDriver] = None,  # 运行时驱动，为 None 时使用默认驱动
    ):
        """初始化应用层 Runtime 包装器，组装所有运行所需的组件。"""
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.memory_manager = memory_manager
        self.routing_llm = routing_llm
        self.skill_registry = skill_registry or build_default_skill_registry(tools)  # 若未提供则根据工具列表构建默认技能注册表
        self.subagent_registry = build_default_subagent_registry(self.skill_registry)  # 基于技能注册表构建默认子 Agent 注册表
        self.subagents = self.subagent_registry.names()  # 获取所有已注册子 Agent 的名称列表
        self.runtime_driver = runtime_driver or DefaultRuntimeDriver()  # 若未提供则使用默认驱动

    def build_supervisor_graph(self, checkpointer: Any = None) -> SupervisorTravelAgentGraph:
        """构建监督者图 —— Agent 执行的核心计算图。

        Args:
            checkpointer: 检查点存储，用于保存和恢复图执行状态（实现对话中断续传）
        """
        return build_supervisor_agent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
            routing_llm=self.routing_llm,
            checkpointer=checkpointer,  # 传入检查点存储，支持对话状态持久化
            skill_registry=self.skill_registry,  # 传入技能注册表，供监督者图做工具路由
        )

    async def stream_with_memory(
        self,
        *,
        user_message: str,  # 用户输入的消息，如"帮我规划一个三亚5日游"
        session_id: str = "default",  # 会话 ID，用于区分不同用户的对话
        persist_memory: bool = True,  # 是否持久化对话记忆（True: 保存到存储; False: 仅内存）
        run_id: Optional[str] = None,  # 运行 ID，用于追踪单次执行（为 None 时自动生成）
        chat_mode: Optional[str] = None,  # 对话模式，如"plan"（规划模式）、"chat"（闲聊模式）
    ) -> AsyncGenerator[dict[str, Any], None]:
        """【核心】流式执行 Agent 并返回标准化事件流，同时管理记忆和子 Agent 切换。

        这是 Runtime 最核心的方法，整个对话执行流程如下：
          1. 构建运行请求 → 2. 初始化子 Agent 追踪器 → 3. 驱动底层图执行
          4. 对每个事件进行子 Agent 路由和制品组装 → 5. 返回标准化事件

        旅行场景举例：用户说"帮我规划三亚5日游"
          - 事件流: stage(理解需求) → subagent_start(planning) → tool_start(搜索三亚酒店)
            → tool_end(酒店结果) → subagent_start(booking) → done(行程制品)
          - 每次子 Agent 切换都会产生 transition 事件，前端据此更新 UI 状态
        """
        request = self._build_stream_request(  # 步骤1: 构建标准化运行请求
            user_message=user_message,
            session_id=session_id,
            persist_memory=persist_memory,
            run_id=run_id,
            chat_mode=chat_mode,
        )
        tracker = _SubagentTracker(  # 步骤2: 初始化子 Agent 追踪器，用于跟踪子 Agent 的切换和执行状态
            registry=self.subagent_registry,
            session_id=request.session_id,
            run_id=request.run_id,
            chat_mode=request.chat_mode,
        )
        async for event in self.runtime_driver.stream_with_memory(  # 步骤3: 通过驱动层启动底层图的流式执行
            request=request,
            context=self._build_runtime_context(),
        ):
            # --- 处理 stage 事件：Agent 执行阶段的进度通知 ---
            if event.get("type") == "stage":
                explicit_subagent = _coerce_optional_str(event.get("subagent"))  # 将值转为可选字符串，处理 None 和空串
                next_subagent = self.subagent_registry.resolve_subagent_for_stage(  # 根据阶段信息解析应切换到哪个子 Agent
                    stage=_coerce_optional_str(event.get("stage")),
                    label=_coerce_optional_str(event.get("label")),
                    explicit_subagent=explicit_subagent,
                )
                for transition_event in tracker.transition(next_subagent, trigger="stage"):  # 如果子 Agent 发生切换，发出过渡事件
                    yield transition_event
                if next_subagent:
                    event = dict(event)  # 浅拷贝事件字典，避免修改原始事件（dict() 创建新字典对象）
                    event["subagent"] = next_subagent  # 在事件中标记当前子 Agent
                tracker.note_stage(  # 记录阶段信息到追踪器
                    stage=_coerce_optional_str(event.get("stage")),
                    label=_coerce_optional_str(event.get("label")),
                    subagent=_coerce_optional_str(event.get("subagent")),
                )

            # --- 处理 tool_start 事件：工具开始调用 ---
            if event.get("type") == "tool_start":
                tool_name = _coerce_optional_str(event.get("tool")) or ""
                next_subagent = self.subagent_registry.resolve_subagent_for_tool(tool_name)  # 根据工具名解析所属子 Agent
                for transition_event in tracker.transition(next_subagent, trigger="tool"):
                    yield transition_event
                if next_subagent:
                    event = dict(event)
                    event["subagent"] = next_subagent
                tracker.note_tool(tool_name, subagent=_coerce_optional_str(event.get("subagent")))  # 记录工具使用信息

            # --- 处理 tool_end 事件：工具调用结束 ---
            if event.get("type") == "tool_end":
                tool_name = _coerce_optional_str(event.get("tool")) or ""
                subagent_name = self.subagent_registry.resolve_subagent_for_tool(tool_name)
                if subagent_name:
                    event = dict(event)
                    event["subagent"] = subagent_name
                tracker.note_tool(tool_name, subagent=_coerce_optional_str(event.get("subagent")))

            # --- 处理 done 事件：执行完成，组装最终制品和执行回执 ---
            if event.get("type") == "done":
                enriched_event = dict(event)  # 浅拷贝，用于添加额外字段
                # 从流式事件构建基础行程制品（如行程概览、酒店推荐等）
                artifact = build_trip_plan_artifact_from_stream_event(
                    enriched_event,
                    user_message=request.user_message,
                    session_id=request.session_id,
                    chat_mode=request.chat_mode,
                )
                # 收集各子 Agent 的制品补丁（如搜索子 Agent 补充景点信息、预订子 Agent 补充价格信息）
                subagent_patches = self.subagent_registry.done_artifact_patches(
                    enriched_event,
                    user_message=request.user_message,
                    session_id=request.session_id,
                    chat_mode=request.chat_mode,
                )
                # 将所有补丁深度合并到基础制品中
                merged_artifact = _merge_artifact_patches(artifact, subagent_patches.values())
                enriched_event["artifact"] = merged_artifact  # 附加合并后的制品到事件
                # 为每个子 Agent 发出独立的制品补丁事件，前端可据此做增量更新
                for subagent_name, patch in subagent_patches.items():
                    tracker.note_artifact_patch(subagent_name, patch)  # 记录制品补丁覆盖情况
                    yield {
                        "type": "artifact_patch",
                        "subagent": subagent_name,
                        "artifact_patch": patch,
                        "run_id": request.run_id,
                        "session_id": request.session_id,
                    }
                # 发出子 Agent 结束过渡事件
                for transition_event in tracker.finish():
                    yield transition_event
                # 附加执行回执（包含所有子 Agent 的执行顺序、使用的工具等）
                enriched_event["execution_receipt"] = tracker.build_execution_receipt()
                yield enriched_event  # 发出最终的 done 事件
                continue  # 跳过末尾的 yield event，因为 done 事件已经手动 yield
            yield event  # 非特殊事件直接透传

    def generate_plan_preview_with_memory(
        self,
        *,
        user_message: str,  # 用户输入的消息
        session_id: str = "default",  # 会话 ID
        chat_mode: Optional[str] = None,  # 对话模式
    ) -> dict[str, Any]:
        """生成带记忆的计划预览，并附加预览制品。

        与 stream_with_memory 不同，此方法是同步的，用于在用户正式提交前
        快速生成一个行程计划的预览。

        旅行场景举例：用户输入"三亚5日游"后，前端先调用此方法展示一个
        初步的行程框架（如 Day1 到达 → Day2 海滩 → ...），用户确认后再
        调用 stream_with_memory 进行详细规划。
        """
        request = self._build_plan_preview_request(
            user_message=user_message,
            session_id=session_id,
            chat_mode=chat_mode,
        )
        preview = self.runtime_driver.generate_plan_preview_with_memory(  # 通过驱动层获取原始计划预览
            request=request,
            context=self._build_runtime_context(),
        )
        enriched_preview = _coerce_plan_preview_dict(preview)  # 将预览结果统一转为字典格式
        artifact = build_trip_plan_artifact_from_plan_preview(  # 从预览构建行程制品
            enriched_preview,
            user_message=request.user_message,
            session_id=request.session_id,
        )
        preview_patch = self.subagent_registry.preview_artifact_patch(enriched_preview)  # 获取规划子 Agent 的制品补丁
        enriched_preview["artifact"] = _merge_artifact_patches(artifact, [preview_patch])  # 合并基础制品和补丁
        enriched_preview["subagent"] = "planning"  # 标记为规划子 Agent 产出
        enriched_preview["skills"] = self.subagent_registry.skill_names("planning")  # 附加规划子 Agent 使用的技能列表
        enriched_preview["artifact_patch"] = preview_patch  # 附加原始补丁，供前端做增量渲染
        return enriched_preview

    def get_tool_health_diagnostics(self) -> dict[str, Any]:
        """获取工具健康诊断信息，以及技能和子 Agent 的元数据。

        用于运维监控和前端展示，返回各工具是否可用、已注册的技能和子 Agent 列表等。
        """
        diagnostics = _coerce_tool_health_diagnostics_dict(self.runtime_driver.get_tool_health_diagnostics())  # 获取底层工具诊断并转为字典
        diagnostics["skills"] = self.skill_registry.to_dict()  # 附加技能注册表信息
        diagnostics["subagents"] = list(self.subagents)  # 附加子 Agent 名称列表
        diagnostics["subagent_skills"] = {  # 每个子 Agent 拥有哪些技能
            name: self.subagent_registry.skill_names(name) for name in self.subagents
        }
        diagnostics["subagent_skill_policies"] = {  # 每个子 Agent 的技能选择策略（如"全部"、"按需"等）
            name: self.subagent_registry.selection_policy(name) for name in self.subagents
        }
        diagnostics["architecture_phase"] = "phase2-supervisor-subagents"  # 标记当前架构阶段
        return diagnostics

    def _build_runtime_context(self) -> SupervisorRuntimeContext:
        """构建共享运行时上下文，传递给驱动层使用。"""
        return SupervisorRuntimeContext(
            llm=self.llm,
            tools=self.tools,
            memory_manager=self.memory_manager,
            routing_llm=self.routing_llm,
        )

    def _build_stream_request(
        self,
        *,
        user_message: str,
        session_id: str,
        persist_memory: bool,
        run_id: Optional[str],
        chat_mode: Optional[str],
    ) -> SupervisorRunRequest:
        """构建监督者运行请求，封装流式执行所需的所有参数。"""
        return SupervisorRunRequest(
            user_message=user_message,
            session_id=session_id,
            system_prompt=self.system_prompt,
            persist_memory=persist_memory,
            run_id=run_id,
            chat_mode=chat_mode,
        )

    def _build_plan_preview_request(
        self,
        *,
        user_message: str,
        session_id: str,
        chat_mode: Optional[str],
    ) -> SupervisorPlanPreviewRequest:
        """构建计划预览请求，封装预览生成所需的参数。"""
        return SupervisorPlanPreviewRequest(
            user_message=user_message,
            session_id=session_id,
            system_prompt=self.system_prompt,
            chat_mode=chat_mode,
        )


class _SubagentTracker:
    """【核心】子 Agent 追踪器 —— 跟踪子 Agent 的切换过程并生成执行回执。

    在一次完整的 Agent 运行中，可能涉及多个子 Agent 的切换，例如：
      - 用户说"帮我规划三亚5日游并预订酒店"
      - 先切换到 planning 子 Agent（规划行程）
      - 再切换到 booking 子 Agent（预订酒店）
      - 最后切换到 search 子 Agent（搜索攻略）

    _SubagentTracker 负责记录每一次切换，并在运行结束时生成完整的执行回执。
    它维护一个 segments 列表，每个 segment 对应一个子 Agent 的执行片段。
    """

    def __init__(
        self,
        *,
        registry: SubagentRegistry,  # 子 Agent 注册表，用于查找子 Agent 的元信息
        session_id: str,  # 会话 ID
        run_id: Optional[str],  # 运行 ID
        chat_mode: Optional[str],  # 对话模式
    ):
        """初始化追踪器状态。"""
        self.registry = registry
        self.session_id = session_id
        self.run_id = run_id
        self.chat_mode = chat_mode
        self.active: Optional[str] = None  # 当前活跃的子 Agent 名称（None 表示无活跃子 Agent）
        self.sequence = 0  # 子 Agent 切换序号，每次切换递增
        self.segments: list[SubagentExecutionReceipt] = []  # 所有子 Agent 执行片段的列表
        self._active_segment: Optional[SubagentExecutionReceipt] = None  # 当前活跃的执行片段（可变对象，用于实时更新）

    def transition(self, next_subagent: Optional[str], *, trigger: str) -> list[dict[str, Any]]:
        """【核心】处理子 Agent 切换，在切换时发出 start/end 事件。

        当活跃子 Agent 发生变化时：
          1. 先为旧子 Agent 发出 end_event（结束事件）
          2. 再为新子 Agent 发出 start_event（开始事件）

        旅行场景举例：当前活跃的是 planning 子 Agent，现在需要切换到 booking 子 Agent
          - 先发出 planning 的 end_event（"规划阶段完成"）
          - 再发出 booking 的 start_event（"预订阶段开始"）

        Args:
            next_subagent: 即将切换到的子 Agent 名称（None 表示结束当前子 Agent）
            trigger: 切换触发原因，如 "stage"（阶段变化）、"tool"（工具调用）、"finish"（运行结束）

        Returns:
            需要发出的事件列表（可能为空，如果没有发生切换）
        """
        if next_subagent == self.active:  # 子 Agent 未变化，无需切换
            return []

        events: list[dict[str, Any]] = []
        if self.active:  # 如果有活跃的子 Agent，先结束它
            active_subagent = self.registry.get(self.active)
            if active_subagent is not None:
                self._finalize_active_segment(  # 终结当前活跃片段，设置状态和摘要
                    status="completed",
                    summary=f"{self.active} segment completed",
                )
                events.append(
                    active_subagent.end_event(  # 生成子 Agent 结束事件
                        session_id=self.session_id,
                        run_id=self.run_id,
                        sequence=self.sequence,
                        status="completed",
                        summary=f"{self.active} segment completed",
                    )
                )

        self.active = next_subagent  # 更新活跃子 Agent
        if next_subagent:  # 如果有新的子 Agent，开始它
            next_subagent_model = self.registry.get(next_subagent)
            if next_subagent_model is not None:
                self.sequence += 1  # 递增切换序号
                self._active_segment = SubagentExecutionReceipt(  # 创建新的执行片段
                    subagent=next_subagent,
                    sequence=self.sequence,
                    trigger=trigger,
                    description=next_subagent_model.description,
                    skills=next_subagent_model.skill_names(),
                    tool_names=next_subagent_model.tool_names(),
                )
                self.segments.append(self._active_segment)  # 追加到片段列表
                events.append(
                    next_subagent_model.start_event(  # 生成子 Agent 开始事件
                        session_id=self.session_id,
                        run_id=self.run_id,
                        sequence=self.sequence,
                        trigger=trigger,
                        chat_mode=self.chat_mode,
                    )
                )
        return events

    def finish(self) -> list[dict[str, Any]]:
        """结束当前活跃的子 Agent，发出终止事件。通过传入 None 触发 transition 的结束逻辑。"""
        return self.transition(None, trigger="finish")

    def note_stage(
        self,
        *,
        stage: Optional[str],  # 阶段标识，如 "searching"、"planning"
        label: Optional[str],  # 阶段显示标签，如 "搜索中"、"规划中"
        subagent: Optional[str],  # 所属子 Agent 名称
    ) -> None:
        """将一个阶段观察记录到对应的执行片段中，自动去重。

        旅行场景举例：planning 子 Agent 经历了 "理解需求" → "搜索景点" → "生成行程" 三个阶段，
        每个阶段都会通过此方法记录到 planning 的执行片段中。
        """
        segment = self._segment_for(subagent or self.active)  # 找到对应的执行片段
        if segment is None:
            return
        observation = ExecutionReceiptStage(stage=stage, label=label)
        # 去重：如果该阶段已记录过，则跳过
        if any(
            existing.stage == observation.stage and existing.label == observation.label
            for existing in segment.stages
        ):
            return
        segment.stages.append(observation)

    def note_tool(self, tool_name: str, *, subagent: Optional[str]) -> None:
        """将一个工具使用记录追加到对应的执行片段中，自动去重。

        旅行场景举例：booking 子 Agent 调用了 "hotel_search" 和 "flight_search" 两个工具，
        这些工具名会被记录到 booking 的执行片段中，最终出现在执行回执里。
        """
        normalized = _coerce_optional_str(tool_name)
        if not normalized:
            return
        segment = self._segment_for(subagent or self.active)
        if segment is None:
            return
        if normalized not in segment.tools_used:
            segment.tools_used.append(normalized)

    def note_artifact_patch(self, subagent: str, patch: dict[str, Any]) -> None:
        """将制品补丁的覆盖范围记录到对应子 Agent 的最新执行片段中。

        旅行场景举例：search 子 Agent 提交了一个包含 "attractions" 和 "restaurants" 两个
        区块的制品补丁，这两个区块名会被记录下来，用于执行回执中的覆盖范围统计。
        """
        segment = self._segment_for(subagent)
        if segment is None or not isinstance(patch, dict):
            return
        for section in patch:
            normalized = _coerce_optional_str(section)
            if normalized and normalized not in segment.artifact_patch_sections:
                segment.artifact_patch_sections.append(normalized)

    def build_execution_receipt(self) -> dict[str, Any]:
        """构建执行回执 —— 一次完整运行的"成绩单"。

        包含：子 Agent 执行顺序、使用的工具列表、制品补丁覆盖的子 Agent、
        以及每个子 Agent 的详细执行片段。
        """
        receipt = ExecutionReceipt(
            session_id=self.session_id,
            run_id=self.run_id,
            chat_mode=self.chat_mode,
            subagent_order=[segment.subagent for segment in self.segments],  # 子 Agent 执行顺序，如 ["planning", "booking", "search"]
            tools_used=_dedupe_preserve_order(  # 所有使用的工具（去重保序）
                tool_name for segment in self.segments for tool_name in segment.tools_used
            ),
            artifact_patch_subagents=_dedupe_preserve_order(  # 提交了制品补丁的子 Agent 列表
                segment.subagent for segment in self.segments if segment.artifact_patch_sections
            ),
            segments=self.segments,
        )
        return receipt.to_dict()

    def _finalize_active_segment(self, *, status: str, summary: str) -> None:
        """终结当前活跃的执行片段，设置最终状态和摘要。"""
        if self._active_segment is None:
            return
        self._active_segment.status = status  # 设置状态，如 "completed"
        self._active_segment.summary = summary  # 设置摘要描述
        self._active_segment = None  # 清空活跃片段引用

    def _segment_for(self, subagent: Optional[str]) -> Optional[SubagentExecutionReceipt]:
        """查找指定子 Agent 的最新执行片段（从后往前搜索，返回最近的匹配）。"""
        normalized = _coerce_optional_str(subagent)
        if not normalized:
            return self._active_segment  # 无指定子 Agent 时返回当前活跃片段
        for segment in reversed(self.segments):  # reversed: 反向遍历列表，从最新到最旧
            if segment.subagent == normalized:
                return segment
        return None


def _merge_artifact_patches(
    base_artifact: dict[str, Any],  # 基础制品字典
    patches: Any,  # 补丁列表，每个补丁是一个字典
) -> dict[str, Any]:
    """将多个子 Agent 的制品补丁递归合并到基础制品中。

    旅行场景举例：基础制品包含行程框架，planning 子 Agent 补充了"景点推荐"，
    booking 子 Agent 补充了"酒店信息"，此函数将它们合并为一个完整的行程制品。
    """
    merged = dict(base_artifact)  # 浅拷贝基础制品，避免修改原始数据
    for patch in patches:
        if isinstance(patch, dict):  # isinstance: 检查对象是否为指定类型
            _deep_merge_inplace(merged, patch)
    return merged


def _deep_merge_inplace(target: dict[str, Any], patch: dict[str, Any]) -> None:
    """递归合并：将 patch 字典深度合并到 target 中（原地修改 target）。

    对于嵌套字典，递归合并而非覆盖；对于非字典值，直接覆盖。
    例: target={"a": {"b": 1}}, patch={"a": {"c": 2}} → target={"a": {"b": 1, "c": 2}}
    """
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):  # 两边都是字典则递归合并
            _deep_merge_inplace(target[key], value)
            continue
        target[key] = value  # 否则直接覆盖


def _coerce_optional_str(value: Any) -> Optional[str]:
    """将任意值转为可选字符串：None → None，其他值 → 去空格后的字符串（空串也转为 None）。"""
    if value is None:
        return None
    text = str(value).strip()  # str(): 转字符串; strip(): 去除首尾空白
    return text or None  # 空字符串 "" 为 falsy 值，or None 会将其转为 None


def _dedupe_preserve_order(values: Any) -> list[str]:
    """去重并保持首次出现的顺序。

    例: ["a", "b", "a", "c"] → ["a", "b", "c"]
    使用列表而非集合（set），因为集合不保证顺序。
    """
    deduped: list[str] = []
    for value in values:
        normalized = _coerce_optional_str(value)
        if normalized and normalized not in deduped:  # not in: O(n) 线性查找，对小型列表足够高效
            deduped.append(normalized)
    return deduped


def _coerce_plan_preview_dict(preview: Any) -> dict[str, Any]:
    """将计划预览统一转为字典格式，兼容契约对象和原始字典两种输入。"""
    if isinstance(preview, SupervisorPlanPreview):
        return preview.to_dict()  # 契约对象有 to_dict() 方法
    return dict(preview) if isinstance(preview, dict) else {}  # 已是字典则浅拷贝，否则返回空字典


def _coerce_tool_health_diagnostics_dict(diagnostics: Any) -> dict[str, Any]:
    """将工具健康诊断统一转为字典格式，兼容契约对象和原始字典两种输入。"""
    if isinstance(diagnostics, SupervisorToolHealthDiagnostics):
        return diagnostics.to_dict()
    return dict(diagnostics) if isinstance(diagnostics, dict) else {}
