from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_evaluation_service
from app.domain.evaluation import RankingEvaluationRequest, RankingEvaluationRun
from app.services.evaluation_service import EvaluationService, SearchNotEvaluableError

router = APIRouter(prefix="/searches")


@router.post(
    "/{search_id}/evaluations",
    response_model=RankingEvaluationRun,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_search_ranking(
    search_id: UUID,
    request: RankingEvaluationRequest,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> RankingEvaluationRun:
    try:
        return await service.evaluate(search_id, request)
    except SearchNotEvaluableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
