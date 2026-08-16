from collections.abc import Sequence

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances, silhouette_score

from app.domain.landscape import (
    ClusteredLandscape,
    LandscapePaper,
    PaperPosition,
    SimilarityEdge,
    ThemeCluster,
)


class LandscapeClusterer:
    def __init__(
        self,
        *,
        max_clusters: int = 6,
        similarity_threshold: float = 0.2,
        random_state: int = 42,
    ) -> None:
        if max_clusters < 2:
            raise ValueError("max_clusters must be at least two")
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between zero and one")
        self._max_clusters = max_clusters
        self._similarity_threshold = similarity_threshold
        self._random_state = random_state

    def cluster(self, papers: Sequence[LandscapePaper]) -> ClusteredLandscape:
        """Create reproducible themes, graph edges, and map coordinates from extractions."""
        if not papers:
            raise ValueError("at least one extracted paper is required")

        documents = [_extraction_text(paper) for paper in papers]
        matrix = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        ).fit_transform(documents)
        labels, cluster_score = self._select_clusters(matrix.toarray())
        distances = pairwise_distances(matrix, metric="cosine")
        coordinates = _coordinates(matrix.toarray())

        clusters = self._describe_clusters(papers, labels)
        positions = _positions(papers, labels, matrix.toarray(), coordinates)
        edges = _similarity_edges(papers, distances, self._similarity_threshold)
        return ClusteredLandscape(
            clusters=tuple(clusters),
            positions=tuple(positions),
            similarity_edges=tuple(edges),
            silhouette_score=cluster_score,
        )

    def _select_clusters(self, vectors: np.ndarray) -> tuple[np.ndarray, float | None]:
        paper_count = len(vectors)
        unique_count = len(np.unique(vectors, axis=0))
        max_k = min(self._max_clusters, paper_count - 1, unique_count)
        if max_k < 2:
            return np.zeros(paper_count, dtype=int), None

        best_labels = np.zeros(paper_count, dtype=int)
        best_score: float | None = None
        for cluster_count in range(2, max_k + 1):
            labels = KMeans(
                n_clusters=cluster_count,
                random_state=self._random_state,
                n_init=10,
            ).fit_predict(vectors)
            if len(set(labels)) < 2:
                continue
            score = float(silhouette_score(vectors, labels, metric="cosine"))
            if best_score is None or score > best_score:
                best_labels = labels
                best_score = score
        return best_labels, best_score

    def _describe_clusters(
        self,
        papers: Sequence[LandscapePaper],
        labels: np.ndarray,
    ) -> list[ThemeCluster]:
        # Fit once more only to recover readable feature names for deterministic labels.
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        label_matrix = vectorizer.fit_transform([_extraction_text(paper) for paper in papers])
        features = vectorizer.get_feature_names_out()
        clusters: list[ThemeCluster] = []
        for cluster_id in sorted(set(int(label) for label in labels)):
            indexes = np.flatnonzero(labels == cluster_id)
            mean_weights = np.asarray(label_matrix[indexes].mean(axis=0)).ravel()
            top_indexes = mean_weights.argsort()[::-1][:3]
            terms = [features[index] for index in top_indexes if mean_weights[index] > 0]
            clusters.append(
                ThemeCluster(
                    cluster_id=cluster_id,
                    label=" · ".join(terms) or f"theme {cluster_id + 1}",
                    paper_ids=tuple(papers[int(index)].paper_id for index in indexes),
                )
            )
        return clusters


def _extraction_text(paper: LandscapePaper) -> str:
    extraction = paper.extraction
    claims = (
        extraction.problem,
        extraction.method,
        *extraction.results,
        *extraction.contributions,
        *extraction.limitations,
    )
    return " ".join(
        (
            paper.title,
            " ".join(extraction.keywords),
            " ".join(extraction.keywords),
            *(claim.summary for claim in claims),
        )
    )


def _coordinates(vectors: np.ndarray) -> np.ndarray:
    paper_count, feature_count = vectors.shape
    if paper_count == 1:
        return np.zeros((1, 2))
    if feature_count == 1:
        coordinates = np.column_stack((vectors[:, 0], np.zeros(paper_count)))
    else:
        coordinates = PCA(n_components=2).fit_transform(vectors)
    scale = np.max(np.abs(coordinates), axis=0)
    scale[scale == 0] = 1
    return np.asarray(coordinates / scale)


def _positions(
    papers: Sequence[LandscapePaper],
    labels: np.ndarray,
    vectors: np.ndarray,
    coordinates: np.ndarray,
) -> list[PaperPosition]:
    positions: list[PaperPosition] = []
    for index, paper in enumerate(papers):
        members = vectors[labels == labels[index]]
        centroid = members.mean(axis=0)
        distance = float(np.linalg.norm(vectors[index] - centroid))
        positions.append(
            PaperPosition(
                paper_id=paper.paper_id,
                cluster_id=int(labels[index]),
                membership_score=1 / (1 + distance),
                x=float(coordinates[index, 0]),
                y=float(coordinates[index, 1]),
            )
        )
    return positions


def _similarity_edges(
    papers: Sequence[LandscapePaper],
    distances: np.ndarray,
    threshold: float,
) -> list[SimilarityEdge]:
    edges: list[SimilarityEdge] = []
    for source in range(len(papers)):
        for target in range(source + 1, len(papers)):
            similarity = max(0.0, 1 - float(distances[source, target]))
            if similarity >= threshold:
                edges.append(
                    SimilarityEdge(
                        source_paper_id=papers[source].paper_id,
                        target_paper_id=papers[target].paper_id,
                        similarity=similarity,
                    )
                )
    return edges
