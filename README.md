# Caching Service

FastAPI service for generating payloads and caching string transformations.
The service provides async payload creation and reading, backed by PostgreSQL.
An async CLI and Docker Compose deployment are included.

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

## CLI

Installing the project registers the `cache-cli` command. Start the API first.
Arguments are parsed and validated through Pydantic Settings:
https://pydantic.dev/docs/validation/2.12/concepts/pydantic_settings/

```bash
cache-cli --help
cache-cli -H http://127.0.0.1:8000 -r 2 \
  -j '{"list_1":["hello"],"list_2":["cat"]}'
cache-cli -i request.json -o response.jsonl
cat request.json | cache-cli -i - -o -
```

Provide exactly one of `--input` (`-i`) and `--json` (`-j`). `--output` (`-o`)
defaults to stdout; `-` selects stdin or stdout. Repeat must be a positive
integer. Each iteration sends POST followed by GET and produces one JSON line:

```json
{"output":"HELLO, CAT"}
```

The input is loaded once and reused for every iteration. Results are written
only after all iterations succeed. An output file is overwritten. Validation,
HTTP, and file errors go to stderr with exit code 1. Help exits with code 0.
The specification assigns `-h` to both host and help; this implementation uses
`-H` for host and reserves `-h` for help. Long option names match the task.

CLI HTTP operations are async; file and standard-stream I/O run in a worker
thread. Run CLI tests with `python -m pytest -q tests/test_cli.py`; the API
integration suite also exercises CLI requests against the test database.

## Docker API

PostgreSQL and the API run in separate containers on the Compose network.
Create `.env` from `.env.example` if you have not configured it yet, then run:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

The API waits for PostgreSQL's healthcheck, applies Alembic migrations, and
starts Uvicorn. A failed migration prevents API startup. The API runs as an
unprivileged user; local `.env` files are excluded from the build context.
This startup migration approach assumes one API container.

Inside Docker the database address is `postgres:5432`. Local tools continue
using `localhost:5433`. The API is published on `127.0.0.1:8000` by default.
If port 8000 is occupied, use `API_PORT=8001 docker compose up -d api` and
point the CLI at port 8001.

```bash
cache-cli -H http://127.0.0.1:8000 -r 2 \
  -j '{"list_1":["hello"],"list_2":["cat"]}'
```

Compose mounts `app/`, `migrations/`, and `alembic.ini` from the host read-only.
`PYTHONPATH=/service/app` makes Python import the mounted code instead of the
installed copy. Uvicorn reloads automatically after Python code changes.
After adding migrations, run `docker compose exec api alembic upgrade head`.
After changing dependencies, rebuild with `docker compose up -d --build api`.
The default Compose configuration is intended for development; the standalone
Docker image runs without mounts or reload.
`docker compose down` stops the services and retains the PostgreSQL volume.
