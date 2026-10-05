from collections.abc import Callable
from contextlib import AbstractContextManager

import pytest

from caching_service.adapters.outbound.persistence.storage import PostgresStorage


def test_saved_payload_and_cache_survive_new_session(
    storage_scope: Callable[[], AbstractContextManager[PostgresStorage]],
) -> None:
    request_hash = "a" * 64

    with storage_scope() as storage:
        saved = storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    with storage_scope() as storage:
        assert storage.get_payload_by_id(saved.id) == saved
        assert storage.get_payload_by_hash(request_hash) == saved
        assert storage.get_transformations(["hello", "unknown"]) == {
            "hello": "HELLO",
        }


def test_repeated_request_returns_existing_payload(
    storage_scope: Callable[[], AbstractContextManager[PostgresStorage]],
) -> None:
    request_hash = "b" * 64

    with storage_scope() as storage:
        first = storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    with storage_scope() as storage:
        second = storage.save_payload(
            request_hash=request_hash,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    assert second == first


def test_existing_transformation_is_not_overwritten(
    storage_scope: Callable[[], AbstractContextManager[PostgresStorage]],
) -> None:
    with storage_scope() as storage:
        storage.save_payload(
            request_hash="c" * 64,
            output="HELLO",
            transformations={"hello": "HELLO"},
        )

    with storage_scope() as storage:
        storage.save_payload(
            request_hash="d" * 64,
            output="HELLO",
            transformations={"hello": "OTHER"},
        )

    with storage_scope() as storage:
        assert storage.get_transformations(["hello"]) == {
            "hello": "HELLO",
        }


def test_transaction_rolls_back_payload_and_cache(
    storage_scope: Callable[[], AbstractContextManager[PostgresStorage]],
) -> None:
    request_hash = "e" * 64

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with storage_scope() as storage:
            storage.save_payload(
                request_hash=request_hash,
                output="HELLO",
                transformations={"hello": "HELLO"},
            )
            raise RuntimeError("Simulated failure")

    with storage_scope() as storage:
        assert storage.get_payload_by_hash(request_hash) is None
        assert storage.get_transformations(["hello"]) == {}
