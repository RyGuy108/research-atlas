"use client";

import { useMemo, useState, type CSSProperties } from "react";

import type { ExtractionBatch, ResearchLandscape as Landscape } from "@/lib/api";

const clusterColors = ["#7ce3b4", "#f1c979", "#92b8ff", "#d9a5ff", "#ff9f91"];

interface ResearchLandscapeProps {
  landscape: Landscape;
  extractions: ExtractionBatch;
}

export function ResearchLandscape({ landscape, extractions }: ResearchLandscapeProps) {
  const { clustered, synthesis_run: synthesisRun } = landscape;
  const synthesis = synthesisRun.synthesis;
  const [selectedPaperId, setSelectedPaperId] = useState(clustered.positions[0]?.paper_id ?? "");

  const papers = useMemo(
    () => new Map(extractions.completed.map((item) => [item.paper_id, item])),
    [extractions.completed],
  );
  const positions = useMemo(
    () => new Map(clustered.positions.map((position) => [position.paper_id, position])),
    [clustered.positions],
  );
  const selectedPaper = papers.get(selectedPaperId);
  const selectedPosition = positions.get(selectedPaperId);
  const selectedCluster = synthesis.clusters.find(
    (cluster) => cluster.cluster_id === selectedPosition?.cluster_id,
  );

  const point = (coordinate: number) => 8 + ((coordinate + 1) / 2) * 84;
  const paperLabel = (paperId: string) => {
    const paper = papers.get(paperId);
    return paper ? `Paper ${paper.rank}` : `Paper ${paperId.slice(0, 4)}`;
  };

  return (
    <section className="landscapeSection" aria-labelledby="landscape-heading">
      <div className="landscapeIntro">
        <div>
          <p className="eyebrow">Research landscape</p>
          <h2 id="landscape-heading">A field, organized by evidence.</h2>
        </div>
        <p>{synthesis.overview}</p>
      </div>

      <div className="mapLayout">
        <div className="mapPanel">
          <div className="mapHeader">
            <span>Semantic reading map</span>
            <span>
              {clustered.clusters.length} themes · {clustered.similarity_edges.length} links
            </span>
          </div>
          <div className="mapCanvas">
            <svg aria-hidden="true" className="mapEdges" preserveAspectRatio="none">
              {clustered.similarity_edges.map((edge) => {
                const source = positions.get(edge.source_paper_id);
                const target = positions.get(edge.target_paper_id);
                if (!source || !target) return null;

                return (
                  <line
                    key={`${edge.source_paper_id}-${edge.target_paper_id}`}
                    opacity={0.18 + edge.similarity * 0.5}
                    strokeWidth={0.7 + edge.similarity * 1.8}
                    x1={`${point(source.x)}%`}
                    x2={`${point(target.x)}%`}
                    y1={`${point(source.y)}%`}
                    y2={`${point(target.y)}%`}
                  />
                );
              })}
            </svg>

            {clustered.positions.map((position) => {
              const paper = papers.get(position.paper_id);
              const color = clusterColors[position.cluster_id % clusterColors.length];
              return (
                <button
                  aria-label={`${paperLabel(position.paper_id)}: ${paper?.title ?? "research paper"}`}
                  aria-pressed={selectedPaperId === position.paper_id}
                  className="mapNode"
                  key={position.paper_id}
                  onClick={() => setSelectedPaperId(position.paper_id)}
                  style={{
                    "--cluster-color": color,
                    left: `${point(position.x)}%`,
                    top: `${point(position.y)}%`,
                  } as CSSProperties}
                  title={paper?.title}
                  type="button"
                >
                  {paper?.rank ?? "·"}
                </button>
              );
            })}
          </div>

          <div className="mapLegend" aria-label="Research themes">
            {synthesis.clusters.map((cluster) => (
              <span key={cluster.cluster_id}>
                <i style={{ background: clusterColors[cluster.cluster_id % clusterColors.length] }} />
                {cluster.name}
              </span>
            ))}
          </div>
        </div>

        <aside className="paperInspector" aria-live="polite">
          <p className="inspectorLabel">Selected paper</p>
          {selectedPaper && selectedPosition ? (
            <>
              <span className="inspectorRank">#{selectedPaper.rank} · {selectedCluster?.name}</span>
              <h3>{selectedPaper.title}</h3>
              <dl>
                <div><dt>Cluster fit</dt><dd>{Math.round(selectedPosition.membership_score * 100)}%</dd></div>
                <div><dt>Model</dt><dd>{selectedPaper.run.model}</dd></div>
              </dl>
              <div className="inspectorClaim">
                <span>Problem</span>
                <p>{selectedPaper.run.extraction.problem.summary}</p>
              </div>
              <div className="inspectorClaim">
                <span>Method</span>
                <p>{selectedPaper.run.extraction.method.summary}</p>
              </div>
            </>
          ) : (
            <p>Select a node to inspect its evidence-backed notes.</p>
          )}
        </aside>
      </div>

      <div className="themeGrid">
        {synthesis.clusters.map((cluster) => (
          <article key={cluster.cluster_id}>
            <span style={{ color: clusterColors[cluster.cluster_id % clusterColors.length] }}>
              Theme {String(cluster.cluster_id + 1).padStart(2, "0")} · {cluster.evidence_paper_ids.length} papers
            </span>
            <h3>{cluster.name}</h3>
            <p>{cluster.summary}</p>
          </article>
        ))}
      </div>

      <div className="synthesisGrid">
        <section aria-labelledby="relationships-heading">
          <p className="eyebrow">Connections</p>
          <h3 id="relationships-heading">How the work relates</h3>
          <div className="insightList">
            {synthesis.relationships.length > 0 ? synthesis.relationships.map((relationship) => (
              <article key={`${relationship.source_paper_id}-${relationship.target_paper_id}-${relationship.kind}`}>
                <span className={`relationshipKind relationshipKind--${relationship.kind}`}>
                  {relationship.kind.replace("_", " ")}
                </span>
                <p>{relationship.summary}</p>
                <small>{paperLabel(relationship.source_paper_id)} → {paperLabel(relationship.target_paper_id)}</small>
              </article>
            )) : <p className="emptyInsight">No strong cross-paper relationships were identified.</p>}
          </div>
        </section>

        <section aria-labelledby="questions-heading">
          <p className="eyebrow">Research frontier</p>
          <h3 id="questions-heading">What remains open</h3>
          <div className="insightList">
            {synthesis.open_questions.map((question, index) => (
              <article key={question.question}>
                <span className="questionNumber">Q{String(index + 1).padStart(2, "0")}</span>
                <h4>{question.question}</h4>
                <p>{question.rationale}</p>
                <small>{question.evidence_paper_ids.map(paperLabel).join(" · ")}</small>
              </article>
            ))}
          </div>
        </section>
      </div>

      {synthesis.tensions.length > 0 && (
        <section className="tensions" aria-labelledby="tensions-heading">
          <p className="eyebrow">Unresolved tensions</p>
          <h3 id="tensions-heading">Where the evidence pulls in different directions</h3>
          <div>
            {synthesis.tensions.map((tension) => (
              <article key={tension.summary}>
                <p>{tension.summary}</p>
                <small>{tension.evidence_paper_ids.map(paperLabel).join(" · ")}</small>
              </article>
            ))}
          </div>
        </section>
      )}

      <p className="modelFootnote">
        Synthesized with {synthesisRun.model} · {synthesisRun.usage.total_tokens.toLocaleString()} tokens · {Math.round(synthesisRun.elapsed_ms)} ms
      </p>
    </section>
  );
}
