"""Health, capabilities, models, and metrics endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from dta.dti.metrics import get_metrics_collector
from dta.dti.models.registry import get_model_registry
from dta.dti.registry import load_registry

from ..schemas import CapabilitiesResponse, HealthResponse, MetricsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)  # type: ignore[misc]
async def health() -> dict[str, Any]:
    """Health check endpoint.

    Returns the current operational status and version of the API.
    """
    return {"ok": True, "service": "DT4LC", "version": "1.0.0"}


@router.get("/capabilities", response_model=CapabilitiesResponse)  # type: ignore[misc]
async def list_capabilities() -> JSONResponse:
    """List all available components from the registry.

    Returns models, algorithms, and other registered components.
    """
    try:
        registry = load_registry()
        return JSONResponse(
            {
                "version": registry.version,
                "types": registry.types,
                "instances": [item.model_dump() for item in registry.instances],
                "count": len(registry.instances),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load registry: {e}") from e


@router.get("/models")  # type: ignore[misc]
async def list_models() -> JSONResponse:
    """List all registered models from the model registry.

    Returns model information including requirements, availability, and metadata.
    """
    try:
        registry = get_model_registry()
        models = []

        for model_id, model in registry._models.items():
            models.append(
                {
                    "id": model_id,
                    "name": model.name,
                    "installed": model.installed,
                    "size_mb": model.size_mb,
                    "description": model.description,
                    "requires": model.requires,
                }
            )

        try:
            base_registry = load_registry()
            for item in base_registry.instances:
                if item.type == "model" and item.metadata.get("hosting") != "local":
                    models.append(
                        {
                            "id": item.id,
                            "name": item.name,
                            "installed": item.integration.status == "ready",
                            "size_mb": 0,
                            "description": item.description,
                            "requires": [],
                            "status": item.integration.status,
                            "keywords": item.keywords,
                            "hosting": item.metadata.get("hosting", "external"),
                            "team": item.metadata.get("team", ""),
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to load hosted models from YAML registry: {e}")

        return JSONResponse({"models": models, "count": len(models)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load models: {e}") from e


@router.get("/metrics", response_model=MetricsResponse)  # type: ignore[misc]
async def get_metrics() -> JSONResponse:
    """Get system metrics including execution and LLM stats."""
    try:
        collector = get_metrics_collector()
        stats = collector.get_stats()

        return JSONResponse(
            {
                "total_executions": stats.total_executions,
                "successful_executions": stats.successful_executions,
                "failed_executions": stats.failed_executions,
                "average_duration_seconds": stats.avg_execution_time,
                "total_llm_calls": stats.total_llm_calls,
                "total_llm_tokens": stats.total_llm_tokens,
                "total_llm_cost": stats.total_llm_cost,
                "llm_by_provider": stats.llm_by_provider,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}") from e
