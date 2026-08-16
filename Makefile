.PHONY: backend-check frontend-check check

backend-check:
	cd backend && .venv/bin/ruff check app tests && .venv/bin/mypy app && .venv/bin/pytest

frontend-check:
	cd frontend && npm run lint && npm run typecheck && npm run build

check: backend-check frontend-check
