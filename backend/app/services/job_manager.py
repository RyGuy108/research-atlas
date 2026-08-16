import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobSnapshot,
    PipelineJobStage,
    PipelineJobStatus,
    PipelineProgress,
)

ProgressReporter = Callable[[PipelineProgress], Awaitable[None]]


class PipelineRunner(Protocol):
    async def run(
        self,
        request: PipelineJobRequest,
        report: ProgressReporter,
    ) -> PipelineArtifacts: ...


class PipelineJobNotFoundError(LookupError):
    """Raised when a caller requests an unknown pipeline job."""


class PipelineJobManager:
    def __init__(self, runner: PipelineRunner) -> None:
        self._runner = runner
        self._jobs: dict[UUID, PipelineJobSnapshot] = {}
        self._subscribers: defaultdict[UUID, set[asyncio.Queue[PipelineJobSnapshot]]] = defaultdict(
            set
        )
        self._tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()

    async def start(self, request: PipelineJobRequest) -> PipelineJobSnapshot:
        snapshot = PipelineJobSnapshot()
        async with self._lock:
            self._jobs[snapshot.job_id] = snapshot

        # Hold strong task references so jobs cannot disappear while the request is running.
        task = asyncio.create_task(self._execute(snapshot.job_id, request))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return snapshot

    async def get(self, job_id: UUID) -> PipelineJobSnapshot:
        async with self._lock:
            snapshot = self._jobs.get(job_id)
        if snapshot is None:
            raise PipelineJobNotFoundError(f"pipeline job {job_id} was not found")
        return snapshot

    async def subscribe(self, job_id: UUID) -> AsyncIterator[PipelineJobSnapshot]:
        queue: asyncio.Queue[PipelineJobSnapshot] = asyncio.Queue()
        snapshot = await self.get(job_id)
        if snapshot.terminal:
            yield snapshot
            return

        self._subscribers[job_id].add(queue)
        try:
            yield snapshot
            while True:
                snapshot = await queue.get()
                yield snapshot
                if snapshot.terminal:
                    return
        finally:
            subscribers = self._subscribers.get(job_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    self._subscribers.pop(job_id, None)

    async def close(self) -> None:
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute(self, job_id: UUID, request: PipelineJobRequest) -> None:
        await self._update(
            job_id,
            status=PipelineJobStatus.RUNNING,
            stage=PipelineJobStage.DISCOVER,
            percent=5,
            message="Searching scholarly indexes",
        )

        async def report(progress: PipelineProgress) -> None:
            current = await self.get(job_id)
            if progress.percent < current.percent:
                raise ValueError("pipeline progress cannot move backwards")
            await self._update(
                job_id,
                stage=progress.stage,
                percent=progress.percent,
                message=progress.message,
                artifacts=progress.artifacts,
            )

        try:
            artifacts = await self._runner.run(request, report)
        except asyncio.CancelledError:
            await self._update(
                job_id,
                status=PipelineJobStatus.FAILED,
                message="Pipeline job was cancelled",
                error="server shutdown interrupted the pipeline",
            )
            raise
        except Exception as error:
            await self._update(
                job_id,
                status=PipelineJobStatus.FAILED,
                message="Pipeline stopped",
                error=str(error),
            )
            return

        await self._update(
            job_id,
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
        async with self._lock:
            current = self._jobs[job_id]
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
            self._jobs[job_id] = snapshot

        for queue in tuple(self._subscribers.get(job_id, ())):
            queue.put_nowait(snapshot)
        return snapshot
