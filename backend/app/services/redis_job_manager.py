import asyncio
from collections.abc import AsyncIterator, Awaitable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobSnapshot,
    PipelineJobStage,
    PipelineJobStatus,
    PipelineProgress,
)
from app.services.job_manager import (
    PipelineJobNotFoundError,
    PipelineRunner,
)


class QueuedPipelineJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: UUID
    request: PipelineJobRequest


class RedisPipelineJobs:
    def __init__(
        self,
        redis: Redis,
        *,
        queue_name: str,
        ttl_seconds: int,
    ) -> None:
        self._redis = redis
        self._queue_name = queue_name
        self._processing_name = f"{queue_name}:processing"
        self._ttl_seconds = ttl_seconds

    async def start(self, request: PipelineJobRequest) -> PipelineJobSnapshot:
        snapshot = PipelineJobSnapshot()
        queued = QueuedPipelineJob(job_id=snapshot.job_id, request=request)
        async with self._redis.pipeline(transaction=True) as transaction:
            transaction.set(
                self._job_key(snapshot.job_id),
                snapshot.model_dump_json(),
                ex=self._ttl_seconds,
            )
            transaction.lpush(self._queue_name, queued.model_dump_json())
            await transaction.execute()
        return snapshot

    async def get(self, job_id: UUID) -> PipelineJobSnapshot:
        payload = await self._redis.get(self._job_key(job_id))
        if payload is None:
            raise PipelineJobNotFoundError(f"pipeline job {job_id} was not found")
        return PipelineJobSnapshot.model_validate_json(payload)

    async def subscribe(self, job_id: UUID) -> AsyncIterator[PipelineJobSnapshot]:
        async with self._redis.pubsub() as pubsub:
            await pubsub.subscribe(self._channel(job_id))
            snapshot = await self.get(job_id)
            yield snapshot
            if snapshot.terminal:
                return

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )
                if message is None:
                    # Polling closes the tiny publish/subscribe race and detects expired jobs.
                    snapshot = await self.get(job_id)
                else:
                    snapshot = PipelineJobSnapshot.model_validate_json(message["data"])
                yield snapshot
                if snapshot.terminal:
                    return

    async def run_next(self, runner: PipelineRunner, *, timeout: int = 5) -> bool:
        payload = await cast(
            Awaitable[str | None],
            self._redis.brpoplpush(
                self._queue_name,
                self._processing_name,
                timeout=timeout,
            ),
        )
        if payload is None:
            return False

        queued = QueuedPipelineJob.model_validate_json(payload)
        try:
            await self._execute(queued, runner)
        finally:
            await cast(Awaitable[int], self._redis.lrem(self._processing_name, 1, payload))
        return True

    async def requeue_interrupted(self) -> int:
        count = 0
        while payload := await cast(Awaitable[str | None], self._redis.rpop(self._processing_name)):
            await cast(Awaitable[int], self._redis.lpush(self._queue_name, payload))
            count += 1
        return count

    async def close(self) -> None:
        await self._redis.aclose()

    async def _execute(self, queued: QueuedPipelineJob, runner: PipelineRunner) -> None:
        await self._update(
            queued.job_id,
            status=PipelineJobStatus.RUNNING,
            stage=PipelineJobStage.DISCOVER,
            percent=5,
            message="Searching scholarly indexes",
        )

        async def report(progress: PipelineProgress) -> None:
            current = await self.get(queued.job_id)
            if progress.percent < current.percent:
                raise ValueError("pipeline progress cannot move backwards")
            await self._update(
                queued.job_id,
                stage=progress.stage,
                percent=progress.percent,
                message=progress.message,
                artifacts=progress.artifacts,
            )

        try:
            artifacts = await runner.run(queued.request, report)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._update(
                queued.job_id,
                status=PipelineJobStatus.FAILED,
                message="Pipeline stopped",
                error=str(error),
            )
            return

        await self._update(
            queued.job_id,
            status=PipelineJobStatus.SUCCEEDED,
            stage=PipelineJobStage.COMPLETE,
            percent=100,
            message="Research atlas is ready",
            artifacts=artifacts,
        )

    async def _update(
        self,
        job_id: UUID,
        *,
        status: PipelineJobStatus | None = None,
        stage: PipelineJobStage | None = None,
        percent: int | None = None,
        message: str | None = None,
        artifacts: PipelineArtifacts | None = None,
        error: str | None = None,
    ) -> PipelineJobSnapshot:
        current = await self.get(job_id)
        snapshot = current.model_copy(
            update={
                "status": status or current.status,
                "stage": stage or current.stage,
                "percent": current.percent if percent is None else percent,
                "message": message or current.message,
                "artifacts": artifacts or current.artifacts,
                "error": error,
                "updated_at": datetime.now(UTC),
            }
        )
        payload = snapshot.model_dump_json()
        async with self._redis.pipeline(transaction=True) as transaction:
            transaction.set(self._job_key(job_id), payload, ex=self._ttl_seconds)
            transaction.publish(self._channel(job_id), payload)
            await transaction.execute()
        return snapshot

    @staticmethod
    def _job_key(job_id: UUID) -> str:
        return f"research-atlas:pipeline-job:{job_id}"

    @staticmethod
    def _channel(job_id: UUID) -> str:
        return f"research-atlas:pipeline-job:{job_id}:events"
