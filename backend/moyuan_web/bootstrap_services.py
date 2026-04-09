"""Default dependency-container bootstrap helpers for web services."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .bootstrap import PROJECT_ROOT, ensure_project_paths
from .config.runtime import get_server_config

ensure_project_paths()

if TYPE_CHECKING:
    from .dependencies.container import Container


_repository: Any | None = None
_share_repository: Any | None = None
_artifact_service: Any | None = None
_session_service: Any | None = None
_chat_service: Any | None = None
_city_service: Any | None = None
_map_service: Any | None = None
_share_service: Any | None = None
_persistence_signature: tuple[Any, ...] | None = None


def _session_file_path() -> str:
    """Return the canonical file-backed sessions snapshot path."""

    return os.path.join(str(PROJECT_ROOT), "data", "sessions", "sessions.json")


def _share_links_file_path() -> str:
    """Return the canonical file-backed share-links snapshot path."""

    return os.path.join(str(PROJECT_ROOT), "data", "share_links.json")


def _reset_persistence_singletons() -> None:
    """Reset persistence-dependent singleton instances after backend reconfiguration."""

    global _repository, _share_repository
    global _artifact_service, _session_service, _chat_service, _share_service
    _repository = None
    _share_repository = None
    _artifact_service = None
    _session_service = None
    _chat_service = None
    _share_service = None


def _ensure_persistence_signature() -> Any:
    """Refresh persistence singletons when database settings change."""

    global _persistence_signature
    server_config = get_server_config()
    signature = (
        server_config.db_backend,
        server_config.postgres_dsn,
        server_config.db_pool_min,
        server_config.db_pool_max,
    )
    if _persistence_signature != signature:
        _reset_persistence_singletons()
        _persistence_signature = signature
    return server_config


def provide_session_repository():
    """Create or reuse the session repository singleton."""
    _ensure_persistence_signature()
    global _repository
    if _repository is None:
        server_config = get_server_config()
        if server_config.db_backend == "postgres":
            from .repositories.session_repository_postgres import PostgresSessionRepository

            if not server_config.postgres_dsn:
                raise ValueError("database.backend=postgres requires database.postgres_dsn")
            _repository = PostgresSessionRepository(
                server_config.postgres_dsn,
                pool_min=server_config.db_pool_min,
                pool_max=server_config.db_pool_max,
            )
        else:
            from .repositories.file_session_repository import FileSessionRepository

            _repository = FileSessionRepository(_session_file_path())
    return _repository


def provide_share_repository():
    """Create or reuse the share-link repository singleton."""

    _ensure_persistence_signature()
    global _share_repository
    if _share_repository is None:
        server_config = get_server_config()
        if server_config.db_backend == "postgres":
            from .repositories.postgres_share_link_repository import PostgresShareLinkRepository

            if not server_config.postgres_dsn:
                raise ValueError("database.backend=postgres requires database.postgres_dsn")
            _share_repository = PostgresShareLinkRepository(
                server_config.postgres_dsn,
                pool_min=server_config.db_pool_min,
                pool_max=server_config.db_pool_max,
            )
        else:
            from .repositories.file_share_link_repository import FileShareLinkRepository

            _share_repository = FileShareLinkRepository(_share_links_file_path())
    return _share_repository


def provide_session_service():
    """Create or reuse the session service singleton with memory integration."""
    _ensure_persistence_signature()
    global _session_service
    if _session_service is None:
        from .services.session_service import SessionService

        _session_service = SessionService(provide_session_repository())
    return _session_service


def provide_artifact_service():
    """Create or reuse the artifact service singleton."""
    _ensure_persistence_signature()
    global _artifact_service
    if _artifact_service is None:
        from .services.artifact_service import ArtifactService

        _artifact_service = ArtifactService(provide_session_repository())
    return _artifact_service


def provide_chat_service():
    """Create or reuse the chat service singleton."""
    _ensure_persistence_signature()
    global _chat_service
    if _chat_service is None:
        from .services.chat_service import ChatService

        _chat_service = ChatService(provide_session_repository())
    return _chat_service


def provide_city_service():
    """Create or reuse the city service singleton."""
    global _city_service
    if _city_service is None:
        from .services.city_service import CityService

        _city_service = CityService()
    return _city_service


def provide_map_service():
    """Create or reuse the map service singleton."""
    global _map_service
    if _map_service is None:
        from .services.map_service import MapService

        _map_service = MapService()
    return _map_service


def provide_share_service():
    """Create or reuse the share service singleton."""
    _ensure_persistence_signature()
    global _share_service
    if _share_service is None:
        from .services.share_service import ShareService

        _share_service = ShareService(repository=provide_share_repository())
    return _share_service


def provide_travel_agent():
    """Build one travel agent instance using configured LLM and tools."""
    from .config.runtime import get_llm_config_path
    from agent.travel_agent.graph.builder import build_travel_agent
    from agent.travel_agent.llm.langchain_adapter import create_from_yaml_config
    from agent.travel_agent.tools.travel_tools import get_travel_tools

    config_path = get_llm_config_path()
    llm_adapter = create_from_yaml_config(config_path)
    llm = llm_adapter.chat_model
    tools = get_travel_tools()
    return build_travel_agent(llm, tools)


def register_default_services(container: "Container") -> None:
    """Register the default web-service providers on the dependency container."""
    container.register("SessionRepository", provide_session_repository)
    container.register("ShareLinkRepository", provide_share_repository)
    container.register("ArtifactService", provide_artifact_service)
    container.register("SessionService", provide_session_service)
    container.register("ChatService", provide_chat_service)
    container.register("CityService", provide_city_service)
    container.register("MapService", provide_map_service)
    container.register("ShareService", provide_share_service)
    container.register("TravelAgent", provide_travel_agent)
