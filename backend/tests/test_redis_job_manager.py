import fakeredis.aioredis
import pytest

from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobStage,
    PipelineJobStatus,
    PipelineProgress,
)
from app.domain.search import SearchRequest
from app.services.job_manager import ProgressReporter
from app.services.redis_job_manager import RedisPipelineJobs


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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
                message=f"Mapping {request.search.topic}",
            )
        )
        return PipelineArtifacts()


@pytest.mark.anyio
async def test_redis_manager_queues_executes_and_retains_job_snapshot() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    manager = RedisPipelineJobs(redis, queue_name="test-jobs", ttl_seconds=300)
    created = await manager.start(
        PipelineJobRequest(search=SearchRequest(topic="adaptive retrieval"))
    )

    processed = await manager.run_next(FakeRunner(), timeout=1)
    loaded = await manager.get(created.job_id)
    snapshots = [snapshot async for snapshot in manager.subscribe(created.job_id)]

    assert processed is True
    assert loaded.status is PipelineJobStatus.SUCCEEDED
    assert snapshots == [loaded]
    assert await redis.llen("test-jobs:processing") == 0
    await manager.close()


@pytest.mark.anyio
async def test_redis_manager_requeues_interrupted_work() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    manager = RedisPipelineJobs(redis, queue_name="test-jobs", ttl_seconds=300)
    await redis.lpush("test-jobs:processing", "job-one", "job-two")

    recovered = await manager.requeue_interrupted()

    assert recovered == 2
    assert await redis.llen("test-jobs") == 2
    assert await redis.llen("test-jobs:processing") == 0
    await manager.close()
