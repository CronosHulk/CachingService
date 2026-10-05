# Caching Service

FastAPI service for generating payloads and caching string transformations.
The project is at the skeleton stage: only the health endpoint is implemented.
PostgreSQL storage, migrations, payload endpoints, CLI, and Docker deployment
will be added in subsequent steps.

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
- `config.py`: placeholder for application settings.

Use cases will depend on ports, with concrete adapters supplied at the
application entry point. `compose.yaml` and `.env.example` are placeholders
for the PostgreSQL setup.
