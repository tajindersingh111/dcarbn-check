FROM python:3.14.7-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m pip install --upgrade pip "setuptools>=83,<84" wheel && \
    python -m pip install --no-cache-dir --target /opt/site . && \
    PYTHONPATH=/opt/site python -c "from importlib.metadata import version; assert tuple(map(int, version('msgpack').split('.'))) >= (1, 2, 1), version('msgpack')"

FROM python:3.14.7-slim AS runtime

ENV PATH="/opt/site/bin:${PATH}" \
    PYTHONPATH="/opt/site" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser

RUN python -m pip uninstall -y setuptools msgpack || true
RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid 10001 --create-home appuser

WORKDIR /app

COPY --from=builder /opt/site /opt/site
COPY --chown=appuser:appuser . /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
