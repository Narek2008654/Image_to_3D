"""Reproducible environment bootstrap.

Creates an isolated ``.venv`` on a supported Python (3.10-3.12; the system
Python may be 3.13, which lacks wheels for some deps), installs CPU-only
dependencies, vendors + patches TripoSR, then verifies every critical import.

Fails loudly with actionable guidance rather than producing a half-broken
environment.

Usage:
    python scripts/setup_env.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
TORCH_CPU_INDEX = "https://download.pytorch.org/whl/cpu"

# torch/torchvision come from the CPU index; the rest from PyPI.
TORCH_PKGS = ["torch==2.2.2", "torchvision==0.17.2"]
PYPI_PKGS = [
    # 4.40.2 pulls tokenizers 0.19 (prebuilt cp312 wheels); API-compatible
    # with TripoSR's ViT/DINO backbone. Older 4.35 forced a Rust build.
    "transformers==4.40.2",
    "omegaconf==2.3.0",
    "einops==0.7.0",
    "Pillow==10.1.0",
    "numpy<2",
    "rembg==2.0.59",
    "onnxruntime==1.17.3",
    # 0.1.6 ships prebuilt cp312 wheels; 0.1.4 forced a C++ source build.
    "PyMCubes==0.1.6",
    "trimesh==4.0.5",
    "huggingface-hub",
    "fastapi==0.110.0",
    "uvicorn==0.29.0",
    "python-multipart==0.0.9",
    "pytest==8.1.1",
    "httpx==0.27.0",
]
VERIFY_IMPORTS = [
    "torch",
    "torchvision",
    "transformers",
    "omegaconf",
    "PIL",
    "numpy",
    "rembg",
    "mcubes",
    "trimesh",
    "fastapi",
    "tsr.system",
    "tsr.models.isosurface",
]


SUPPORTED = {"3.10", "3.11", "3.12"}


def _is_supported(cmd: list[str]) -> bool:
    """True if running ``cmd`` yields a supported Python minor version."""
    try:
        out = subprocess.run(
            [*cmd, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0 and out.stdout.strip() in SUPPORTED


def _candidate_commands() -> list[list[str]]:
    cmds: list[list[str]] = []
    if sys.version_info[:2] in {(3, 10), (3, 11), (3, 12)}:
        cmds.append([sys.executable])
    if os.name == "nt":
        cmds += [["py", f"-{m}"] for m in ("3.12", "3.11", "3.10")]
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        cmds += [
            [str(local / "Programs" / "Python" / f"Python{v}" / "python.exe")]
            for v in ("312", "311", "310")
        ]
    else:
        cmds += [["python3.12"], ["python3.11"], ["python3.10"]]
    return cmds


def _find_interpreter() -> list[str]:
    for cmd in _candidate_commands():
        if _is_supported(cmd):
            return cmd
    raise SystemExit(
        "No Python 3.10-3.12 found. Install one (e.g. python.org 3.12) and "
        "re-run. The system Python 3.13 is not supported (missing wheels)."
    )


def _run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _venv_python() -> str:
    if os.name == "nt":
        return str(VENV / "Scripts" / "python.exe")
    return str(VENV / "bin" / "python")


def main() -> int:
    interp = _find_interpreter()
    print(f"Using interpreter: {' '.join(interp)}")

    if not VENV.exists():
        _run([*interp, "-m", "venv", str(VENV)])

    py = _venv_python()
    _run([py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    _run([py, "-m", "pip", "install", "--index-url", TORCH_CPU_INDEX, *TORCH_PKGS])
    _run([py, "-m", "pip", "install", *PYPI_PKGS])

    # Vendor TripoSR BEFORE the editable install so the `tsr` package exists
    # at package-discovery time (strict PEP 660 finders won't pick it up
    # otherwise). fetch_triposr's import check needs torch, already installed.
    _run([py, str(ROOT / "scripts" / "fetch_triposr.py")])

    _run([py, "-m", "pip", "install", "-e", str(ROOT)])

    check = "import importlib,sys; [importlib.import_module(m) for m in sys.argv[1:]]; print('ALL IMPORTS OK')"
    _run([py, "-c", check, *VERIFY_IMPORTS])

    print(
        "\nSetup complete. Start the app with:\n"
        f"  {py} -m uvicorn image_to_3d.api.main:app\n"
        "Then open http://localhost:8000"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
