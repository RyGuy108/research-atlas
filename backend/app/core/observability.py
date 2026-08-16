import json
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from prometheus_client import Counter, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_COUNT = Counter(
    "research_atlas_http_requests_total",
    "HTTP requests handled by the API",
    ("method", "path", "status"),
)
REQUEST_LATENCY = Histogram(
    "research_atlas_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ("method", "path"),
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "elapsed_ms", "job_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class RequestObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._logger = logging.getLogger("research_atlas.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", str(uuid4()).encode()).decode()[:128]
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "unknown")
        status_code = 500
        started_at = perf_counter()

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_context)
        finally:
            elapsed = perf_counter() - started_at
            REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
            self._logger.info(
                "request complete",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "elapsed_ms": round(elapsed * 1_000, 2),
                },
            )
