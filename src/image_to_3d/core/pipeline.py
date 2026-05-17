"""The single public entry point of the core library.

``reconstruct`` runs the full image -> 3D mesh pipeline and returns a plain
result object. It contains no HTTP/web knowledge; the API layer and tests
depend only on this function.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from image_to_3d.core import model as _model
from image_to_3d.core.config import ReconstructionOptions
from image_to_3d.core.mesh import extract_and_export
from image_to_3d.core.preprocessing import ImageSource, preprocess


@dataclass(slots=True)
class ReconstructionResult:
    """Outcome of a reconstruction run."""

    files: dict[str, Path]  # export format -> file path
    vertex_count: int
    face_count: int
    elapsed_seconds: float
    output_dir: Path


def reconstruct(
    image: ImageSource,
    options: Optional[ReconstructionOptions] = None,
    job_id: Optional[str] = None,
) -> ReconstructionResult:
    """Convert one image of an object into exported 3D mesh files.

    Raises the typed errors from ``image_to_3d.core.errors`` for invalid input
    or empty foreground; lets unexpected exceptions propagate so the caller
    can log and surface them.
    """
    options = options or ReconstructionOptions()
    job_id = job_id or uuid.uuid4().hex
    out_dir = options.output_dir / job_id

    start = time.perf_counter()
    processed = preprocess(image, options.foreground_ratio)
    scene_codes = _model.infer(processed, options)
    loaded_model = _model.get_model(options)
    export = extract_and_export(loaded_model, scene_codes, options, out_dir)
    elapsed = time.perf_counter() - start

    return ReconstructionResult(
        files=export.files,
        vertex_count=export.vertex_count,
        face_count=export.face_count,
        elapsed_seconds=round(elapsed, 2),
        output_dir=out_dir,
    )
