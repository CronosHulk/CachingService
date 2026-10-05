from typing import Protocol


class Transformer(Protocol):
    def transform(self, text: str) -> str: ...
