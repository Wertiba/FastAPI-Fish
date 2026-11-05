from .endpoints import router as ops_router
from .v1.endpoints import router as v1_router

__all__ = [
    "ops_router",
    "v1_router",
]
