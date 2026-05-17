"""FastAPI application factory.

Wires the API routes, the single-worker job queue, the static web UI, and a
static mount that serves generated mesh files for download.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from image_to_3d.api.jobs import JobQueue
from image_to_3d.api.routes import router
from image_to_3d.core.config import ReconstructionOptions

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app() -> FastAPI:
    app = FastAPI(title="Image-to-3D", version="0.1.0")
    app.state.job_queue = JobQueue()

    app.include_router(router)

    # Generated meshes are served for download from the configured output dir.
    output_dir = ReconstructionOptions().output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=output_dir), name="files")

    # The web UI is the last mount so /api and /files take precedence.
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
    return app


app = create_app()
