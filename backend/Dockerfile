FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
ARG INSTALL_ML=false
RUN if [ "$INSTALL_ML" = "true" ]; then \
      pip install --no-cache-dir '.[ml]'; \
    else \
      pip install --no-cache-dir .; \
    fi

RUN groupadd --system atlas && useradd --system --gid atlas --home-dir /app atlas \
    && chown -R atlas:atlas /app

USER atlas

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
