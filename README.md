# Research Atlas

Research Atlas is a conference-aware paper discovery and evaluation workspace. I made this in mind to retrieve academic papers, compare ranking strategies, and turn a field of your choice into an interactive map.

The current backend retrieves papers from arXiv and OpenAlex, merges duplicate records, and runs a two-stage retrieve-and-rerank pipeline with persisted results.

## Phase 1 domain

The backend already defines provider-neutral paper and search models plus an immutable pipeline state machine. External providers, ranking models, and persistence can be added without changing the API's core vocabulary.

## Phase 3 ranking pipeline

Every search queries the configured metadata providers concurrently, normalizes their records, and uses TF-IDF cosine similarity to produce a cheap candidate shortlist. When the ML extra is enabled, `cross-encoder/ms-marco-MiniLM-L6-v2` reranks those candidates by reading the topic and paper text together. The response reports provider counts, deduplication totals, latency, and fallback warnings.

Run the baseline search pipeline with the normal installation. To enable the PyTorch-backed cross-encoder locally:

```bash
cd backend
pip install -e '.[ml,dev]'
export CROSS_ENCODER_ENABLED=true
```

For Docker, set both `INSTALL_ML=true` and `CROSS_ENCODER_ENABLED=true` before building. The model downloads on the first semantic search and remains cached in the API process.

Create a search with:

```bash
curl -X POST http://localhost:8000/api/v1/searches \
  -H 'Content-Type: application/json' \
  -d '{"topic":"adaptive retrieval for small language models","strategies":["keyword"]}'
```

The ranking module also exposes Recall@K, reciprocal rank, and nDCG evaluation helpers for labeled experiments.

## Database migrations

PostgreSQL stores searches, canonical papers, provider identifiers, and ranked search results. Apply migrations after configuring `DATABASE_URL`:

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
