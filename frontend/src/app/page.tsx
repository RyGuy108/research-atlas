const pipeline = ["Discover", "Rerank", "Extract", "Map"];

export default function Home() {
  return (
    <main>
      <nav className="nav">
        <span className="brand">Research Atlas</span>
        <span className="badge">Foundation preview</span>
      </nav>

      <section className="hero">
        <p className="eyebrow">Conference-aware literature discovery</p>
        <h1>Turn a research topic into an evidence-backed reading map.</h1>
        <p className="lede">
          Search across machine-learning venues, compare retrieval strategies, and trace every
          synthesized claim back to its source.
        </p>

        <div className="searchShell" aria-label="Search preview">
          <span>Adaptive retrieval for small language models</span>
          <button type="button" disabled>
            Build atlas
          </button>
        </div>

        <ol className="pipeline" aria-label="Research pipeline">
          {pipeline.map((stage, index) => (
            <li key={stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {stage}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

