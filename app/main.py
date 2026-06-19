"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.config import APP_ENV, APP_NAME, APP_VERSION
from app.schemas import HealthResponse

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return basic service health information."""
    return HealthResponse(
        status="ok",
        service=APP_NAME,
        environment=APP_ENV,
        version=APP_VERSION,
    )
