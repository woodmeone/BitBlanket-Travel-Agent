"""Unit tests for dependency-container bootstrap wiring."""

from __future__ import annotations

from config import server_config
from moyuan_web.bootstrap_container import initialize_dependency_container  # noqa: E402
from moyuan_web.bootstrap_services import register_default_services  # noqa: E402
from moyuan_web.dependencies.container import Container, build_default_container  # noqa: E402
from moyuan_web.repositories.file_session_repository import FileSessionRepository  # noqa: E402
from moyuan_web.repositories.postgres_share_link_repository import PostgresShareLinkRepository  # noqa: E402
from moyuan_web.repositories.session_repository_postgres import PostgresSessionRepository  # noqa: E402
from moyuan_web.services.artifact_service import ArtifactService  # noqa: E402
from moyuan_web.services.chat_service import ChatService  # noqa: E402
from moyuan_web.services.city_service import CityService  # noqa: E402
from moyuan_web.services.map_service import MapService  # noqa: E402
from moyuan_web.services.share_service import ShareService  # noqa: E402


def test_register_default_services_registers_expected_provider_names():
    container = Container()
    register_default_services(container)

    assert container.has_provider("SessionRepository") is True
    assert container.has_provider("ShareLinkRepository") is True
    assert container.has_provider("ArtifactService") is True
    assert container.has_provider("SessionService") is True
    assert container.has_provider("ChatService") is True
    assert container.has_provider("CityService") is True
    assert container.has_provider("MapService") is True
    assert container.has_provider("ShareService") is True
    assert container.has_provider("TravelAgent") is True


def test_build_default_container_resolves_singletons():
    container = build_default_container()

    city_service = container.resolve("CityService")
    map_service = container.resolve("MapService")
    share_service = container.resolve("ShareService")
    chat_service = container.resolve("ChatService")
    artifact_service = container.resolve("ArtifactService")

    assert isinstance(city_service, CityService)
    assert isinstance(map_service, MapService)
    assert isinstance(share_service, ShareService)
    assert isinstance(chat_service, ChatService)
    assert isinstance(artifact_service, ArtifactService)
    assert container.resolve("CityService") is city_service
    assert container.resolve("MapService") is map_service
    assert container.resolve("ShareService") is share_service
    assert container.resolve("ChatService") is chat_service
    assert container.resolve("ArtifactService") is artifact_service


def test_build_default_container_resolves_file_session_repository_by_default():
    container = build_default_container()

    session_repository = container.resolve("SessionRepository")

    assert isinstance(session_repository, FileSessionRepository)


def test_build_default_container_resolves_postgres_backends_when_configured(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'bootstrap.db'}"
    monkeypatch.setenv("MOYUAN_DB_BACKEND", "postgres")
    monkeypatch.setenv("MOYUAN_POSTGRES_DSN", database_url)
    monkeypatch.setenv("MOYUAN_DB_POOL_MIN", "1")
    monkeypatch.setenv("MOYUAN_DB_POOL_MAX", "2")
    server_config.reload()

    try:
        container = build_default_container()
        session_repository = container.resolve("SessionRepository")
        share_repository = container.resolve("ShareLinkRepository")

        assert isinstance(session_repository, PostgresSessionRepository)
        assert isinstance(share_repository, PostgresShareLinkRepository)
    finally:
        monkeypatch.delenv("MOYUAN_DB_BACKEND", raising=False)
        monkeypatch.delenv("MOYUAN_POSTGRES_DSN", raising=False)
        monkeypatch.delenv("MOYUAN_DB_POOL_MIN", raising=False)
        monkeypatch.delenv("MOYUAN_DB_POOL_MAX", raising=False)
        server_config.reload()


def test_initialize_dependency_container_returns_shared_container():
    first = initialize_dependency_container()
    second = initialize_dependency_container()

    assert first is second
    assert first.has_provider("SessionService") is True
