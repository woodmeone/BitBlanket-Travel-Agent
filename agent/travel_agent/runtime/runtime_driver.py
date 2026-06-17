"""
运行时驱动（Runtime Driver）—— Agent 发动机的"传动系统"
========================================================

如果说 AgentRuntime 是发动机的操控面板（面向应用层），
那么 RuntimeDriver 就是发动机的传动系统（面向底层图执行引擎）。

它定义了 Agent 执行的三个核心操作接口：
  1. stream_with_memory —— 流式执行对话
  2. generate_plan_preview_with_memory —— 生成计划预览
  3. get_tool_health_diagnostics —— 获取工具健康诊断

本模块包含：
  - RuntimeDriver（Protocol）：驱动接口协议，定义"驱动必须实现什么"
  - DefaultRuntimeDriver：默认驱动实现，委托给 graph.runtime_flow 模块

设计模式：使用 Protocol（协议类）实现依赖倒置，AgentRuntime 依赖抽象接口
而非具体实现，便于测试时注入 Mock 驱动，或未来替换为其他执行引擎。
"""

from __future__ import annotations  # 启用延迟类型注解求值

from typing import Any, AsyncGenerator, Protocol  # Protocol: Python 的协议类（结构化子类型），类似于 Go 的接口

from ..contracts import (  # contracts: 契约/数据协议模块
    SupervisorPlanPreview,  # 监督者计划预览结果
    SupervisorPlanPreviewRequest,  # 计划预览请求
    SupervisorRunRequest,  # 监督者运行请求
    SupervisorToolHealthDiagnostics,  # 工具健康诊断结果
    SupervisorRuntimeContext,  # 运行时上下文（LLM、工具等共享资源）
)

TOOL_RESULT_PREVIEW_LIMIT = 200  # 工具结果预览的字符数上限，防止过长的工具输出


class RuntimeDriver(Protocol):
    """【核心】运行时驱动协议 —— 定义驱动层必须实现的接口。

    Protocol 是 Python 的结构化子类型机制（PEP 544），类似于其他语言的 interface。
    任何实现了这三个方法的类都可以作为 RuntimeDriver 使用，无需显式继承。

    旅行场景举例：就像汽车的传动系统接口，不管是燃油发动机还是电动马达，
    只要能提供"挂挡"、"加速"、"刹车"这三个操作，就可以驱动汽车。
    """

    async def stream_with_memory(
        self,
        *,
        request: SupervisorRunRequest,  # 运行请求，包含用户消息、会话 ID 等
        context: SupervisorRuntimeContext,  # 运行时上下文，包含 LLM、工具等共享资源
    ) -> AsyncGenerator[dict[str, Any], None]:
        """流式执行 Agent 对话，逐步 yield 标准化事件字典。"""

    def generate_plan_preview_with_memory(
        self,
        *,
        request: SupervisorPlanPreviewRequest,  # 计划预览请求
        context: SupervisorRuntimeContext,  # 运行时上下文
    ) -> SupervisorPlanPreview:
        """生成带记忆的计划预览，返回预览结果对象。"""

    def get_tool_health_diagnostics(self) -> SupervisorToolHealthDiagnostics:
        """获取工具健康诊断信息，检查各工具是否可用。"""


class DefaultRuntimeDriver:
    """默认运行时驱动实现 —— 延迟委托给 graph.runtime_flow 模块。

    "延迟委托"的含义：import 语句放在方法体内部而非模块顶部，
    这样只有在实际调用时才会加载 graph 模块，避免循环导入问题，
    同时也降低了模块初始化时的依赖开销。
    """

    async def stream_with_memory(
        self,
        *,
        request: SupervisorRunRequest,  # 运行请求
        context: SupervisorRuntimeContext,  # 运行时上下文
    ) -> AsyncGenerator[dict[str, Any], None]:
        """流式执行：委托给 graph.runtime_flow.stream_supervisor_run。"""
        from ..graph.runtime_flow import stream_supervisor_run  # 延迟导入，避免循环依赖

        async for event in stream_supervisor_run(request=request, context=context):  # 逐事件转发
            yield event

    def generate_plan_preview_with_memory(
        self,
        *,
        request: SupervisorPlanPreviewRequest,  # 计划预览请求
        context: SupervisorRuntimeContext,  # 运行时上下文
    ) -> SupervisorPlanPreview:
        """生成计划预览：委托给 graph.runtime_flow.generate_supervisor_plan_preview。

        不将 graph 模块的导入暴露给上层，保持驱动层作为隔离边界。
        """
        from ..graph.runtime_flow import generate_supervisor_plan_preview  # 延迟导入

        return generate_supervisor_plan_preview(request=request, context=context)

    def get_tool_health_diagnostics(self) -> SupervisorToolHealthDiagnostics:
        """获取工具健康诊断：委托给 graph.runtime_flow.collect_supervisor_tool_health_diagnostics。"""
        from ..graph.runtime_flow import collect_supervisor_tool_health_diagnostics  # 延迟导入

        return collect_supervisor_tool_health_diagnostics()
