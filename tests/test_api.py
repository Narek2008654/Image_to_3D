"""API tests with the core reconstruction stubbed at the job boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from image_to_3d.api import jobs as jobs_module
from image_to_3d.api.main import create_app
from image_to_3d.core.pipeline import ReconstructionResult


@pytest.fixture
def client(monkeypatch):
    def fake_reconstruct(image_bytes, options, job_id=None):
        out = options.output_dir / job_id
        return ReconstructionResult(
            files={"glb": out / "model.glb", "obj": out / "model.obj"},
            vertex_count=100,
            face_count=180,
            elapsed_seconds=1.5,
            output_dir=out,
        )

    monkeypatch.setattr(jobs_module, "reconstruct", fake_reconstruct)
    app = create_app()
    with TestClient(app) as c:
        c._queue = app.state.job_queue
        yield c


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False


def test_reconstruct_rejects_non_image(client):
    r = client.post(
        "/api/reconstruct",
        files={"image": ("a.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_reconstruct_rejects_empty_upload(client):
    r = client.post(
        "/api/reconstruct",
        files={"image": ("a.png", b"", "image/png")},
    )
    assert r.status_code == 400


def test_reconstruct_rejects_bad_resolution(client, sphere_png_bytes):
    r = client.post(
        "/api/reconstruct",
        files={"image": ("a.png", sphere_png_bytes, "image/png")},
        data={"mc_resolution": "9999"},
    )
    assert r.status_code == 400


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/does-not-exist").status_code == 404


def test_job_lifecycle(client, sphere_png_bytes):
    r = client.post(
        "/api/reconstruct",
        files={"image": ("a.png", sphere_png_bytes, "image/png")},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    assert client._queue.get(job_id).wait(timeout=10)

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["state"] == "done"
    assert status["vertex_count"] == 100
    assert status["face_count"] == 180
    assert status["downloads"]["glb"] == f"/files/{job_id}/model.glb"
    assert set(status["downloads"]) == {"glb", "obj"}
