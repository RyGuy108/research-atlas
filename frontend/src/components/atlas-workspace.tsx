"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { ExtractionNotes } from "@/components/extraction-notes";
import { EvaluationPanel } from "@/components/evaluation-panel";
import { PaperResults } from "@/components/paper-results";
import { PipelineProgress, type PipelineStage } from "@/components/pipeline-progress";
import { ResearchLandscape } from "@/components/research-landscape";
import {
  buildLandscape,
  createSearch,
  extractPapers,
  startPipelineJob,
  subscribePipelineJob,
  type ExtractionBatch,
  type PipelineJobSnapshot,
  type RankingStrategy,
  type ResearchLandscape as ResearchLandscapeData,
  type SearchOutcome,
} from "@/lib/api";

type RunningStage = "search" | "extract" | "landscape" | null;

const automaticStageOrder = {
  discover: 0,
  rerank: 1,
  extract: 2,
  map: 3,
  complete: 4,
};

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something unexpected happened. Please try again.";
}

export function AtlasWorkspace() {
  const [topic, setTopic] = useState("adaptive retrieval for small language models");
  const [strategy, setStrategy] = useState<RankingStrategy>("cross_encoder");
  const [yearFrom, setYearFrom] = useState(2020);
  const [maxCandidates, setMaxCandidates] = useState(50);
  const [extractionLimit, setExtractionLimit] = useState(5);
  const [automatic, setAutomatic] = useState(false);
  const [search, setSearch] = useState<SearchOutcome | null>(null);
  const [extractions, setExtractions] = useState<ExtractionBatch | null>(null);
  const [landscape, setLandscape] = useState<ResearchLandscapeData | null>(null);
  const [job, setJob] = useState<PipelineJobSnapshot | null>(null);
  const [running, setRunning] = useState<RunningStage>(null);
  const [failedStage, setFailedStage] = useState<RunningStage>(null);
  const [error, setError] = useState<string | null>(null);
  const closeJobStream = useRef<(() => void) | null>(null);

  useEffect(() => () => closeJobStream.current?.(), []);

  const jobIsRunning = job?.status === "queued" || job?.status === "running";
  const isBusy = running !== null || jobIsRunning;

  const stages = useMemo<PipelineStage[]>(() => {
    if (job) {
      const current = automaticStageOrder[job.stage];
      const defaults = [
        "arXiv + OpenAlex",
        "Semantic relevance",
        "Evidence-linked notes",
        "Themes + tensions",
      ];

      return ["Discover", "Rerank", "Extract", "Map"].map((name, index) => {
        let state: PipelineStage["state"] = "waiting";
        if (job.status === "failed" && index === current) state = "error";
        else if (job.status === "succeeded" || index < current) state = "complete";
        else if ((job.status === "queued" || job.status === "running") && index === current) {
          state = "active";
        }

        return {
          name,
          detail: index === current && jobIsRunning ? job.message : defaults[index],
          state,
        };
      });
    }

    const stage = (
      name: string,
      detail: string,
      key: Exclude<RunningStage, null>,
      complete: boolean,
    ): PipelineStage => ({
      name,
      detail,
      state:
        failedStage === key
          ? "error"
          : running === key
            ? "active"
            : complete
              ? "complete"
              : "waiting",
    });

    return [
      stage("Discover", "arXiv + OpenAlex", "search", Boolean(search)),
      stage(
        "Rerank",
        strategy === "cross_encoder" ? "Cross-encoder" : "TF-IDF",
        "search",
        Boolean(search),
      ),
      stage("Extract", "Evidence-linked notes", "extract", Boolean(extractions)),
      stage("Map", "Themes + tensions", "landscape", Boolean(landscape)),
    ];
  }, [extractions, failedStage, job, jobIsRunning, landscape, running, search, strategy]);

  function applyJobSnapshot(snapshot: PipelineJobSnapshot) {
    setJob(snapshot);
    if (snapshot.artifacts.search) setSearch(snapshot.artifacts.search);
    if (snapshot.artifacts.extractions) setExtractions(snapshot.artifacts.extractions);
    if (snapshot.artifacts.landscape) setLandscape(snapshot.artifacts.landscape);
    if (snapshot.status === "failed") {
      setError(snapshot.error ?? "The pipeline stopped before it completed.");
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunning("search");
    setFailedStage(null);
    setError(null);
    closeJobStream.current?.();
    closeJobStream.current = null;
    setJob(null);

    // A new topic starts a new persisted pipeline, so downstream state must follow it.
    setSearch(null);
    setExtractions(null);
    setLandscape(null);

    try {
      if (automatic) {
        const created = await startPipelineJob({
          search: {
            topic,
            strategies: [strategy],
            filters: { year_from: yearFrom, max_candidates: maxCandidates },
          },
          extraction_limit: extractionLimit,
        });
        setJob(created);
        closeJobStream.current = subscribePipelineJob(created.job_id, applyJobSnapshot);
        return;
      }

      const outcome = await createSearch({
        topic,
        strategies: [strategy],
        filters: { year_from: yearFrom, max_candidates: maxCandidates },
      });
      setSearch(outcome);
    } catch (requestError) {
      setFailedStage("search");
      setError(errorMessage(requestError));
    } finally {
      setRunning(null);
    }
  }

  async function handleExtraction() {
    if (!search) return;
    setRunning("extract");
    setFailedStage(null);
    setError(null);
    setExtractions(null);
    setLandscape(null);

    try {
      const batch = await extractPapers(
        search.search_id,
        Math.min(extractionLimit, search.results.length),
      );
      setExtractions(batch);
    } catch (requestError) {
      setFailedStage("extract");
      setError(errorMessage(requestError));
    } finally {
      setRunning(null);
    }
  }

  async function handleLandscape() {
    if (!search) return;
    setRunning("landscape");
    setFailedStage(null);
    setError(null);
    setLandscape(null);

    try {
      setLandscape(await buildLandscape(search.search_id));
    } catch (requestError) {
      setFailedStage("landscape");
      setError(errorMessage(requestError));
    } finally {
      setRunning(null);
    }
  }

  const extractionCount = extractions?.completed.length ?? 0;

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Conference-aware literature intelligence</p>
        <h1>See the shape of a research field.</h1>
        <p className="lede">
          Search the scholarly record, rerank it semantically, and turn primary-source evidence
          into a map of methods, tensions, and unanswered questions.
        </p>

        <form className="searchPanel" onSubmit={handleSearch}>
          <label className="topicField">
            <span>Research topic</span>
            <input
              minLength={3}
              maxLength={240}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="What do you want to understand?"
              required
              type="search"
              value={topic}
            />
          </label>
          <button className="primaryButton" disabled={isBusy} type="submit">
            {jobIsRunning
              ? "Pipeline running…"
              : running === "search"
                ? "Finding papers…"
                : automatic
                  ? "Build atlas"
                  : "Find papers"}
          </button>
          <div className="searchOptions">
            <label>
              <span>Ranking</span>
              <select
                value={strategy}
                onChange={(event) => setStrategy(event.target.value as RankingStrategy)}
              >
                <option value="cross_encoder">Semantic reranker</option>
                <option value="keyword">TF-IDF baseline</option>
              </select>
            </label>
            <label>
              <span>Since</span>
              <input
                min={1950}
                max={new Date().getFullYear()}
                onChange={(event) => setYearFrom(Number(event.target.value))}
                type="number"
                value={yearFrom}
              />
            </label>
            <label>
              <span>Candidate pool</span>
              <select
                value={maxCandidates}
                onChange={(event) => setMaxCandidates(Number(event.target.value))}
              >
                <option value={25}>25 papers</option>
                <option value={50}>50 papers</option>
                <option value={100}>100 papers</option>
              </select>
            </label>
            <label className="automaticOption">
              <input
                checked={automatic}
                disabled={isBusy}
                onChange={(event) => setAutomatic(event.target.checked)}
                type="checkbox"
              />
              <span>Run all stages</span>
              <select
                aria-label="Papers to extract automatically"
                disabled={!automatic || isBusy}
                onChange={(event) => setExtractionLimit(Number(event.target.value))}
                value={extractionLimit}
              >
                {[2, 3, 5, 8].map((limit) => (
                  <option key={limit} value={limit}>
                    Top {limit}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </form>

        {jobIsRunning && job && (
          <div className="jobProgress" aria-live="polite">
            <div>
              <span>{job.message}</span>
              <strong>{job.percent}%</strong>
            </div>
            <div className="progressTrack" aria-hidden="true">
              <i style={{ width: `${job.percent}%` }} />
            </div>
          </div>
        )}

        <PipelineProgress stages={stages} />
      </section>

      {error && (
        <div className="notice notice--error globalNotice" role="alert">
          <strong>Pipeline stopped.</strong> {error}
        </div>
      )}

      {search && (
        <div className="workspace">
          <PaperResults outcome={search} />

          <section className="actionPanel" aria-labelledby="extract-heading">
            <div>
              <p className="eyebrow">Stage three</p>
              <h2 id="extract-heading">Read the shortlist with an LLM</h2>
              <p>
                Extract problems, methods, results, contributions, and limitations. Every claim
                must include an exact quote from the title or abstract.
              </p>
            </div>
            <div className="actionControls">
              <label>
                Papers to read
                <select
                  value={extractionLimit}
                  onChange={(event) => setExtractionLimit(Number(event.target.value))}
                >
                  {[2, 3, 5, 8].map((limit) => (
                    <option disabled={limit > search.results.length} key={limit} value={limit}>
                      Top {limit}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="secondaryButton"
                disabled={isBusy}
                onClick={handleExtraction}
                type="button"
              >
                {running === "extract"
                  ? "Reading papers…"
                  : extractions
                    ? "Run extraction again"
                    : "Extract evidence"}
              </button>
              <small>Uses the configured OpenAI model and records token usage.</small>
            </div>
          </section>

          {extractions && <ExtractionNotes batch={extractions} />}

          {extractions && extractions.completed.length > 0 && (
            <EvaluationPanel batch={extractions} />
          )}

          {extractions && (
            <section className="actionPanel" aria-labelledby="map-heading">
              <div>
                <p className="eyebrow">Stage four</p>
                <h2 id="map-heading">Synthesize the research landscape</h2>
                <p>
                  Cluster the extracted papers, connect similar work, and surface themes,
                  disagreements, and open questions.
                </p>
              </div>
              <div className="actionControls">
                <button
                  className="secondaryButton"
                  disabled={isBusy || extractionCount < 2}
                  onClick={handleLandscape}
                  type="button"
                >
                  {running === "landscape"
                    ? "Building landscape…"
                    : landscape
                      ? "Rebuild landscape"
                      : "Build landscape"}
                </button>
                <small>
                  {extractionCount < 2
                    ? "At least two successful extractions are required."
                    : `${extractionCount} evidence-backed papers ready.`}
                </small>
              </div>
            </section>
          )}

          {landscape && extractions && (
            <ResearchLandscape landscape={landscape} extractions={extractions} />
          )}
        </div>
      )}
    </>
  );
}
