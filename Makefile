.PHONY: backend-check frontend-check migrate check

backend-check:
	cd backend && .venv/bin/ruff check app tests migrations && .venv/bin/mypy app && .venv/bin/pytest

frontend-check:
	cd frontend && npm run lint && npm run typecheck && npm run build

migrate:
	cd backend && .venv/bin/alembic upgrade head

check: backend-check frontend-check
