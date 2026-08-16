from collections.abc import Sequence
from typing import Any, Protocol

from app.domain.paper import Paper
from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"


class PairScorer(Protocol):
    def predict(self, pairs: Sequence[tuple[str, str]], *, batch_size: int) -> list[float]: ...


class SentenceTransformerScorer:
    def __init__(self, model_name: str = DEFAULT_MODEL, *, device: str | None = None) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:
            raise RuntimeError(
                "cross-encoder ranking requires the backend ml extra: pip install -e '.[ml]'"
            ) from error

        self._model: Any = CrossEncoder(model_name, device=device)

    def predict(self, pairs: Sequence[tuple[str, str]], *, batch_size: int) -> list[float]:
        scores = self._model.predict(
            list(pairs),
            batch_size=batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]


class CrossEncoderRanker:
    strategy = RankingStrategy.CROSS_ENCODER

    def __init__(
        self,
        scorer: PairScorer | None = None,
        *,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        batch_size: int = 16,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self._scorer = scorer
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size

    def rank(
        self,
        query: str,
        papers: Sequence[Paper],
        *,
        limit: int | None = None,
    ) -> list[RankedPaper]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")
        if not papers:
            return []

        scorer = self._scorer or SentenceTransformerScorer(
            self._model_name,
            device=self._device,
        )
        pairs = [(query, f"{paper.title}. {paper.abstract}") for paper in papers]
        scores = scorer.predict(pairs, batch_size=self._batch_size)
        if len(scores) != len(papers):
            raise ValueError("cross-encoder returned a different number of scores than papers")

        ordered = sorted(
            enumerate(zip(papers, scores, strict=True)),
            key=lambda item: (-item[1][1], item[0]),
        )
        selected = ordered[:limit] if limit is not None else ordered
        return [
            RankedPaper(
                paper=paper,
                rank=rank,
                score=score,
                strategy=self.strategy,
            )
            for rank, (_, (paper, score)) in enumerate(selected, start=1)
        ]
