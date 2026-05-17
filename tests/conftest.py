"""Shared fixtures.

We synthesize test images at runtime (a shaded sphere on a plain background)
instead of committing binary fixtures: deterministic, reviewable, and a
realistic "single object on plain background" input for TripoSR.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image


def _sphere_image(size: int = 256) -> Image.Image:
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    cx = cy = size / 2.0
    r = size * 0.35
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

    img = np.full((size, size, 3), 245, dtype=np.uint8)  # plain near-white bg
    mask = dist <= r
    # Simple diffuse shading so the object has depth cues.
    z = np.sqrt(np.clip(r**2 - (xx - cx) ** 2 - (yy - cy) ** 2, 0, None))
    shade = (0.35 + 0.65 * (z / (r + 1e-6))).clip(0, 1)
    for c, base in enumerate((70, 130, 220)):
        channel = img[:, :, c]
        channel[mask] = (base * shade[mask]).astype(np.uint8)
    return Image.fromarray(img, "RGB")


@pytest.fixture
def sphere_image() -> Image.Image:
    return _sphere_image()


@pytest.fixture
def sphere_png_bytes(sphere_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    sphere_image.save(buf, format="PNG")
    return buf.getvalue()
