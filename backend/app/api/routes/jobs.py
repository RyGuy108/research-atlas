from collections.abc import AsyncIterator
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.security import require_write_access
from app.domain.job import PipelineJobRequest, PipelineJobSnapshot
from app.services.job_manager import PipelineJobNotFoundError, PipelineJobs

router = APIRouter(prefix="/pipeline-jobs")


def get_pipeline_job_manager(request: Request) -> PipelineJobs:
    return cast(PipelineJobs, request.app.state.pipeline_job_manager)


@router.post(
    "",
    response_model=PipelineJobSnapshot,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_write_access)],
)
async def start_pipeline_job(
    request: PipelineJobRequest,
    manager: Annotated[PipelineJobs, Depends(get_pipeline_job_manager)],
) -> PipelineJobSnapshot:
    return await manager.start(request)


@router.get("/{job_id}", response_model=PipelineJobSnapshot)
async def get_pipeline_job(
    job_id: UUID,
    manager: Annotated[PipelineJobs, Depends(get_pipeline_job_manager)],
) -> PipelineJobSnapshot:
    try:
        return await manager.get(job_id)
    except PipelineJobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{job_id}/events", response_class=StreamingResponse)
async def stream_pipeline_job(
    job_id: UUID,
    manager: Annotated[PipelineJobs, Depends(get_pipeline_job_manager)],
) -> StreamingResponse:
    try:
        await manager.get(job_id)
    except PipelineJobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    async def events() -> AsyncIterator[str]:
        yield "retry: 1500\n\n"
        async for snapshot in manager.subscribe(job_id):
            yield f"event: snapshot\ndata: {snapshot.model_dump_json()}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
