import { AtlasWorkspace } from "@/components/atlas-workspace";

export default function Home() {
  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top" aria-label="Research Atlas home">Research Atlas</a>
        <div className="navMeta">
          <span>Evidence over hype</span>
          <a href="https://github.com/RyGuy108/research-atlas" target="_blank" rel="noreferrer">Source <span aria-hidden="true">↗</span></a>
        </div>
      </nav>
      <div id="top"><AtlasWorkspace /></div>
      <footer><span>Research Atlas</span><p>Built to make literature review methods inspectable.</p></footer>
    </main>
  );
}
