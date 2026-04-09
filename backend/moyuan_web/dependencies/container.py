"""Simple dependency container and default-container bootstrap entrypoint."""

from __future__ import annotations

from typing import Any, Callable


class Container:
    """Register and resolve application services by name."""

    def __init__(self) -> None:
        """Initialize provider and singleton instance registries."""
        self._providers: dict[str, tuple[Callable[[], Any], bool]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, provider: Callable[[], Any], singleton: bool = True) -> None:
        """Register one provider callable under the given service name."""
        self._providers[name] = (provider, singleton)

    def has_provider(self, name: str) -> bool:
        """Return whether the container knows how to build the requested service."""
        return name in self._providers

    def resolve(self, name: str) -> Any:
        """Resolve one service instance, reusing singleton instances when configured."""
        if name not in self._providers:
            raise ValueError(f"Dependency not found: {name}")

        provider, singleton = self._providers[name]
        if singleton and name in self._instances:
            return self._instances[name]

        instance = provider()
        if singleton:
            self._instances[name] = instance
        return instance


_container: Container | None = None
_container_signature: tuple[Any, ...] | None = None


def _current_container_signature() -> tuple[Any, ...] | None:
    """Return persistence-related config used to invalidate the shared container."""

    try:
        from ..config.runtime import get_server_config

        server_config = get_server_config()
        return (
            server_config.db_backend,
            server_config.postgres_dsn,
            server_config.db_pool_min,
            server_config.db_pool_max,
        )
    except Exception:
        return None


def build_default_container() -> Container:
    """Create a container preloaded with the application's default services."""
    from ..bootstrap_services import register_default_services

    container = Container()
    register_default_services(container)
    return container


def get_container() -> Container:
    """Return the shared default dependency container."""
    global _container, _container_signature
    signature = _current_container_signature()
    if _container is None or _container_signature != signature:
        _container = build_default_container()
        _container_signature = signature
    return _container


def reset_container() -> None:
    """Drop the shared container so tests and config reloads can rebuild dependencies."""

    global _container, _container_signature
    _container = None
    _container_signature = None
