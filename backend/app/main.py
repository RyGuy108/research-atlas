from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.services.job_manager import PipelineJobManager
from app.services.pipeline_runner import AtlasPipelineRunner


def create_app(settings: Settings | None = None) -> FastAPI:
    """Assemble the API in one place so tests and future workers share the same setup."""
    resolved_settings = settings or get_settings()
    job_manager = PipelineJobManager(AtlasPipelineRunner(resolved_settings))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await job_manager.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        description="Conference-aware research discovery and evaluation.",
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.pipeline_job_manager = job_manager
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=resolved_settings.api_prefix)

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"name": "Research Atlas API", "docs": "/docs"}

    return application


app = create_app()
