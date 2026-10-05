from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from caching_service.domain.payload import Payload


class Storage(Protocol):
    def get_payload_by_hash(self, request_hash: str) -> Payload | None: ...

    def get_payload_by_id(self, payload_id: UUID) -> Payload | None: ...

    def get_transformations(self, texts: Sequence[str]) -> dict[str, str]: ...

    def save_payload(
        self, request_hash: str, output: str, transformations: Mapping[str, str]
    ) -> Payload: ...
