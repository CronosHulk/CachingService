from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from caching_service.adapters.outbound.persistence.storage import PostgresStorage
from caching_service.adapters.outbound.transformer.uppercase import (
    UppercaseTransformer,
)
from caching_service.application.create_payload import CreatePayload
from caching_service.config import Settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = Settings()
    return create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )


async def get_session(
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as session, session.begin():
        yield session


async def get_storage(
    session: Annotated[
        AsyncSession,
        Depends(get_session, scope="function"),
    ],
) -> PostgresStorage:
    return PostgresStorage(session)


async def get_create_payload(
    storage: Annotated[PostgresStorage, Depends(get_storage)],
) -> CreatePayload:
    return CreatePayload(
        storage=storage,
        transformer=UppercaseTransformer(),
    )
