from uuid import UUID

from app.domain.landscape import ClusteredLandscape, LandscapeSynthesis


class LandscapeValidationError(ValueError):
    """Raised when a synthesis references papers or clusters outside its supplied landscape."""


def validate_landscape_synthesis(
    clustered: ClusteredLandscape,
    synthesis: LandscapeSynthesis,
) -> None:
    known_papers = {position.paper_id for position in clustered.positions}
    cluster_members = {cluster.cluster_id: set(cluster.paper_ids) for cluster in clustered.clusters}
    narrative_ids = [narrative.cluster_id for narrative in synthesis.clusters]
    if len(narrative_ids) != len(set(narrative_ids)):
        raise LandscapeValidationError("cluster narratives must have unique cluster IDs")
    if set(narrative_ids) != set(cluster_members):
        raise LandscapeValidationError("cluster narratives must cover every computed cluster")

    for narrative in synthesis.clusters:
        cited = set(narrative.evidence_paper_ids)
        if not cited <= cluster_members[narrative.cluster_id]:
            raise LandscapeValidationError("cluster narrative cites a paper outside its cluster")

    for relationship in synthesis.relationships:
        referenced = {relationship.source_paper_id, relationship.target_paper_id}
        if len(referenced) != 2:
            raise LandscapeValidationError("a relationship must connect two different papers")
        _require_known_papers(referenced, known_papers)
    for tension in synthesis.tensions:
        _require_known_papers(set(tension.evidence_paper_ids), known_papers)
    for question in synthesis.open_questions:
        _require_known_papers(set(question.evidence_paper_ids), known_papers)


def _require_known_papers(referenced: set[UUID], known: set[UUID]) -> None:
    if not referenced <= known:
        raise LandscapeValidationError("synthesis cites an unknown paper")
