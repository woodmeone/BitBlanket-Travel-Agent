"""Route package exports.

Business routers are mounted under `/api` in `shuai_web.main`.
Documentation routers are mounted without API prefix.
"""

from .api_docs import router as api_docs_router
from .city import router as city_router
from .health import router as health_router
from .map import router as map_router
from .model import router as model_router
from .session import router as session_router
from .share import router as share_router

__all__ = [
    "api_docs_router",
    "city_router",
    "health_router",
    "map_router",
    "model_router",
    "session_router",
    "share_router",
]
