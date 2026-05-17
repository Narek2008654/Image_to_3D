"""Configuration for a reconstruction run.

Defaults are tuned for CPU-only inference (low marching-cubes resolution,
modest chunk size) so a run finishes in roughly 30 s - 2 min on a laptop CPU.
Callers may override any field per request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

MODEL_ID = "stabilityai/TripoSR"

# Mesh export formats produced for every run, in trimesh-export order.
EXPORT_FORMATS: tuple[str, ...] = ("glb", "obj", "stl")


def _default_output_dir() -> Path:
    return Path("outputs").resolve()


@dataclass(slots=True)
class ReconstructionOptions:
    """Per-run knobs trading quality against CPU time/RAM.

    mc_resolution:    marching-cubes grid size. Higher = finer mesh, much
                      slower. 192 is a sane CPU default; 256 is the upstream
                      default; 128 is fast/blocky.
    chunk_size:       density-field query batch. Lower = less RAM, slower.
    foreground_ratio: how much of the framed image the object should fill
                      after background removal (passed to resize_foreground).
    output_dir:       where the per-job mesh files are written.
    device:           torch device. CPU-only on the target hardware.
    """

    mc_resolution: int = 192
    chunk_size: int = 4096
    foreground_ratio: float = 0.85
    output_dir: Path = field(default_factory=_default_output_dir)
    device: str = "cpu"
    model_id: str = MODEL_ID

    def __post_init__(self) -> None:
        if not 32 <= self.mc_resolution <= 512:
            raise ValueError("mc_resolution must be between 32 and 512")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        if not 0.1 <= self.foreground_ratio <= 1.0:
            raise ValueError("foreground_ratio must be between 0.1 and 1.0")
        self.output_dir = Path(self.output_dir)
