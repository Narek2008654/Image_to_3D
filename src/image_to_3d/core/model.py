"""TripoSR model loading and inference (CPU).

The model is loaded lazily and cached process-wide: weights are ~2-3 GB and
loading is slow, so we never load more than once. The API runs a single
worker, so a module-level singleton is the right amount of machinery here.
"""

from __future__ import annotations

import threading
from typing import Optional

import torch
from PIL import Image

from image_to_3d.core.config import ReconstructionOptions

# tsr is the vendored TripoSR package (see scripts/fetch_triposr.py).
from tsr.system import TSR

_model: Optional[TSR] = None
_model_lock = threading.Lock()
_loading = False


def is_loaded() -> bool:
    """True once the model is in memory (used by the API health endpoint)."""
    return _model is not None


def is_loading() -> bool:
    """True while weights are being fetched/loaded (first run downloads ~2 GB)."""
    return _loading


def _load(options: ReconstructionOptions) -> TSR:
    global _model, _loading
    with _model_lock:
        if _model is not None:
            return _model
        _loading = True
        try:
            model = TSR.from_pretrained(
                options.model_id,
                config_name="config.yaml",
                weight_name="model.ckpt",
            )
            model.to(options.device)
            model.eval()
            _model = model
            return _model
        finally:
            _loading = False


def get_model(options: ReconstructionOptions) -> TSR:
    """Return the loaded model, applying per-request runtime options.

    chunk_size is re-applied every call because it is a per-request knob and
    the model itself is a cached singleton shared across requests.
    """
    model = _load(options)
    model.renderer.set_chunk_size(options.chunk_size)
    return model


def infer(image: Image.Image, options: ReconstructionOptions) -> torch.Tensor:
    """Run TripoSR on a preprocessed image, returning scene codes."""
    model = get_model(options)
    with torch.no_grad():
        return model(image, device=options.device)
