"""Pydantic schemas for the FastAPI server.

Defines request/response models for the REST API endpoints including
job submission, chat messages, and file attachments.
"""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel

# Re-export Attachment from domain schemas to avoid duplication
from dta.dti.schemas import Attachment

__all__ = [
    "Attachment",
    "ChatMessage",
    "ChatRequest",
    "CreateJobRequest",
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    "JobStatus",
    "JobSubmitRequest",
    "Plan",
    "HealthResponse",
    "CapabilitiesResponse",
    "JobListResponse",
    "MetricsResponse",
    "UploadResponse",
]

Role = Literal["user", "assistant"]


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""

    VALIDATION_ERROR = "validation_error"
    MISSING_INPUT = "missing_input"
    MODEL_NOT_INSTALLED = "model_not_installed"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"


class ErrorDetail(BaseModel):  # type: ignore[misc]
    """Details of the error."""

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):  # type: ignore[misc]
    """Standardized error response schema."""

    ok: Literal[False] = False
    error: ErrorDetail


class ChatMessage(BaseModel):  # type: ignore[misc]
    """Single message in a chat conversation."""

    role: Role
    content: str


class ChatRequest(BaseModel):  # type: ignore[misc]
    """Request containing chat message history."""

    messages: list[ChatMessage]


class JobSubmitRequest(BaseModel):  # type: ignore[misc]
    """Request for submitting a new job."""

    prompt: str
    mode: str = "hybrid"  # hybrid/llm/template
    attachments: list[Attachment] = []
    context: dict[str, Any] | None = None


class Plan(BaseModel):  # type: ignore[misc]
    """Execution plan for a pipeline of analysis steps."""

    tags: list[str] = []
    goals: list[str] = []
    pipeline: list[str] = []  # tool ids
    inputs: dict[str, Any] = {}  # e.g., {"file_path": "..."}
    meta: dict[str, Any] = {}


class CreateJobRequest(BaseModel):  # type: ignore[misc]
    """Request to create a job from a pre-defined plan."""

    plan: Plan


class JobStatus(BaseModel):  # type: ignore[misc]
    """Current status and results of a job."""

    id: str
    state: Literal["queued", "running", "succeeded", "failed"] = "queued"
    progress: float = 0.0
    message: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):  # type: ignore[misc]
    """Response schema for the health check endpoint."""

    ok: bool = True
    service: str = "DT4LC"
    version: str = "1.0.0"


class CapabilitiesResponse(BaseModel):  # type: ignore[misc]
    """Response schema for listing registry capabilities."""

    version: str
    types: list[str]
    instances: list[dict[str, Any]]
    count: int


class JobListResponse(BaseModel):  # type: ignore[misc]
    """Response schema for a paginated list of background jobs."""

    jobs: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class MetricsResponse(BaseModel):  # type: ignore[misc]
    """Response schema for system execution and LLM metrics."""

    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: float
    total_llm_calls: int
    total_llm_tokens: int
    total_llm_cost: float
    llm_by_provider: dict[str, Any]


class UploadResponse(BaseModel):  # type: ignore[misc]
    """Response schema for a successful GeoTIFF file upload."""

    ok: bool = True
    filename: str
    path: str
    size_bytes: int
