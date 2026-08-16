from collections.abc import Sequence
from typing import Protocol

from app.domain.paper import Paper
from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy


class PaperRanker(Protocol):
    strategy: RankingStrategy

    def rank(
        self,
        query: str,
        papers: Sequence[Paper],
        *,
        limit: int | None = None,
    ) -> list[RankedPaper]: ...
