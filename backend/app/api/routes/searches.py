from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_search_service
from app.domain.search import SearchRequest
from app.domain.search_result import SearchOutcome
from app.services.search_service import SearchService, SearchUnavailableError

router = APIRouter(prefix="/searches")


@router.post("", response_model=SearchOutcome, status_code=status.HTTP_201_CREATED)
async def create_search(
    request: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutcome:
    try:
        return await service.search(request)
    except SearchUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
