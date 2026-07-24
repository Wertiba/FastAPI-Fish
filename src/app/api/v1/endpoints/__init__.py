from fastapi import APIRouter

from .auth import router as auth_router
from .decisions import router as decision_router
from .event_catalog import router as event_catalog_router
from .events import router as event_router
from .experiments import router as experiment_router
from .flags import router as flag_router
from .health import router as ping_router
from .metric_catalog import router as metric_catalog_router
from .reports import router as report_router
from .reviews import router as review_router
from .users import router as user_router

router = APIRouter(prefix="/v1")


router.include_router(ping_router)
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(flag_router)
router.include_router(metric_catalog_router)
router.include_router(event_catalog_router)
router.include_router(experiment_router)
router.include_router(review_router)
router.include_router(decision_router)
router.include_router(event_router)
router.include_router(report_router)
