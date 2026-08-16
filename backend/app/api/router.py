from fastapi import APIRouter

from app.api.routes import health, jobs, searches

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(searches.router, tags=["searches"])
api_router.include_router(jobs.router, tags=["pipeline jobs"])
