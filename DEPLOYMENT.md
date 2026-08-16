# Production deployment

Research Atlas deploys as five cooperating services:

```text
Browser -> Next.js -> FastAPI -> PostgreSQL
                        |
                      Redis -> pipeline worker -> arXiv / OpenAlex / OpenAI
```

The included `docker-compose.yml` is the reference topology. A cloud deployment can use any platform that supports two long-running containers plus managed PostgreSQL and Redis. Run one worker replica with the current reliable-list queue implementation.

## Required configuration

Configure these values in the deployment platform rather than committing them:

| Variable | Service | Purpose |
|---|---|---|
| `DATABASE_URL` | API, worker | Async PostgreSQL connection |
| `REDIS_URL` | API, worker | Durable job state, queue, and Pub/Sub |
| `OPENAI_API_KEY` | Worker | Structured extraction and synthesis |
| `OPENALEX_API_KEY` | Worker | Optional second discovery provider |
| `CORS_ORIGINS` | API | Exact deployed frontend origins as JSON |
| `NEXT_PUBLIC_API_URL` | Frontend build | Public API origin |
| `WRITE_API_KEY` | API | Optional protection for mutating API clients |

`WRITE_API_KEY` is intended for private or server-to-server deployments. Do not place it in a `NEXT_PUBLIC_*` variable. A public browser deployment should add user authentication or a server-side Next.js proxy before enabling this key.

## Release sequence

1. Provision PostgreSQL and Redis with persistence and TLS.
2. Build the backend image once and run it as both the API and worker, overriding the worker command with `python -m app.worker`.
3. Run `alembic upgrade head` as a release command before starting the API.
4. Build the frontend with its final `NEXT_PUBLIC_API_URL`; this value is compiled into the browser bundle.
5. Verify `/api/v1/ready`, inspect `/api/v1/metrics`, and submit a small keyword-ranked pipeline job.

## Operations

- Retain Redis data across restarts. Job snapshots expire after `PIPELINE_JOB_TTL_SECONDS`.
- Scrape `/api/v1/metrics` with Prometheus or a compatible hosted collector.
- Forward JSON application logs and index `request_id` so an API response can be traced through logs.
- Alert on elevated 5xx request counts, job failures, worker restarts, and PostgreSQL connection errors.
- Keep the API and worker on the same application version during releases.

The GitHub Actions workflow validates Python, TypeScript, the production Next.js build, and both container images on every pull request and push to `main`.
Pushing a version tag such as `v1.0.0` publishes versioned backend and frontend images to GitHub Container Registry for deployment.
