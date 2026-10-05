from fastapi import FastAPI

app = FastAPI(title="Caching Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
