FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[dev]" \
    && playwright install --with-deps firefox

COPY config ./config
COPY personal ./personal
COPY tests ./tests

RUN useradd --create-home appuser \
    && mkdir -p credentials profile data \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "job_applier"]
