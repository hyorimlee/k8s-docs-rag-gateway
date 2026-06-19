"""Response schemas for the API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    environment: str
    version: str
