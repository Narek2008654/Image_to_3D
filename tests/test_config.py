"""ReconstructionOptions output-dir resolution (env override for containers)."""

from __future__ import annotations

from pathlib import Path

from image_to_3d.core.config import OUTPUT_DIR_ENV, ReconstructionOptions


def test_output_dir_defaults_to_outputs(monkeypatch):
    monkeypatch.delenv(OUTPUT_DIR_ENV, raising=False)
    assert ReconstructionOptions().output_dir == Path("outputs").resolve()


def test_output_dir_honors_env(monkeypatch, tmp_path):
    target = tmp_path / "container_out"
    monkeypatch.setenv(OUTPUT_DIR_ENV, str(target))
    assert ReconstructionOptions().output_dir == target.resolve()


def test_explicit_output_dir_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv(OUTPUT_DIR_ENV, str(tmp_path / "from_env"))
    explicit = tmp_path / "explicit"
    # An explicit argument still wins over the env default.
    assert ReconstructionOptions(output_dir=explicit).output_dir == explicit
