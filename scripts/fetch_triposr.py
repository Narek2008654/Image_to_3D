"""Vendor the TripoSR ``tsr`` package and apply the PyMCubes patch.

Why vendor instead of ``pip install``: upstream's requirements pull
``torchmcubes`` as a from-source build with no Windows / Python 3.13 wheels.
We copy only the ``tsr`` package and swap its single isosurface module for a
PyMCubes-backed one (``patches/isosurface_pymcubes.py``).

Idempotent: re-running replaces ``src/tsr`` cleanly. Verifies the patched
package imports before returning success.

Usage:
    python scripts/fetch_triposr.py [--ref <git-ref-or-sha>]
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = "VAST-AI-Research/TripoSR"
DEFAULT_REF = "main"  # pin to a SHA for full reproducibility once verified

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DEST = SRC / "tsr"
PATCH = ROOT / "patches" / "isosurface_pymcubes.py"


def _download_tarball(ref: str) -> bytes:
    url = f"https://github.com/{REPO}/archive/{ref}.tar.gz"
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
        return resp.read()


def _extract_tsr(tarball: bytes, dest: Path) -> str:
    """Extract just the ``tsr/`` package; return the archive's top dir name."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        top = tar.getnames()[0].split("/")[0]
        prefix = f"{top}/tsr/"
        members = [m for m in tar.getmembers() if m.name.startswith(prefix)]
        if not members:
            raise RuntimeError("Archive did not contain a 'tsr/' package.")
        for member in members:
            rel = member.name[len(prefix):]
            if not rel:
                continue
            target = dest / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = tar.extractfile(member)
                if extracted is not None:
                    target.write_bytes(extracted.read())
    return top


def _apply_patch() -> None:
    target = DEST / "models" / "isosurface.py"
    if not target.parent.exists():
        raise RuntimeError("Vendored tsr/models directory missing.")
    shutil.copyfile(PATCH, target)
    print(f"Patched {target.relative_to(ROOT)} -> PyMCubes")


def _write_vendor_info(ref: str, top: str) -> None:
    (DEST / "VENDOR_INFO.txt").write_text(
        f"source: https://github.com/{REPO}\n"
        f"ref: {ref}\n"
        f"archive_top: {top}\n"
        f"fetched_utc: {datetime.now(timezone.utc).isoformat()}\n"
        "patch: patches/isosurface_pymcubes.py (torchmcubes -> PyMCubes)\n",
        encoding="utf-8",
    )


def _verify_import() -> None:
    sys.path.insert(0, str(SRC))
    import importlib

    for mod in ("tsr.system", "tsr.utils", "tsr.models.isosurface"):
        importlib.import_module(mod)
    iso = importlib.import_module("tsr.models.isosurface")
    if not hasattr(iso, "MarchingCubeHelper"):
        raise RuntimeError("Patched isosurface is missing MarchingCubeHelper.")
    print("Import check OK: patched tsr package is usable.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vendor + patch TripoSR.")
    parser.add_argument("--ref", default=DEFAULT_REF)
    ref = parser.parse_args().ref

    if not PATCH.is_file():
        print(f"ERROR: patch file not found: {PATCH}", file=sys.stderr)
        return 1

    top = _extract_tsr(_download_tarball(ref), DEST)
    _apply_patch()
    _write_vendor_info(ref, top)
    _verify_import()
    print(f"\nVendored tsr from {REPO}@{ref} into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
