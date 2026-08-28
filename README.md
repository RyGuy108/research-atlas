# Research Atlas

Research Atlas is a conference-aware paper discovery and evaluation workspace. I made this in mind to retrieve academic papers, compare ranking strategies, and turn a field of your choice into an interactive map.

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
