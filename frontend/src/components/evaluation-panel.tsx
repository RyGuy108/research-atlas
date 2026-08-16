"use client";

import { useState } from "react";

import {
  evaluateRanking,
  type ExtractionBatch,
  type RankingEvaluationRun,
} from "@/lib/api";

export function EvaluationPanel({ batch }: { batch: ExtractionBatch }) {
  const [scores, setScores] = useState<Record<string, number>>(() =>
    Object.fromEntries(batch.completed.map((paper) => [paper.paper_id, 0])),
  );
  const [result, setResult] = useState<RankingEvaluationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submitEvaluation() {
    setSubmitting(true);
    setError(null);
    try {
      setResult(
        await evaluateRanking(
          batch.search_id,
          batch.completed.map((paper) => ({
            paper_id: paper.paper_id,
            relevance: scores[paper.paper_id] ?? 0,
          })),
          Math.min(10, batch.completed.length),
        ),
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Evaluation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="evaluationPanel" aria-labelledby="evaluation-heading">
      <div className="evaluationIntro">
        <div>
          <p className="eyebrow">Human evaluation</p>
          <h2 id="evaluation-heading">Measure ranking quality.</h2>
        </div>
        <p>
          Grade the extracted shortlist from irrelevant to highly relevant. Each run is persisted
          so ranking experiments can be compared with standard information-retrieval metrics.
        </p>
      </div>

      <div className="judgmentList">
        {batch.completed.map((paper) => (
          <label key={paper.paper_id}>
            <span><strong>#{paper.rank}</strong> {paper.title}</span>
            <select
              aria-label={`Relevance for ${paper.title}`}
              onChange={(event) =>
                setScores((current) => ({
                  ...current,
                  [paper.paper_id]: Number(event.target.value),
                }))
              }
              value={scores[paper.paper_id]}
            >
              <option value={0}>0 · Irrelevant</option>
              <option value={1}>1 · Related</option>
              <option value={2}>2 · Relevant</option>
              <option value={3}>3 · Essential</option>
            </select>
          </label>
        ))}
      </div>

      <div className="evaluationFooter">
        <button className="secondaryButton" disabled={submitting} onClick={submitEvaluation} type="button">
          {submitting ? "Calculating…" : "Save evaluation"}
        </button>
        {error && <p className="evaluationError" role="alert">{error}</p>}
        {result && (
          <dl className="metricResults" aria-live="polite">
            <div><dt>Recall@{result.metrics.k}</dt><dd>{result.metrics.recall.toFixed(3)}</dd></div>
            <div><dt>MRR</dt><dd>{result.metrics.reciprocal_rank.toFixed(3)}</dd></div>
            <div><dt>nDCG</dt><dd>{result.metrics.ndcg.toFixed(3)}</dd></div>
          </dl>
        )}
      </div>
    </section>
  );
}
