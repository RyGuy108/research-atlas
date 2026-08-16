import asyncio

import pytest

from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobSnapshot,
    PipelineJobStage,
    PipelineJobStatus,
    PipelineProgress,
)
from app.domain.search import SearchRequest
from app.services.job_manager import PipelineJobManager, PipelineJobNotFoundError, ProgressReporter


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class SuccessfulRunner:
    async def run(
        self,
        request: PipelineJobRequest,
        report: ProgressReporter,
    ) -> PipelineArtifacts:
        assert request.search.topic == "adaptive retrieval"
        await asyncio.sleep(0)
        await report(
            PipelineProgress(
                stage=PipelineJobStage.RERANK,
                percent=35,
                message="Reranking candidates",
            )
        )
        await report(
            PipelineProgress(
                stage=PipelineJobStage.MAP,
                percent=85,
                message="Synthesizing themes",
            )
        )
        return PipelineArtifacts()


class FailingRunner:
    async def run(
        self,
        request: PipelineJobRequest,
        report: ProgressReporter,
    ) -> PipelineArtifacts:
        raise RuntimeError("provider quota exhausted")


@pytest.mark.anyio
async def test_manager_streams_monotonic_progress_until_success() -> None:
    manager = PipelineJobManager(SuccessfulRunner())
    created = await manager.start(
        PipelineJobRequest(search=SearchRequest(topic="adaptive retrieval"))
    )

    snapshots = [snapshot async for snapshot in manager.subscribe(created.job_id)]

    assert snapshots[-1].status is PipelineJobStatus.SUCCEEDED
    assert snapshots[-1].stage is PipelineJobStage.COMPLETE
    assert snapshots[-1].percent == 100
    assert [snapshot.percent for snapshot in snapshots] == sorted(
        snapshot.percent for snapshot in snapshots
    )
    await manager.close()


@pytest.mark.anyio
async def test_manager_exposes_pipeline_failure_without_losing_job() -> None:
    manager = PipelineJobManager(FailingRunner())
    created = await manager.start(
        PipelineJobRequest(search=SearchRequest(topic="adaptive retrieval"))
    )

    snapshots = [snapshot async for snapshot in manager.subscribe(created.job_id)]
    loaded = await manager.get(created.job_id)

    assert snapshots[-1].status is PipelineJobStatus.FAILED
    assert loaded.error == "provider quota exhausted"
    assert loaded.message == "Pipeline stopped"
    await manager.close()


@pytest.mark.anyio
async def test_manager_rejects_unknown_job() -> None:
    manager = PipelineJobManager(SuccessfulRunner())

    with pytest.raises(PipelineJobNotFoundError):
        await manager.get(PipelineJobSnapshot().job_id)

    await manager.close()


@pytest.mark.anyio
async def test_late_subscriber_receives_completed_snapshot_without_waiting() -> None:
    manager = PipelineJobManager(SuccessfulRunner())
    created = await manager.start(
        PipelineJobRequest(search=SearchRequest(topic="adaptive retrieval"))
    )
    while not (await manager.get(created.job_id)).terminal:
        await asyncio.sleep(0)

    snapshots = [snapshot async for snapshot in manager.subscribe(created.job_id)]

    assert len(snapshots) == 1
    assert snapshots[0].status is PipelineJobStatus.SUCCEEDED
    await manager.close()
