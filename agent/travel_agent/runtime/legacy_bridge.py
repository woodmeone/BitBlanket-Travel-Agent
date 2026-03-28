"""Bridge legacy graph-builder entrypoints into the application-facing runtime."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Protocol

from ..contracts import (
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorRuntimeContext,
)

TOOL_RESULT_PREVIEW_LIMIT = 200


class LegacyRuntimeBridge(Protocol):
    """Describe the compatibility surface that still delegates to the legacy graph."""

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
    ) -> dict[str, Any]:
        """Return one memory-aware plan preview from the legacy graph path."""

    def get_tool_health_diagnostics(self) -> dict[str, Any]:
        """Return legacy graph tool-health diagnostics."""


class DefaultLegacyRuntimeBridge:
    """Lazy compatibility adapter around the existing graph.builder entrypoints."""

    async def stream_with_memory(
        self,
        *,
        request: SupervisorRunRequest,
        context: SupervisorRuntimeContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield runtime events from the legacy memory-aware streaming entrypoint."""
        from ..graph.builder import run_travel_agent_streaming_with_memory

        async for event in run_travel_agent_streaming_with_memory(
            user_message=request.user_message,
            llm=context.llm,
            tools=context.tools,
            session_id=request.session_id,
            memory_manager=context.memory_manager,
            system_prompt=request.system_prompt,
            persist_memory=request.persist_memory,
            run_id=request.run_id,
            chat_mode=request.chat_mode,
            routing_llm=context.routing_llm,
        ):
            yield event

    def generate_plan_preview_with_memory(
        self,
        *,
        request: SupervisorPlanPreviewRequest,
        context: SupervisorRuntimeContext,
    ) -> dict[str, Any]:
        """Return legacy graph plan preview data without exposing builder imports upstream."""
        from ..graph.builder import generate_plan_preview_with_memory

        return generate_plan_preview_with_memory(
            user_message=request.user_message,
            llm=context.llm,
            tools=context.tools,
            session_id=request.session_id,
            memory_manager=context.memory_manager,
            system_prompt=request.system_prompt,
            chat_mode=request.chat_mode,
            routing_llm=context.routing_llm,
        )

    def get_tool_health_diagnostics(self) -> dict[str, Any]:
        """Return tool-health diagnostics from the legacy graph compatibility path."""
        from ..graph.builder import get_tool_health_diagnostics

        return get_tool_health_diagnostics()
