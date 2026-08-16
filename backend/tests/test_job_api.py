from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import AppEnvironment, Settings
from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobStage,
    PipelineProgress,
)
from app.main import create_app
from app.services.job_manager import PipelineJobManager, ProgressReporter


class FakeRunner:
    async def run(
        self,
        request: PipelineJobRequest,
        report: ProgressReporter,
    ) -> PipelineArtifacts:
        await report(
            PipelineProgress(
                stage=PipelineJobStage.MAP,
                percent=80,
                message="Mapping papers",
            )
        )
        return PipelineArtifacts()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_app() -> tuple[FastAPI, PipelineJobManager]:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    manager = PipelineJobManager(FakeRunner())
    app.state.pipeline_job_manager = manager
    return app, manager


@pytest.mark.anyio
async def test_job_api_starts_reads_and_streams_pipeline_progress() -> None:
    app, manager = make_test_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        created = await client.post(
            "/api/v1/pipeline-jobs",
            json={"search": {"topic": "adaptive retrieval"}, "extraction_limit": 3},
        )
        job_id = created.json()["job_id"]
        await _wait_until_terminal(manager, job_id)
        loaded = await client.get(f"/api/v1/pipeline-jobs/{job_id}")
        streamed = await client.get(f"/api/v1/pipeline-jobs/{job_id}/events")

    assert created.status_code == 202
    assert loaded.json()["status"] == "succeeded"
    assert "event: snapshot" in streamed.text
    assert '"percent":100' in streamed.text
    await manager.close()


@pytest.mark.anyio
async def test_job_api_returns_not_found_for_unknown_job() -> None:
    app, manager = make_test_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/pipeline-jobs/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    await manager.close()


async def _wait_until_terminal(
    manager: PipelineJobManager,
    job_id: str,
) -> None:
    async for snapshot in manager.subscribe(UUID(job_id)):
        if snapshot.terminal:
            return
