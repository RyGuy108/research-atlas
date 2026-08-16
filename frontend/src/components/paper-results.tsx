import type { SearchOutcome } from "@/lib/api";

function formatAuthors(names: string[]): string {
  if (names.length <= 3) return names.join(", ");
  return `${names.slice(0, 3).join(", ")} +${names.length - 3}`;
}

export function PaperResults({ outcome }: { outcome: SearchOutcome }) {
  const providerTotal = Object.values(outcome.diagnostics.provider_candidates).reduce(
    (total, count) => total + count,
    0,
  );

  return (
    <section className="resultsSection" aria-labelledby="papers-heading">
      <div className="sectionHeading">
        <div>
          <p className="eyebrow">Ranked reading list</p>
          <h2 id="papers-heading">{outcome.results.length} papers worth a closer look</h2>
        </div>
        <dl className="diagnostics" aria-label="Search diagnostics">
          <div><dt>Retrieved</dt><dd>{providerTotal}</dd></div>
          <div><dt>Deduplicated</dt><dd>{outcome.diagnostics.deduplicated_count}</dd></div>
          <div><dt>Ranker</dt><dd>{outcome.ranking_strategy.replace("_", " ")}</dd></div>
          <div><dt>Latency</dt><dd>{Math.round(outcome.diagnostics.elapsed_ms)} ms</dd></div>
        </dl>
      </div>

      {outcome.diagnostics.warnings.length > 0 && (
        <div className="notice notice--warning" role="status">
          {outcome.diagnostics.warnings.join(" ")}
        </div>
      )}

      <div className="paperList">
        {outcome.results.map(({ paper, rank, score, strategy }) => (
          <article className="paperCard" key={`${rank}-${paper.landing_page_url}`}>
            <div className="rank" aria-label={`Rank ${rank}`}>
              {String(rank).padStart(2, "0")}
            </div>
            <div className="paperBody">
              <div className="paperMeta">
                <span>{paper.published_on.slice(0, 4)}</span>
                <span>{paper.venue ?? paper.sources[0].provider}</span>
                <span>{paper.citation_count.toLocaleString()} citations</span>
              </div>
              <h3>{paper.title}</h3>
              <p className="authors">{formatAuthors(paper.authors.map((author) => author.name))}</p>
              <p className="abstract">{paper.abstract}</p>
              <div className="paperFooter">
                <span className="score">{strategy.replace("_", " ")} · {score.toFixed(3)}</span>
                <a href={paper.landing_page_url} target="_blank" rel="noreferrer">
                  Read source <span aria-hidden="true">↗</span>
                </a>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
