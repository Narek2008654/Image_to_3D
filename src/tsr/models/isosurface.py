"""Marching-cubes isosurface extraction backed by PyMCubes.

Drop-in replacement for the vendored TripoSR ``tsr/models/isosurface.py``.
Upstream hardcodes ``torchmcubes`` (a from-source C++/CUDA build that has no
Windows / Python 3.13 wheels). PyMCubes ships prebuilt wheels and runs on CPU.

The public surface intentionally matches upstream so the rest of the
(unmodified) TripoSR package keeps working:

  * ``IsosurfaceHelper`` base class
  * ``MarchingCubeHelper(resolution)`` with ``.points_range``,
    ``.grid_vertices`` (flattened (R**3, 3) coords in [0, 1]), and
    ``forward(level) -> (vertices_in_[0,1], faces)`` as torch tensors.

``tsr.system.TSR.extract_mesh`` passes ``level = -(density - threshold)``;
PyMCubes extracts the surface where the volume crosses 0.0, so the contract
is identical to the original torchmcubes path (axis swap and normalization
preserved).
"""

from __future__ import annotations

import mcubes
import numpy as np
import torch
import torch.nn as nn


class IsosurfaceHelper(nn.Module):
    points_range = (0, 1)

    @property
    def grid_vertices(self) -> torch.FloatTensor:
        raise NotImplementedError


class MarchingCubeHelper(IsosurfaceHelper):
    def __init__(self, resolution: int) -> None:
        super().__init__()
        self.resolution = resolution
        self.points_range = (0, 1)
        self._grid_vertices: torch.FloatTensor | None = None

    @property
    def grid_vertices(self) -> torch.FloatTensor:
        if self._grid_vertices is None:
            x = torch.linspace(0, 1, self.resolution)
            x, y, z = torch.meshgrid(x, x, x, indexing="ij")
            verts = torch.cat(
                [x.reshape(-1, 1), y.reshape(-1, 1), z.reshape(-1, 1)], dim=-1
            )
            self._grid_vertices = verts
        return self._grid_vertices

    def forward(self, level: torch.FloatTensor):
        # level is the negated density field; the surface is the 0 level set.
        grid = (
            -level.view(self.resolution, self.resolution, self.resolution)
            .detach()
            .cpu()
            .numpy()
            .astype(np.float64)
        )
        verts, faces = mcubes.marching_cubes(grid, 0.0)

        verts = torch.from_numpy(np.ascontiguousarray(verts)).float()
        faces = torch.from_numpy(
            np.ascontiguousarray(faces.astype(np.int64))
        ).long()

        # Match upstream torchmcubes path: swap to (x, y, z) and normalize the
        # vertex coordinates from voxel indices into the [0, 1] range.
        verts = verts[:, [2, 1, 0]]
        verts = verts / (self.resolution - 1.0)
        return verts, faces
