# Research Atlas

Research Atlas is a conference-aware paper discovery and evaluation workspace. It will retrieve academic papers, compare ranking strategies, extract evidence-backed notes, and turn a field into an interactive research map.

This first phase establishes the FastAPI and Next.js applications that later pipeline work will build on.

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
