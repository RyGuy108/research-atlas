from collections.abc import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer

from app.domain.paper import Paper
from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy


class TfidfRanker:
    strategy = RankingStrategy.KEYWORD

    def rank(
        self,
        query: str,
        papers: Sequence[Paper],
        *,
        limit: int | None = None,
    ) -> list[RankedPaper]:
        """Score title and abstract overlap with a reproducible TF-IDF baseline."""
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")
        if not papers:
            return []

        documents = [f"{paper.title}. {paper.abstract}" for paper in papers]
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        try:
            matrix = vectorizer.fit_transform([query, *documents])
            # TF-IDF rows are L2 normalized, so their dot product is cosine similarity.
            scores = (matrix[1:] @ matrix[0].T).toarray().ravel().tolist()
        except ValueError as error:
            if "empty vocabulary" not in str(error):
                raise
            scores = [0.0] * len(papers)

        ordered = sorted(
            enumerate(zip(papers, scores, strict=True)),
            key=lambda item: (-item[1][1], item[0]),
        )
        selected = ordered[:limit] if limit is not None else ordered
        return [
            RankedPaper(
                paper=paper,
                rank=rank,
                score=float(score),
                strategy=self.strategy,
            )
            for rank, (_, (paper, score)) in enumerate(selected, start=1)
        ]
