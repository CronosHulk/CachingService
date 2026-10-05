FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /service

COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN python -m pip install . \
    && useradd --create-home --uid 10001 appuser

COPY alembic.ini ./
COPY migrations/ ./migrations/

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn caching_service.main:app --host 0.0.0.0 --port 8000"]
