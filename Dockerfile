FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Bibliotecas de texto exigidas pelo WeasyPrint para gerar os PDFs
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

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
