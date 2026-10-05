from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from caching_service.main import app


@pytest.mark.parametrize("path, status", [("/health", 200), ("/unknown", 404)])
async def test_response_headers(path: str, status: int) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(path)

    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert UUID(response.headers["X-Request-ID"])


async def test_preserves_valid_request_id() -> None:
    request_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health", headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] == request_id


async def test_replaces_invalid_request_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health", headers={"X-Request-ID": "invalid"})

    assert UUID(response.headers["X-Request-ID"])


async def test_validation_error_has_headers() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/payload/invalid-uuid")

    assert response.status_code == 422
    assert response.headers["Cache-Control"] == "no-store"
    assert UUID(response.headers["X-Request-ID"])
