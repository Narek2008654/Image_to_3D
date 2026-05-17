"""Mesh extraction and export.

TripoSR turns scene codes into a colored triangle mesh via marching cubes
(patched to use PyMCubes instead of the unbuildable torchmcubes). We export
the mesh to every format in EXPORT_FORMATS using trimesh.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import trimesh

from image_to_3d.core.config import EXPORT_FORMATS, ReconstructionOptions
from image_to_3d.tsr_compat import extract_first_mesh


@dataclass(slots=True)
class MeshExport:
    """Exported mesh files plus basic geometry stats."""

    files: dict[str, Path]  # format -> path, e.g. {"glb": .../model.glb}
    vertex_count: int
    face_count: int


def extract_and_export(
    model,
    scene_codes: torch.Tensor,
    options: ReconstructionOptions,
    out_dir: Path,
    stem: str = "model",
) -> MeshExport:
    """Extract the mesh and write one file per EXPORT_FORMATS format."""
    mesh: trimesh.Trimesh = extract_first_mesh(
        model, scene_codes, resolution=options.mc_resolution
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    for fmt in EXPORT_FORMATS:
        path = out_dir / f"{stem}.{fmt}"
        mesh.export(path)
        files[fmt] = path

    return MeshExport(
        files=files,
        vertex_count=int(mesh.vertices.shape[0]),
        face_count=int(mesh.faces.shape[0]),
    )
