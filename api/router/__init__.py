from .v1.file import file_router
from .v1.knowledge import knowledge_router
from .v1.search import search_router
from .v1.user import user_router

__all__ = [
    "file_router",
    "knowledge_router",
    "search_router",
    "user_router",
]
