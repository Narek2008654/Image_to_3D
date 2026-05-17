"""Core reconstruction library: pure Python, no HTTP/web knowledge.

The single public entry point is :func:`image_to_3d.core.pipeline.reconstruct`.
"""

from image_to_3d.core.config import ReconstructionOptions
from image_to_3d.core.errors import (
    InvalidImageError,
    NoForegroundError,
    ReconstructionError,
)
from image_to_3d.core.pipeline import ReconstructionResult, reconstruct

__all__ = [
    "ReconstructionOptions",
    "ReconstructionResult",
    "reconstruct",
    "ReconstructionError",
    "InvalidImageError",
    "NoForegroundError",
]
