"""Pipeline orchestration test with the model fully stubbed."""

from __future__ import annotations

from pathlib import Path

from image_to_3d.core import pipeline
from image_to_3d.core.config import ReconstructionOptions
from image_to_3d.core.mesh import MeshExport


def test_reconstruct_orchestration(monkeypatch, tmp_path, sphere_png_bytes):
    monkeypatch.setattr(pipeline, "preprocess", lambda src, ratio: "IMG")
    monkeypatch.setattr(pipeline._model, "infer", lambda img, opts: "CODES")
    monkeypatch.setattr(pipeline._model, "get_model", lambda opts: "MODEL")

    captured = {}

    def fake_export(model, codes, opts, out_dir, stem="model"):
        captured["args"] = (model, codes, out_dir)
        files = {"glb": out_dir / "model.glb"}
        return MeshExport(files=files, vertex_count=12, face_count=20)

    monkeypatch.setattr(pipeline, "extract_and_export", fake_export)

    options = ReconstructionOptions(output_dir=tmp_path)
    result = pipeline.reconstruct(sphere_png_bytes, options, job_id="job1")

    assert captured["args"][0] == "MODEL"
    assert captured["args"][1] == "CODES"
    assert result.vertex_count == 12
    assert result.face_count == 20
    assert result.elapsed_seconds >= 0
    assert result.output_dir == tmp_path / "job1"
    assert result.files["glb"] == tmp_path / "job1" / "model.glb"
    assert isinstance(result.output_dir, Path)
