"""API routes: submit a reconstruction, poll its status, health check."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from image_to_3d.api.schemas import (
    Health,
    JobState,
    JobStatus,
    ReconstructAccepted,
)
from image_to_3d.core import ReconstructionOptions
from image_to_3d.core import model as core_model

router = APIRouter(prefix="/api")

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB is plenty for a single photo


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(
        model_loaded=core_model.is_loaded(),
        model_loading=core_model.is_loading(),
    )


@router.post("/reconstruct", response_model=ReconstructAccepted, status_code=202)
async def reconstruct_endpoint(
    request: Request,
    image: UploadFile = File(...),
    mc_resolution: int = Form(192),
) -> ReconstructAccepted:
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 25 MB).")
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")

    try:
        options = ReconstructionOptions(mc_resolution=mc_resolution)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = request.app.state.job_queue.submit(data, options)
    return ReconstructAccepted(job_id=job.job_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(request: Request, job_id: str) -> JobStatus:
    job = request.app.state.job_queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")

    status = JobStatus(job_id=job.job_id, state=job.state, error=job.error)
    if job.state is JobState.DONE and job.result is not None:
        result = job.result
        status.downloads = {
            fmt: f"/files/{job_id}/{path.name}"
            for fmt, path in result.files.items()
        }
        status.vertex_count = result.vertex_count
        status.face_count = result.face_count
        status.elapsed_seconds = result.elapsed_seconds
    return status
