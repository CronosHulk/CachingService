from collections.abc import Callable, Generator, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from caching_service.adapters.outbound.persistence.models import (
    Payload,
    TransformCache,
)
from caching_service.adapters.outbound.persistence.storage import PostgresStorage


class IntegrationSettings(BaseSettings):
    test_database_url: PostgresDsn | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@pytest.fixture
def engine() -> Iterator[Engine]:
    settings = IntegrationSettings()
    if settings.test_database_url is None:
        pytest.skip("Set TEST_DATABASE_URL in .env or the environment")
    database_url = str(settings.test_database_url)

    if make_url(database_url).database != "caching_service_test":
        raise ValueError("Expected the caching_service_test database")

    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(delete(Payload))
            connection.execute(delete(TransformCache))

        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def storage_scope(
    engine: Engine,
) -> Callable[[], AbstractContextManager[PostgresStorage]]:
    @contextmanager
    def open_storage() -> Generator[PostgresStorage, None, None]:
        with Session(engine) as session, session.begin():
            yield PostgresStorage(session)

    return open_storage
