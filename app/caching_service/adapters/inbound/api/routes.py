from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from caching_service.adapters.inbound.api.dependencies import (
    get_create_payload,
    get_storage,
)
from caching_service.adapters.inbound.api.schemas import (
    CreatePayloadRequest,
    CreatePayloadResponse,
    ReadPayloadResponse,
)
from caching_service.adapters.outbound.persistence.storage import PostgresStorage
from caching_service.application.create_payload import CreatePayload

router = APIRouter(prefix="/payload", tags=["payload"])


@router.post("", response_model=CreatePayloadResponse)
async def create_payload(
    body: CreatePayloadRequest,
    service: Annotated[CreatePayload, Depends(get_create_payload)],
) -> CreatePayloadResponse:
    payload = await service.execute(body.list_1, body.list_2)
    return CreatePayloadResponse(id=payload.id)


@router.get("/{payload_id}", response_model=ReadPayloadResponse)
async def read_payload(
    payload_id: UUID,
    storage: Annotated[PostgresStorage, Depends(get_storage)],
) -> ReadPayloadResponse:
    payload = await storage.get_payload_by_id(payload_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Payload not found")

    return ReadPayloadResponse(output=payload.output)
