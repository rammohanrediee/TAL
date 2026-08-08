from fastapi import APIRouter

from tal.api.routes import health
from tal.features.applications import router as applications
from tal.features.auth import router as auth
from tal.features.resumes import router as resumes
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(applications.router, tags=["applications"])
api_router.include_router(auth.router,tags=["auth"])
api_router.include_router(resumes.router, tags=["resumes"])
