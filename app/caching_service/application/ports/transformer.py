from typing import Protocol


class Transformer(Protocol):
    async def transform(self, text: str) -> str: ...
