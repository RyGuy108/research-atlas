from pydantic import BaseModel, ConfigDict, Field

from app.domain.paper import Paper
from app.domain.search import RankingStrategy


class RankedPaper(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper: Paper
    rank: int = Field(ge=1)
    score: float
    strategy: RankingStrategy
