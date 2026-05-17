"""Thin compatibility shim over the vendored TripoSR ``extract_mesh``.

Upstream returns a *list* of meshes and has changed the ``has_vertex_color``
parameter across revisions. Isolating that here keeps ``core.mesh`` clean and
gives one place to adapt if the vendored revision changes.
"""

from __future__ import annotations

import inspect

import torch
import trimesh


def extract_first_mesh(
    model, scene_codes: torch.Tensor, resolution: int
) -> trimesh.Trimesh:
    """Return the first colored mesh for the given scene codes."""
    params = inspect.signature(model.extract_mesh).parameters
    kwargs: dict[str, object] = {"resolution": resolution}
    if "has_vertex_color" in params:
        kwargs["has_vertex_color"] = True

    meshes = model.extract_mesh(scene_codes, **kwargs)
    if not meshes:
        raise RuntimeError("TripoSR returned no mesh for this image.")
    return meshes[0]
