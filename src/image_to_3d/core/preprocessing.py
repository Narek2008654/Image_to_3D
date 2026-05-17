"""Image loading and preprocessing.

Turns an arbitrary user image into the normalized, background-removed,
gray-matted RGB image TripoSR expects. Raises typed errors so callers can
give actionable feedback instead of leaking stack traces.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import numpy as np
import rembg
from PIL import Image, UnidentifiedImageError

from image_to_3d.core.errors import InvalidImageError, NoForegroundError

# tsr is the vendored TripoSR package (see scripts/fetch_triposr.py).
from tsr.utils import remove_background, resize_foreground

ImageSource = Union[str, Path, bytes, Image.Image]

# Background-removed pixels are composited onto this neutral gray, matching
# upstream TripoSR preprocessing (run.py).
_MATTE_GRAY = 0.5

# Minimum fraction of opaque pixels for the result to count as "an object".
_MIN_FOREGROUND_FRACTION = 0.005

_rembg_session = None


def _get_rembg_session():
    """Create the rembg session once; it loads a model and is reusable."""
    global _rembg_session
    if _rembg_session is None:
        _rembg_session = rembg.new_session()
    return _rembg_session


def _load_image(source: ImageSource) -> Image.Image:
    try:
        if isinstance(source, Image.Image):
            return source.convert("RGB")
        if isinstance(source, bytes):
            return Image.open(io.BytesIO(source)).convert("RGB")
        path = Path(source)
        if not path.is_file():
            raise InvalidImageError(f"Image file not found: {path}")
        return Image.open(path).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(f"Could not decode image: {exc}") from exc


def preprocess(source: ImageSource, foreground_ratio: float) -> Image.Image:
    """Load, remove background, reframe, and gray-matte an input image.

    Returns an RGB ``PIL.Image`` ready for TripoSR inference.

    Raises:
        InvalidImageError: input missing or not a decodable image.
        NoForegroundError: nothing recognizable left after background removal.
    """
    image = _load_image(source)

    cut = remove_background(image, _get_rembg_session())  # RGBA, bg transparent
    cut = resize_foreground(cut, foreground_ratio)

    rgba = np.asarray(cut).astype(np.float32) / 255.0
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise NoForegroundError(
            "Background removal produced no object. Use an image with a single "
            "clear object on a plain background."
        )

    alpha = rgba[:, :, 3:4]
    if float(alpha.mean()) < _MIN_FOREGROUND_FRACTION:
        raise NoForegroundError(
            "No clear object detected after background removal. Try a photo of "
            "a single object on a plain background."
        )

    matted = rgba[:, :, :3] * alpha + (1.0 - alpha) * _MATTE_GRAY
    return Image.fromarray((matted * 255.0).astype(np.uint8))
