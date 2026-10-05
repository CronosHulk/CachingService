from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class CreatePayloadRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    list_1: list[str]
    list_2: list[str]

    @model_validator(mode="after")
    def validate_lengths(self) -> "CreatePayloadRequest":
        if len(self.list_1) != len(self.list_2):
            raise ValueError("Lists must have the same length")
        return self


class CreatePayloadResponse(BaseModel):
    id: UUID


class ReadPayloadResponse(BaseModel):
    output: str
