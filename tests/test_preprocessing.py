"""Preprocessing tests. rembg/TripoSR background removal is mocked so these
stay fast and deterministic; only our load/validate/matte logic is exercised.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from image_to_3d.core import preprocessing
from image_to_3d.core.errors import InvalidImageError, NoForegroundError


@pytest.fixture(autouse=True)
def _stub_rembg(monkeypatch):
    monkeypatch.setattr(preprocessing, "_get_rembg_session", lambda: object())
    monkeypatch.setattr(
        preprocessing, "resize_foreground", lambda img, ratio: img
    )


def _rgba(opaque: bool) -> Image.Image:
    arr = np.zeros((64, 64, 4), dtype=np.uint8)
    if opaque:
        arr[16:48, 16:48, :3] = (200, 60, 60)
        arr[16:48, 16:48, 3] = 255
    return Image.fromarray(arr, "RGBA")


def test_missing_file_raises_invalid(tmp_path):
    with pytest.raises(InvalidImageError):
        preprocessing.preprocess(tmp_path / "nope.png", 0.85)


def test_corrupt_bytes_raise_invalid():
    with pytest.raises(InvalidImageError):
        preprocessing.preprocess(b"not an image", 0.85)


def test_no_foreground_raises(monkeypatch, sphere_png_bytes):
    monkeypatch.setattr(
        preprocessing, "remove_background", lambda img, s: _rgba(opaque=False)
    )
    with pytest.raises(NoForegroundError):
        preprocessing.preprocess(sphere_png_bytes, 0.85)


def test_success_returns_rgb_image(monkeypatch, sphere_png_bytes):
    monkeypatch.setattr(
        preprocessing, "remove_background", lambda img, s: _rgba(opaque=True)
    )
    out = preprocessing.preprocess(sphere_png_bytes, 0.85)
    assert isinstance(out, Image.Image)
    assert out.mode == "RGB"
    assert out.size == (64, 64)
