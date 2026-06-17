"""Local ASGI tests for API validation and error-code contracts."""

from __future__ import annotations

import httpx
import pytest

from moyuan_web.main import create_app  # noqa: E402


class _FakeModelConfigManager:
    """Minimal model catalog for validation/error-contract tests."""

    def get_available_models(self) -> list[dict[str, str]]:
        """Return one configured model entry."""

        return [
            {
                "model_id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "openai",
            }
        ]


def _install_fake_model_config_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch model-config lookup so tests stay deterministic."""

    manager = _FakeModelConfigManager()
    monkeypatch.setattr("moyuan_web.bootstrap_app.get_model_config_manager", lambda: manager)
    monkeypatch.setattr("moyuan_web.routes.session.get_model_config_manager", lambda: manager)


@pytest.mark.asyncio
async def test_chat_validation_errors_use_normalized_error_contract():
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/chat/stream", json={"message": "trip please", "mode": "invalid"})

    assert response.status_code == 422
    assert response.headers.get("X-Request-ID")
    detail = response.json()["detail"]
    assert detail["code"] == "REQUEST_VALIDATION_FAILED"
    assert detail["error"] == "Request validation failed."
    assert any(issue["field"] == "body.mode" for issue in detail["details"])


@pytest.mark.asyncio
async def test_blank_message_is_rejected_by_request_model():
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/chat/stream", json={"message": "   ", "mode": "react"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "REQUEST_VALIDATION_FAILED"
    assert any(issue["field"] == "body.message" for issue in detail["details"])


@pytest.mark.asyncio
async def test_session_name_rejects_unknown_extra_fields():
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post("/api/session/new")
        session_id = create_response.json()["session_id"]

        response = await client.put(
            f"/api/session/{session_id}/name",
            json={"name": "Weekend Trip", "unexpected": "value"},
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "REQUEST_VALIDATION_FAILED"
    assert any(issue["field"] == "body.unexpected" for issue in detail["details"])


@pytest.mark.asyncio
async def test_set_session_model_rejects_removed_legacy_model_field():
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post("/api/session/new")
        session_id = create_response.json()["session_id"]

        response = await client.put(
            f"/api/session/{session_id}/model",
            json={"model_id": "gpt-4o-mini", "model": "gpt-4o"},
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "REQUEST_VALIDATION_FAILED"
    assert any(issue["field"] == "body.model" for issue in detail["details"])


@pytest.mark.asyncio
async def test_set_session_model_rejects_unknown_model_id(monkeypatch):
    _install_fake_model_config_manager(monkeypatch)
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post("/api/session/new")
        session_id = create_response.json()["session_id"]

        response = await client.put(
            f"/api/session/{session_id}/model",
            json={"model_id": "unknown-model"},
        )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "MODEL_NOT_FOUND"
    assert detail["details"] == {"model_id": "unknown-model"}
