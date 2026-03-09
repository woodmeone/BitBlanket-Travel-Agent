"""Dependency provider package for FastAPI route wiring."""

# Dependencies Package
from .container import Container, get_container
from .providers import provide_session_repository, provide_chat_service

__all__ = ['Container', 'get_container', 'provide_session_repository', 'provide_chat_service']
