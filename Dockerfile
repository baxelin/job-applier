FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:99

WORKDIR /app

# Bibliotecas de texto exigidas pelo WeasyPrint para gerar os PDFs e
# tela virtual + VNC + noVNC para ver e controlar o Firefox pelo navegador
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
        xvfb x11vnc novnc websockify \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[dev]" \
    && playwright install --with-deps firefox

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY config ./config
COPY personal ./personal
COPY tests ./tests

RUN useradd --create-home appuser \
    && mkdir -p credentials profile data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 6080
ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "-m", "job_applier"]
