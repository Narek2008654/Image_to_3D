"""Opt-in end-to-end test: the real TripoSR model on a synthetic object.

Deselected by default (pyproject sets ``-m 'not slow'``). Run explicitly:

    pytest -m slow

Downloads ~2 GB of weights on first run and takes ~30 s - 2 min on CPU.
"""

from __future__ import annotations

import io

import pytest
import trimesh

from image_to_3d.core import reconstruct
from image_to_3d.core.config import ReconstructionOptions


@pytest.mark.slow
def test_real_reconstruction_produces_loadable_mesh(tmp_path, sphere_image):
    buf = io.BytesIO()
    sphere_image.save(buf, format="PNG")

    options = ReconstructionOptions(mc_resolution=128, output_dir=tmp_path)
    result = reconstruct(buf.getvalue(), options, job_id="e2e")

    assert result.vertex_count > 0
    assert result.face_count > 0
    for fmt in ("glb", "obj", "stl"):
        path = result.files[fmt]
        assert path.is_file() and path.stat().st_size > 0

    mesh = trimesh.load(result.files["glb"], force="mesh")
    assert len(mesh.vertices) > 0 and len(mesh.faces) > 0
