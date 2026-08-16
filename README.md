# Research Atlas

Research Atlas is a conference-aware paper discovery and evaluation workspace. I made this in mind to retrieve academic papers, compare ranking strategies, and turn a field of your choice into an interactive map.

## Phase 1 — Project foundation

Established a Dockerized monorepo with a FastAPI backend and Next.js frontend. Added typed configuration, health/readiness endpoints, provider-neutral paper models, and an immutable state machine for tracking pipeline execution.

## Phase 2 — Multi-source discovery and persistence

Implemented async integrations with arXiv and OpenAlex for journal, preprint, and conference-paper discovery. Results are normalized into a shared schema, deduplicated across DOI, arXiv, and provider identifiers, and persisted in PostgreSQL using SQLAlchemy and Alembic.

## Phase 3 — Retrieval and semantic reranking

Metadata providers are queried concurrently before TF-IDF cosine similarity creates a fast candidate shortlist. An optional PyTorch-backed cross-encoder/ms-marco-MiniLM-L6-v2 model then reranks candidates by jointly evaluating the research topic and paper text.

Search responses include provider counts, deduplication totals, latency, ranking diagnostics, and fallback warnings. The ranking package also supports Recall@K, mean reciprocal rank, and nDCG evaluation.

Enable semantic reranking locally with:

```bash
cd backend
pip install -e '.[ml,dev]'
export CROSS_ENCODER_ENABLED=true
```

For Docker builds, enable both INSTALL_ML=true and CROSS_ENCODER_ENABLED=true. The model is downloaded during the first semantic search and cached by the API process.

## Phase 4 — Evidence-backed extraction
Ranked papers can be converted into structured research notes covering the problem, method, results, contributions, limitations, and keywords.

Extraction uses the async OpenAI Responses API with Pydantic Structured Outputs. Every generated claim must include a supporting quotation found in the supplied paper metadata; unsupported evidence causes validation to fail.

Requests use bounded concurrency, while successful outputs persist their model, prompt version, response ID, token usage, and latency. Individual paper failures remain visible without failing the entire batch.

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-5-mini
```

## Phase 5 — Research landscape synthesis

Research Atlas converts extracted papers into a cross-paper research landscape. A deterministic scikit-learn pipeline selects a cluster count using silhouette score, groups papers with K-means, creates cosine-similarity graph edges, and projects papers into normalized two-dimensional coordinates.

A structured LLM pass names the clusters and identifies evidence-linked relationships, tensions, and open research questions. Semantic validation rejects irregularities such as the following: unknown papers, invalid cluster evidence, duplicate narratives, and self-referential relationships.

## Phase 6 — Interactive research workspace

The Next.js and TypeScript interface supports the complete persisted workflow here: topic configuration, multi-provider discovery, ranking diagnostics, evidence extraction, and landscape synthesis.

Researchers can inspect paper-level evidence and relationships through an interactive semantic graph. Selecting a graph node connects the paper directly to its extracted problem, method, results, and limitations.

Use NEXT_PUBLIC_API_URL when FastAPI is not available at its default address:

```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Phase 7 — Live asynchronous pipeline jobs

FastAPI immediately returns a job identifier, executes each stage with an isolated database transaction, and streams immutable progress snapshots to the frontend using Server-Sent Events.

For local development, jobs can run entirely inside the API process. The Docker deployment uses Redis for durable snapshots, Pub/Sub events, and queue coordination, while a separate worker processes jobs and recovers interrupted queue entries.

## Evaluation and operations

Human relevance judgments can be recorded from the evidence notebook or API against any persisted search. Research Atlas saves each evaluation run and reports Recall@K, reciprocal rank, and nDCG so ranking changes can be compared with repeatable metrics rather than screenshots or intuition.

The production API adds JSON request logs, traceable `X-Request-ID` response headers, Prometheus metrics at `/api/v1/metrics`, and optional `X-API-Key` protection for mutating endpoints. See [DEPLOYMENT.md](DEPLOYMENT.md) for the service topology, secrets, release sequence, and operational checks.

## Database migrations

PostgreSQL stores searches, canonical papers, provider identifiers, ranked results, structured extractions, and synthesized landscapes. Apply migrations after configuring `DATABASE_URL`:

```bash
make migrate
```

Docker Compose applies the migration automatically before the API starts.

## Repository layout

```text
backend/   FastAPI service and Python domain logic
frontend/  Next.js web application
```

## Run locally

Copy the example environment file, then start the stack:

```bash
cp .env.example .env
docker compose up --build
```

Open the web app at <http://localhost:3000> and the API documentation at <http://localhost:8000/docs>.

## Run without Docker

The backend requires Python 3.12 or newer:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Run the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Verify

```bash
make check
```
