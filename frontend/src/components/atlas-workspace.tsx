"use client";

import { FormEvent, useMemo, useState } from "react";

import { ExtractionNotes } from "@/components/extraction-notes";
import { PaperResults } from "@/components/paper-results";
import { PipelineProgress, type PipelineStage } from "@/components/pipeline-progress";
import {
  buildLandscape,
  createSearch,
  extractPapers,
  type ExtractionBatch,
  type RankingStrategy,
  type ResearchLandscape,
  type SearchOutcome,
} from "@/lib/api";

type RunningStage = "search" | "extract" | "landscape" | null;

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
  const [search, setSearch] = useState<SearchOutcome | null>(null);
  const [extractions, setExtractions] = useState<ExtractionBatch | null>(null);
  const [landscape, setLandscape] = useState<ResearchLandscape | null>(null);
  const [running, setRunning] = useState<RunningStage>(null);
  const [failedStage, setFailedStage] = useState<RunningStage>(null);
  const [error, setError] = useState<string | null>(null);

  const stages = useMemo<PipelineStage[]>(() => {
    const stage = (
      name: string,
      detail: string,
      key: Exclude<RunningStage, null>,
      complete: boolean,
    ): PipelineStage => ({
      name,
      detail,
      state: failedStage === key ? "error" : running === key ? "active" : complete ? "complete" : "waiting",
    });

    return [
      stage("Discover", "arXiv + OpenAlex", "search", Boolean(search)),
      stage("Rerank", strategy === "cross_encoder" ? "Cross-encoder" : "TF-IDF", "search", Boolean(search)),
      stage("Extract", "Evidence-linked notes", "extract", Boolean(extractions)),
      stage("Map", "Themes + tensions", "landscape", Boolean(landscape)),
    ];
  }, [extractions, failedStage, landscape, running, search, strategy]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunning("search");
    setFailedStage(null);
    setError(null);

    // A new topic starts a new persisted pipeline, so downstream state must follow it.
    setSearch(null);
    setExtractions(null);
    setLandscape(null);

    try {
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
      const batch = await extractPapers(search.search_id, Math.min(extractionLimit, search.results.length));
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
            <input minLength={3} maxLength={240} onChange={(event) => setTopic(event.target.value)} placeholder="What do you want to understand?" required type="search" value={topic} />
          </label>
          <button className="primaryButton" disabled={running !== null} type="submit">
            {running === "search" ? "Finding papers…" : "Find papers"}
          </button>
          <div className="searchOptions">
            <label>
              <span>Ranking</span>
              <select value={strategy} onChange={(event) => setStrategy(event.target.value as RankingStrategy)}>
                <option value="cross_encoder">Semantic reranker</option>
                <option value="keyword">TF-IDF baseline</option>
              </select>
            </label>
            <label>
              <span>Since</span>
              <input min={1950} max={new Date().getFullYear()} onChange={(event) => setYearFrom(Number(event.target.value))} type="number" value={yearFrom} />
            </label>
            <label>
              <span>Candidate pool</span>
              <select value={maxCandidates} onChange={(event) => setMaxCandidates(Number(event.target.value))}>
                <option value={25}>25 papers</option>
                <option value={50}>50 papers</option>
                <option value={100}>100 papers</option>
              </select>
            </label>
          </div>
        </form>

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
              <p>Extract problems, methods, results, contributions, and limitations. Every claim must include an exact quote from the title or abstract.</p>
            </div>
            <div className="actionControls">
              <label>
                Papers to read
                <select value={extractionLimit} onChange={(event) => setExtractionLimit(Number(event.target.value))}>
                  {[2, 3, 5, 8].map((limit) => (
                    <option disabled={limit > search.results.length} key={limit} value={limit}>Top {limit}</option>
                  ))}
                </select>
              </label>
              <button className="secondaryButton" disabled={running !== null} onClick={handleExtraction} type="button">
                {running === "extract" ? "Reading papers…" : extractions ? "Run extraction again" : "Extract evidence"}
              </button>
              <small>Uses the configured OpenAI model and records token usage.</small>
            </div>
          </section>

          {extractions && <ExtractionNotes batch={extractions} />}

          {extractions && (
            <section className="actionPanel" aria-labelledby="map-heading">
              <div>
                <p className="eyebrow">Stage four</p>
                <h2 id="map-heading">Synthesize the research landscape</h2>
                <p>Cluster the extracted papers, connect similar work, and surface themes, disagreements, and open questions.</p>
              </div>
              <div className="actionControls">
                <button className="secondaryButton" disabled={running !== null || extractionCount < 2} onClick={handleLandscape} type="button">
                  {running === "landscape" ? "Building landscape…" : landscape ? "Rebuild landscape" : "Build landscape"}
                </button>
                <small>{extractionCount < 2 ? "At least two successful extractions are required." : `${extractionCount} evidence-backed papers ready.`}</small>
              </div>
            </section>
          )}

          {landscape && (
            <section className="landscapeSummary" aria-labelledby="landscape-heading">
              <p className="eyebrow">Research landscape</p>
              <h2 id="landscape-heading">{landscape.synthesis_run.synthesis.overview}</h2>
              <div className="themeGrid">
                {landscape.synthesis_run.synthesis.clusters.map((cluster) => (
                  <article key={cluster.cluster_id}>
                    <span>Theme {String(cluster.cluster_id + 1).padStart(2, "0")}</span>
                    <h3>{cluster.name}</h3>
                    <p>{cluster.summary}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
