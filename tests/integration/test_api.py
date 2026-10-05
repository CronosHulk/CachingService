from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from caching_service.adapters.inbound.api.dependencies import get_engine
from caching_service.main import app


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    async def override_engine() -> AsyncEngine:
        return engine

    app.dependency_overrides[get_engine] = override_engine
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_engine, None)


async def test_create_read_and_repeat_payload(client: AsyncClient) -> None:
    body = {"list_1": ["hello", "world"], "list_2": ["cat", "hello"]}

    created = await client.post("/payload", json=body)
    assert created.status_code == 200
    payload_id = created.json()["id"]

    read = await client.get(f"/payload/{payload_id}")
    assert read.status_code == 200
    assert read.json() == {"output": "HELLO, CAT, WORLD, HELLO"}

    repeated = await client.post("/payload", json=body)
    assert repeated.status_code == 200
    assert repeated.json() == created.json()


async def test_unknown_payload_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/payload/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"list_1": ["hello"], "list_2": []},
        {"list_1": [123], "list_2": ["hello"]},
    ],
)
async def test_invalid_payload_returns_422(client: AsyncClient, body: dict) -> None:
    response = await client.post("/payload", json=body)
    assert response.status_code == 422
