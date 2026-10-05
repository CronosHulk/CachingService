from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from caching_service.adapters.inbound.api.dependencies import get_engine
from caching_service.adapters.inbound.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        if get_engine.cache_info().currsize:
            await get_engine().dispose()
            get_engine.cache_clear()


app = FastAPI(title="Caching Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
