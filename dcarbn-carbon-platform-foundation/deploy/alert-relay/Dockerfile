FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid 10001 --create-home appuser

WORKDIR /app
COPY --chown=appuser:appuser relay.py /app/relay.py

USER 10001:10001
EXPOSE 8080
CMD ["python", "/app/relay.py"]
