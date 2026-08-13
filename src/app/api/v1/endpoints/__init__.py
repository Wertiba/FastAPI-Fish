from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as ping_router
from .metrics import router as metrics_router
from .users import router as user_router

router = APIRouter(prefix="/v1")

router.include_router(ping_router)
router.include_router(metrics_router)
router.include_router(auth_router)
router.include_router(user_router)
