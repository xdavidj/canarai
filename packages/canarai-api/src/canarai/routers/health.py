"""Health check endpoint."""

from fastapi import APIRouter

from canarai import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return API health status and version."""
    return {
        "status": "ok",
        "version": __version__,
    }
