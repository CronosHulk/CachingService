from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import pytest

from caching_service.adapters.outbound.persistence.storage import PostgresStorage


async def test_saved_payload_and_cache_survive_new_session(
    storage_scope: Callable[[], AbstractAsyncContextManager[PostgresStorage]],
) -> None:
    request_hash = "a" * 64

    async with storage_scope() as storage:
        saved = await storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    async with storage_scope() as storage:
        assert await storage.get_payload_by_id(saved.id) == saved
        assert await storage.get_payload_by_hash(request_hash) == saved
        assert await storage.get_transformations(["hello", "unknown"]) == {
            "hello": "HELLO",
        }


async def test_repeated_request_returns_existing_payload(
    storage_scope: Callable[[], AbstractAsyncContextManager[PostgresStorage]],
) -> None:
    request_hash = "b" * 64

    async with storage_scope() as storage:
        first = await storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    async with storage_scope() as storage:
        second = await storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    assert second == first


async def test_existing_transformation_is_not_overwritten(
    storage_scope: Callable[[], AbstractAsyncContextManager[PostgresStorage]],
) -> None:
    async with storage_scope() as storage:
        await storage.save_payload(
            request_hash="c" * 64,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    async with storage_scope() as storage:
        await storage.save_payload(
            request_hash="d" * 64,
            output="HELLO",
            transformations={"hello": "OTHER"},
        )

    async with storage_scope() as storage:
        assert await storage.get_transformations(["hello"]) == {
            "hello": "HELLO",
        }


async def test_transaction_rolls_back_payload_and_cache(
    storage_scope: Callable[[], AbstractAsyncContextManager[PostgresStorage]],
) -> None:
    request_hash = "e" * 64

    with pytest.raises(RuntimeError, match="Simulated failure"):
        async with storage_scope() as storage:
            await storage.save_payload(
                request_hash=request_hash,
                output="HELLO",
                transformations={"hello": "HELLO"},
            )
            raise RuntimeError("Simulated failure")

    async with storage_scope() as storage:
        assert await storage.get_payload_by_hash(request_hash) is None
        assert await storage.get_transformations(["hello"]) == {}
