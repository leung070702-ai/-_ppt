"""Protocol-only API routes for the initial project skeleton."""

from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    """Return a stable liveness response without touching business services."""

    return HealthResponse(status="ok", service="backend")
