from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.golf_courses import router as courses_router
from .endpoints.work_areas import router as work_areas_router
from .endpoints.work_reports import router as work_reports_router
from .endpoints.daily_plans import router as daily_plans_router
from .endpoints.users import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(courses_router)
router.include_router(work_reports_router)
router.include_router(work_areas_router)
router.include_router(daily_plans_router)
router.include_router(users_router)
