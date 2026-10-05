# Caching Service

FastAPI service for generating payloads and caching string transformations.
The service provides async payload creation and reading, backed by PostgreSQL.
CLI and application Docker deployment will be added in subsequent steps.

## Local setup

Requires Python 3.12 or newer. Run commands from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pre-commit install
```

Keep the virtual environment active when committing: the hooks use its Ruff
installation. Each developer must install the Git hooks locally.

## Run

```bash
uvicorn caching_service.main:app --reload
```

The API is available at http://127.0.0.1:8000, with interactive documentation
at http://127.0.0.1:8000/docs.

```bash
curl http://127.0.0.1:8000/health
```

Expected response: `{"status":"ok"}`. This endpoint checks that the application
responds; it does not check database connectivity.

## Checks

```bash
pytest
ruff check .
ruff format --check .
pre-commit run --all-files
```

If a commit hook modifies a file, review and stage the changes before retrying
the commit.

## Architecture

The Python package lives in `app/caching_service/`:

- `domain/`: business rules independent of frameworks and storage.
- `application/`: use cases; `ports/` defines interfaces for external services.
- `adapters/inbound/api/`: HTTP requests and responses.
- `adapters/outbound/persistence/`: database implementations of storage ports.
- `adapters/outbound/transformer/`: implementation of the string transformer.
- `main.py`: application entry point and future dependency wiring.
- `config.py`: application settings loaded from the environment and `.env`.

Use cases will depend on ports, with concrete adapters supplied at the
application entry point. PostgreSQL runs through `compose.yaml`; connection
examples are in `.env.example`.

## Async execution

API handlers, use cases, transformer ports, and storage operations use
`async`/`await`. SQLAlchemy uses `AsyncEngine` and `AsyncSession` with psycopg 3;
the existing `postgresql+psycopg` URLs work with the async engine. Each request
gets one session and transaction, completed before the response is sent.
The engine pool is disposed when the application shuts down.

Alembic uses an async connection with `run_sync` for its migration API.
Schema definitions, validation, hashing, and migration operations remain
ordinary Python functions because they do not perform async I/O.

Tests run with pytest-asyncio. Integration tests read `TEST_DATABASE_URL` from
`.env` or the environment and require a migrated `caching_service_test` database.
They clear the two application tables before each test and run sequentially.
Concurrent cache misses can still invoke the transformer more than once;
unique constraints prevent duplicate stored records.
