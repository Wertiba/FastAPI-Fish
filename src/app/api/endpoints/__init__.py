from fastapi import APIRouter

from .health import router as health_router
from .metrics import router as metrics_router

router = APIRouter()

router.include_router(health_router)
router.include_router(metrics_router)
