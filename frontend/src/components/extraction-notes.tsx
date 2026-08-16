import type { CompletedExtraction, EvidenceClaim, ExtractionBatch } from "@/lib/api";

function Claim({ label, claim }: { label: string; claim: EvidenceClaim }) {
  return (
    <div className="claim">
      <h4>{label}</h4>
      <p>{claim.summary}</p>
      <blockquote>
        “{claim.evidence[0].quote}”
        <cite>{claim.evidence[0].section}</cite>
      </blockquote>
    </div>
  );
}

function ExtractionCard({ item }: { item: CompletedExtraction }) {
  const extraction = item.run.extraction;

  return (
    <details className="extractionCard">
      <summary>
        <span className="rank">{String(item.rank).padStart(2, "0")}</span>
        <span>
          <strong>{item.title}</strong>
          <small>{extraction.keywords.slice(0, 4).join(" · ")}</small>
        </span>
        <span className="expandLabel">View evidence</span>
      </summary>
      <div className="extractionBody">
        <Claim label="Research problem" claim={extraction.problem} />
        <Claim label="Method" claim={extraction.method} />
        <Claim label="Reported result" claim={extraction.results[0]} />
        <Claim label="Contribution" claim={extraction.contributions[0]} />
      </div>
    </details>
  );
}

export function ExtractionNotes({ batch }: { batch: ExtractionBatch }) {
  return (
    <section className="resultsSection" aria-labelledby="notes-heading">
      <div className="sectionHeading sectionHeading--compact">
        <div>
          <p className="eyebrow">Evidence notebook</p>
          <h2 id="notes-heading">Structured notes with source quotes</h2>
        </div>
        <p className="usage">{batch.usage.total_tokens.toLocaleString()} model tokens</p>
      </div>

      {batch.failures.length > 0 && (
        <div className="notice notice--warning" role="status">
          {batch.failures.length} extraction{batch.failures.length === 1 ? "" : "s"} failed. The
          successful papers below remain available for synthesis.
        </div>
      )}

      <div className="extractionList">
        {batch.completed.map((item) => (
          <ExtractionCard item={item} key={item.paper_id} />
        ))}
      </div>
    </section>
  );
}
