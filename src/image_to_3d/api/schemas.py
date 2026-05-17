"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class ReconstructAccepted(BaseModel):
    """Returned by POST /api/reconstruct once a job is enqueued."""

    job_id: str
    state: JobState = JobState.QUEUED


class JobStatus(BaseModel):
    """Returned by GET /api/jobs/{id}."""

    job_id: str
    state: JobState
    error: Optional[str] = None
    # Populated only when state == DONE.
    downloads: dict[str, str] = Field(default_factory=dict)  # fmt -> URL
    vertex_count: Optional[int] = None
    face_count: Optional[int] = None
    elapsed_seconds: Optional[float] = None


class Health(BaseModel):
    """Returned by GET /api/health."""

    status: str = "ok"
    model_loaded: bool
    model_loading: bool
