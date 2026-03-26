"""Local ASGI smoke tests for artifact retrieval route."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from moyuan_web.dependencies.container import get_container  # noqa: E402
from moyuan_web.main import create_app  # noqa: E402


@pytest.mark.asyncio
async def test_latest_artifact_route_returns_normalized_artifact():
    app = create_app()
    repository = get_container().resolve("SessionRepository")
    session_id = f"artifact-route-{uuid.uuid4()}"
    await repository.create(
        {
            "session_id": session_id,
            "name": "artifact route",
            "model_id": "MiniMax-M2.5",
            "messages": [
                {
                    "role": "assistant",
                    "content": "trip ready",
                    "timestamp": "13:00:00",
                    "diagnostics": {
                        "runId": "run-artifact",
                        "artifact": {
                            "itinerary": {"plan_id": "plan-route"},
                            "verification": {"should_retry": False},
                        },
                    },
                }
            ],
        }
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/artifacts/{session_id}/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_found"] is True
    assert payload["run_id"] == "run-artifact"
    assert payload["artifact"]["itinerary"]["planId"] == "plan-route"
    assert payload["artifact"]["verification"]["shouldRetry"] is False


@pytest.mark.asyncio
async def test_latest_artifact_route_returns_not_found_for_missing_session():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/artifacts/missing-session/latest")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"
