import hashlib
import json
from collections.abc import Sequence

from caching_service.application.ports.storage import Storage
from caching_service.application.ports.transformer import Transformer
from caching_service.domain.payload import Payload


class CreatePayload:
    def __init__(
        self,
        storage: Storage,
        transformer: Transformer,
    ) -> None:
        self.storage = storage
        self.transformer = transformer

    def execute(
        self,
        list_1: Sequence[str],
        list_2: Sequence[str],
    ) -> Payload:
        if len(list_1) != len(list_2):
            raise ValueError("Lists must have the same length")

        request_json = json.dumps(
            [list(list_1), list(list_2)],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        request_hash = hashlib.sha256(request_json.encode("utf-8")).hexdigest()

        existing = self.storage.get_payload_by_hash(request_hash)
        if existing is not None:
            return existing

        unique_texts = list(dict.fromkeys([*list_1, *list_2]))
        cached = self.storage.get_transformations(unique_texts)

        new_transformations = {
            text: self.transformer.transform(text)
            for text in unique_texts
            if text not in cached
        }
        transformations = {**cached, **new_transformations}

        output = ", ".join(
            transformations[text]
            for pair in zip(list_1, list_2, strict=True)
            for text in pair
        )

        return self.storage.save_payload(
            request_hash=request_hash,
            output=output,
            transformations=new_transformations,
        )
