from collections.abc import Mapping, Sequence
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from caching_service.adapters.outbound.persistence.models import (
    Payload as PayloadModel,
)
from caching_service.adapters.outbound.persistence.models import TransformCache
from caching_service.domain.payload import Payload


class PostgresStorage:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_payload_by_hash(self, request_hash: str) -> Payload | None:
        row = self.session.scalar(
            select(PayloadModel).where(PayloadModel.request_hash == request_hash)
        )
        if row is None:
            return None

        return Payload(id=row.id, output=row.output)

    def get_payload_by_id(self, payload_id: UUID) -> Payload | None:
        row = self.session.get(PayloadModel, payload_id)
        if row is None:
            return None

        return Payload(id=row.id, output=row.output)

    def get_transformations(self, texts: Sequence[str]) -> dict[str, str]:
        if not texts:
            return {}

        hashes = {sha256(text.encode("utf-8")).hexdigest() for text in texts}

        rows = self.session.scalars(
            select(TransformCache).where(TransformCache.input_hash.in_(hashes))
        )
        return {row.input_text: row.output_text for row in rows}

    def save_payload(
        self,
        request_hash: str,
        output: str,
        transformations: Mapping[str, str],
    ) -> Payload:
        if transformations:
            rows = [
                {
                    "input_hash": sha256(text.encode("utf-8")).hexdigest(),
                    "input_text": text,
                    "output_text": transformed,
                }
                for text, transformed in transformations.items()
            ]
            rows.sort(key=lambda row: row["input_hash"])

            self.session.execute(
                insert(TransformCache)
                .values(rows)
                .on_conflict_do_nothing(
                    index_elements=[TransformCache.input_hash],
                )
            )

        self.session.execute(
            insert(PayloadModel)
            .values(
                id=uuid4(),
                request_hash=request_hash,
                output=output,
            )
            .on_conflict_do_nothing(
                index_elements=[PayloadModel.request_hash],
            )
        )

        payload = self.get_payload_by_hash(request_hash)
        if payload is None:
            raise RuntimeError("Payload not found after insert")

        return payload
