from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_extraction_service, get_search_service
from app.domain.extraction import ExtractionBatch
from app.domain.search import SearchRequest
from app.domain.search_result import SearchOutcome
from app.services.extraction_service import ExtractionService, NoExtractionTargetsError
from app.services.search_service import SearchService, SearchUnavailableError

router = APIRouter(prefix="/searches")


class ExtractionBatchRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=25)


@router.post("", response_model=SearchOutcome, status_code=status.HTTP_201_CREATED)
async def create_search(
    request: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutcome:
    try:
        return await service.search(request)
    except SearchUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post("/{search_id}/extractions", response_model=ExtractionBatch)
async def extract_search_papers(
    search_id: UUID,
    request: ExtractionBatchRequest,
    service: Annotated[ExtractionService, Depends(get_extraction_service)],
) -> ExtractionBatch:
    try:
        return await service.extract_search(search_id, limit=request.limit)
    except NoExtractionTargetsError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
