from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

import pytest
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

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
async def engine() -> AsyncIterator[AsyncEngine]:
    settings = IntegrationSettings()
    if settings.test_database_url is None:
        pytest.skip("Set TEST_DATABASE_URL in .env or the environment")
    database_url = str(settings.test_database_url)

    if make_url(database_url).database != "caching_service_test":
        raise ValueError("Expected the caching_service_test database")

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.execute(delete(Payload))
            await connection.execute(delete(TransformCache))

        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def storage_scope(
    engine: AsyncEngine,
) -> Callable[[], AbstractAsyncContextManager[PostgresStorage]]:
    @asynccontextmanager
    async def open_storage() -> AsyncGenerator[PostgresStorage, None]:
        async with AsyncSession(engine) as session, session.begin():
            yield PostgresStorage(session)

    return open_storage
