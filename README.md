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

## Phase 4 evidence-backed extraction

Research Atlas can turn ranked paper metadata into structured notes containing the problem, method, reported results, contributions, limitations, and keywords. Each claim carries an exact quote and its source section; the backend rejects a model response when a quote cannot be found in the supplied title or abstract.

The extractor uses the async OpenAI Responses API with Pydantic Structured Outputs. Configure a key before running this paid, opt-in stage:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-5-mini
```

After creating a search, extract its five highest-ranked papers:

```bash
curl -X POST http://localhost:8000/api/v1/searches/SEARCH_ID/extractions \
  -H 'Content-Type: application/json' \
  -d '{"limit":5}'
```

Calls run concurrently with a configurable bound. Successful extractions are persisted with their prompt version, model, provider response ID, token usage, and latency; individual paper failures remain visible in the batch response.

## Database migrations

PostgreSQL stores searches, canonical papers, provider identifiers, ranked results, and structured extractions. Apply migrations after configuring `DATABASE_URL`:

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
