"""Typed errors raised by the core pipeline.

Callers (API, CLI, tests) match on these instead of parsing strings.
"""


class ReconstructionError(Exception):
    """Base class for every error the reconstruction pipeline can raise."""


class InvalidImageError(ReconstructionError):
    """The input is missing, corrupt, or not a decodable image."""


class NoForegroundError(ReconstructionError):
    """Background removal left no usable object (empty/transparent result)."""
