from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Payload:
    id: UUID
    output: str
