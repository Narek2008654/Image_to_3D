"""Tests for the critical PyMCubes patch and mesh export.

These run without TripoSR weights: they exercise the patched isosurface
directly on a synthetic density field, which is exactly the contract
``tsr.system.extract_mesh`` relies on.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
import trimesh

from tsr.models.isosurface import MarchingCubeHelper


@pytest.fixture
def sphere_level() -> tuple[int, torch.Tensor]:
    """level = -(density - threshold) for a sphere, as extract_mesh passes."""
    res = 48
    lin = np.linspace(-1, 1, res, dtype=np.float32)
    x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
    density = 1.0 - np.sqrt(x**2 + y**2 + z**2)  # >0 inside the unit sphere
    threshold = 0.0
    level = -(torch.from_numpy(density).reshape(-1) - threshold)
    return res, level


def test_marching_cubes_produces_nonempty_normalized_mesh(sphere_level):
    res, level = sphere_level
    helper = MarchingCubeHelper(res)

    verts, faces = helper(level)

    assert verts.ndim == 2 and verts.shape[1] == 3
    assert faces.ndim == 2 and faces.shape[1] == 3
    assert verts.shape[0] > 0 and faces.shape[0] > 0
    # forward() normalizes vertices into [0, 1].
    assert float(verts.min()) >= -1e-6
    assert float(verts.max()) <= 1.0 + 1e-6
    assert faces.dtype == torch.int64


def test_grid_vertices_shape_and_range():
    res = 16
    helper = MarchingCubeHelper(res)
    grid = helper.grid_vertices
    assert grid.shape == (res**3, 3)
    assert float(grid.min()) == pytest.approx(0.0)
    assert float(grid.max()) == pytest.approx(1.0)


@pytest.mark.parametrize("fmt", ["glb", "obj", "stl"])
def test_export_roundtrip(sphere_level, tmp_path, fmt):
    res, level = sphere_level
    verts, faces = MarchingCubeHelper(res)(level)
    mesh = trimesh.Trimesh(vertices=verts.numpy(), faces=faces.numpy())

    out = tmp_path / f"model.{fmt}"
    mesh.export(out)

    assert out.is_file() and out.stat().st_size > 0
    reloaded = trimesh.load(out, force="mesh")
    assert len(reloaded.vertices) > 0 and len(reloaded.faces) > 0
