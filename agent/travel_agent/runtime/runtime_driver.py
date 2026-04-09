"""Runtime driver that connects AgentRuntime to graph execution flow."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Protocol

from ..contracts import (
    SupervisorPlanPreview,
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorToolHealthDiagnostics,
    SupervisorRuntimeContext,
)

TOOL_RESULT_PREVIEW_LIMIT = 200


class RuntimeDriver(Protocol):
    """Describe the execution surface consumed by the application-facing runtime."""

    async def stream_with_memory(
        self,
        *,
        request: SupervisorRunRequest,
        context: SupervisorRuntimeContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield normalized runtime events backed by the legacy graph implementation."""

    def generate_plan_preview_with_memory(
        self,
        *,
        request: SupervisorPlanPreviewRequest,
        context: SupervisorRuntimeContext,
    ) -> SupervisorPlanPreview:
        """Return one memory-aware plan preview from the legacy graph path."""

    def get_tool_health_diagnostics(self) -> SupervisorToolHealthDiagnostics:
        """Return legacy graph tool-health diagnostics."""


class DefaultRuntimeDriver:
    """Lazy runtime driver that delegates to the graph execution module."""

    async def stream_with_memory(
        self,
        *,
        request: SupervisorRunRequest,
        context: SupervisorRuntimeContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield runtime events from the graph execution flow."""
        from ..graph.runtime_flow import stream_supervisor_run

        async for event in stream_supervisor_run(request=request, context=context):
            yield event

    def generate_plan_preview_with_memory(
        self,
        *,
        request: SupervisorPlanPreviewRequest,
        context: SupervisorRuntimeContext,
    ) -> SupervisorPlanPreview:
        """Return plan preview data without exposing graph imports upstream."""
        from ..graph.runtime_flow import generate_supervisor_plan_preview

        return generate_supervisor_plan_preview(request=request, context=context)

    def get_tool_health_diagnostics(self) -> SupervisorToolHealthDiagnostics:
        """Return tool-health diagnostics from the graph execution flow."""
        from ..graph.runtime_flow import collect_supervisor_tool_health_diagnostics

        return collect_supervisor_tool_health_diagnostics()
