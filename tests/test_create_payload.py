from collections.abc import Mapping, Sequence
from uuid import UUID, uuid4

import pytest

from caching_service.application.create_payload import CreatePayload
from caching_service.domain.payload import Payload


class MemoryStorage:
    def __init__(self) -> None:
        self.payloads: dict[str, Payload] = {}
        self.transformations: dict[str, str] = {}

    async def get_payload_by_hash(self, request_hash: str) -> Payload | None:
        return self.payloads.get(request_hash)

    async def get_payload_by_id(self, payload_id: UUID) -> Payload | None:
        return next(
            (payload for payload in self.payloads.values() if payload.id == payload_id),
            None,
        )

    async def get_transformations(self, texts: Sequence[str]) -> dict[str, str]:
        return {
            text: self.transformations[text]
            for text in texts
            if text in self.transformations
        }

    async def save_payload(
        self,
        request_hash: str,
        output: str,
        transformations: Mapping[str, str],
    ) -> Payload:
        existing = self.payloads.get(request_hash)
        if existing is not None:
            return existing

        payload = Payload(id=uuid4(), output=output)
        self.transformations.update(transformations)
        self.payloads[request_hash] = payload
        return payload


class CountingTransformer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def transform(self, text: str) -> str:
        self.calls.append(text)
        return text.upper()


async def test_interleaves_transformed_strings() -> None:
    storage = MemoryStorage()
    transformer = CountingTransformer()
    service = CreatePayload(storage, transformer)

    payload = await service.execute(["hello", "world"], ["cat", "dog"])

    assert payload.output == "HELLO, CAT, WORLD, DOG"
    assert len(transformer.calls) == 4
    assert await storage.get_payload_by_id(payload.id) == payload


async def test_transforms_duplicate_string_once() -> None:
    storage = MemoryStorage()
    transformer = CountingTransformer()
    service = CreatePayload(storage, transformer)

    payload = await service.execute(["hello", "hello"], ["hello", "hello"])

    assert payload.output == "HELLO, HELLO, HELLO, HELLO"
    assert transformer.calls == ["hello"]


async def test_repeated_request_reuses_payload_id() -> None:
    storage = MemoryStorage()
    transformer = CountingTransformer()
    service = CreatePayload(storage, transformer)

    first = await service.execute(["hello"], ["cat"])
    calls_after_first = transformer.calls.copy()

    second = await service.execute(["hello"], ["cat"])

    assert second.id == first.id
    assert second.output == first.output
    assert transformer.calls == calls_after_first
    assert len(storage.payloads) == 1


async def test_new_request_reuses_cached_transformations() -> None:
    storage = MemoryStorage()
    transformer = CountingTransformer()
    service = CreatePayload(storage, transformer)

    first = await service.execute(["hello"], ["cat"])
    transformer.calls.clear()

    second = await service.execute(["cat"], ["dog"])

    assert second.id != first.id
    assert second.output == "CAT, DOG"
    assert transformer.calls == ["dog"]


async def test_rejects_different_list_lengths() -> None:
    storage = MemoryStorage()
    transformer = CountingTransformer()
    service = CreatePayload(storage, transformer)

    with pytest.raises(ValueError, match="same length"):
        await service.execute(["hello"], [])

    assert transformer.calls == []
    assert storage.payloads == {}
