from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_extraction_service,
    get_landscape_service,
    get_search_service,
)
from app.api.security import require_write_access
from app.domain.extraction import ExtractionBatch
from app.domain.landscape import ResearchLandscape
from app.domain.search import SearchRequest
from app.domain.search_result import SearchOutcome
from app.services.extraction_service import ExtractionService, NoExtractionTargetsError
from app.services.landscape_service import (
    InsufficientLandscapeDataError,
    LandscapeService,
    LandscapeSynthesisUnavailableError,
)
from app.services.search_service import SearchService, SearchUnavailableError

router = APIRouter(prefix="/searches")


class ExtractionBatchRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=25)


@router.post(
    "",
    response_model=SearchOutcome,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_search(
    request: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutcome:
    try:
        return await service.search(request)
    except SearchUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post(
    "/{search_id}/extractions",
    response_model=ExtractionBatch,
    dependencies=[Depends(require_write_access)],
)
async def extract_search_papers(
    search_id: UUID,
    request: ExtractionBatchRequest,
    service: Annotated[ExtractionService, Depends(get_extraction_service)],
) -> ExtractionBatch:
    try:
        return await service.extract_search(search_id, limit=request.limit)
    except NoExtractionTargetsError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/{search_id}/landscape",
    response_model=ResearchLandscape,
    dependencies=[Depends(require_write_access)],
)
async def build_research_landscape(
    search_id: UUID,
    service: Annotated[LandscapeService, Depends(get_landscape_service)],
) -> ResearchLandscape:
    try:
        return await service.build(search_id)
    except InsufficientLandscapeDataError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except LandscapeSynthesisUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.get("/{search_id}/landscape", response_model=ResearchLandscape)
async def get_research_landscape(
    search_id: UUID,
    service: Annotated[LandscapeService, Depends(get_landscape_service)],
) -> ResearchLandscape:
    try:
        return await service.get(search_id)
    except InsufficientLandscapeDataError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
