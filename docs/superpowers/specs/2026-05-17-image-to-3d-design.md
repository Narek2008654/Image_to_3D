# Image-to-3D — Design Spec

**Date:** 2026-05-17
**Status:** Approved (pending spec review)

## 1. Goal & Scope

Build a free, local tool that turns **one 2D photo of an object** into a
**rotatable 3D mesh** the user can preview in a browser and download.

**In scope (v1):**

- Single input image of a single object (toy, product, character, furniture, etc.).
- Output: a 3D mesh exported as both `.glb` and `.obj`.
- In-browser rotatable preview and download.
- Runs entirely locally on CPU. No API keys, no cloud, no usage limits, no cost.
- 3-layer architecture so a future phone app reuses the backend unchanged.

**Out of scope (v1):**

- Full scenes / landscapes / multi-object reconstruction.
- Multi-image or video input.
- The phone app itself (only the architecture must accommodate it).
- GPU/CUDA acceleration (designed CPU-first; GPU is a future optimization).
- Authentication, multi-user accounts, hosted deployment.

## 2. Constraints

- **Hardware:** Intel i7-1355U (12 threads), 15.7 GB RAM, Intel Iris Xe
  (integrated, no CUDA). CPU-only inference.
- **Free & unlimited:** all components open-source and permissively licensed;
  no metered services.
- **Future phone app:** thin client + self-hosted backend. The phone never runs
  the heavy model; it calls the same HTTP API as the web frontend.

## 3. AI Model Choice

**TripoSR** (Stability AI + Tripo AI, MIT license).

Rationale:

- Feed-forward transformer (no iterative diffusion) → tractable on CPU
  (~30 s–2 min per image at default resolution).
- MIT-licensed code and weights → genuinely free, including commercial use.
- Single image → textured mesh in one pass; mature, documented codebase.
- Heavier alternatives (TRELLIS, InstantMesh, Hunyuan3D) require a CUDA GPU and
  are infeasible on this hardware.

Weights download once from Hugging Face (`stabilityai/TripoSR`) and are cached
locally. First run requires internet for this one-time download; thereafter the
tool is fully offline.

## 4. Architecture

Three clean, independently testable layers:

```
src/image_to_3d/
  core/                 Pure Python. Image -> 3D mesh. No web/HTTP knowledge.
    config.py           Settings: resolution, output dir, device, model id.
    preprocessing.py    Load, validate, resize, background removal (rembg),
                        foreground crop.
    model.py            TripoSR load + inference wrapper.
    mesh.py             Marching cubes (PyMCubes), vertex colors, export glb/obj.
    pipeline.py         Orchestrates preprocess -> infer -> mesh -> export.
  api/                  Thin FastAPI layer over core.
    main.py             App factory, static file serving for web/.
    routes.py           POST /api/reconstruct, GET /api/jobs/{id}, GET /api/health.
    jobs.py             In-process single-worker job queue + status tracking.
    schemas.py          Pydantic request/response models.
  web/                  Static frontend (no build step).
    index.html          Drag-drop upload, progress, preview, download.
    app.js              Calls the API, polls job status.
    styles.css          Clean, minimal, professional styling.
```

**Layer contracts:**

- `core` exposes one primary entry point:
  `pipeline.reconstruct(image_path_or_bytes, options) -> ReconstructionResult`
  where `ReconstructionResult` holds paths to the exported `.glb`/`.obj` and
  metadata (vertex/face counts, timing). `core` has zero dependency on `api`.
- `api` depends only on `core`'s public entry point. It owns concurrency,
  HTTP concerns, and file serving. It does not contain reconstruction logic.
- `web` depends only on the HTTP API. The future phone app is a sibling of
  `web` at this layer — it requires no backend changes.

## 5. Data Flow

1. User drag-drops/selects an image in `web`.
2. `web` sends `POST /api/reconstruct` (multipart image + optional params).
3. `api` validates, enqueues a job (single worker), returns a `job_id`.
4. Worker calls `core.pipeline.reconstruct`:
   a. Preprocess: validate, resize, remove background (rembg), crop foreground.
   b. TripoSR inference → implicit 3D representation.
   c. Mesh extraction: marching cubes via PyMCubes; sample vertex colors.
   d. Export: `trimesh` writes `.glb` and `.obj` to the job output dir.
5. `web` polls `GET /api/jobs/{id}` until `done` (or `error`).
6. On success, `web` loads the `.glb` into Google `<model-viewer>` for a
   rotatable preview and shows `.glb`/`.obj` download buttons.

## 6. Error Handling

| Condition | Behaviour |
|---|---|
| Invalid / corrupt / unsupported image | `400` with a clear message; no job created. |
| No foreground found after bg removal | Job ends `error` with actionable message ("no clear object detected; try an image with a single object on a plain background"). |
| First-run weight download | `health`/status surfaces a "downloading model" state; web shows an informative message. |
| Inference out-of-memory / too slow | Job ends `error` suggesting a lower resolution; single-worker queue prevents concurrent OOM. |
| Concurrent uploads | Jobs queue (FIFO, one worker); each gets its own status. |
| Unexpected exception in core | Caught at the worker boundary; job marked `error` with a sanitized message; full traceback logged server-side. |

## 7. Testing Strategy

- **core unit tests** (fast, model mocked where heavy):
  - `preprocessing`: resize bounds, rejects corrupt input, background removal
    output shape, foreground crop logic.
  - `mesh`: marching-cubes wrapper produces a watertight-ish mesh from a known
    synthetic volume; `.glb`/`.obj` export round-trips loadable by `trimesh`.
  - `pipeline`: orchestration with a stubbed model returns a well-formed
    `ReconstructionResult`.
- **api tests** (FastAPI `TestClient`, core mocked):
  - Validation and error paths for `/api/reconstruct`.
  - Job lifecycle: create → poll `running` → `done`/`error`.
  - `/api/health`.
- **End-to-end (slow, opt-in, `-m slow`):** real TripoSR on a small bundled
  sample image; asserts non-empty mesh and valid exported files.
- CI-friendly: default `pytest` run excludes `slow`; setup is reproducible.

## 8. Project Layout & Tooling

```
fun_project_2D_to_3D/
  README.md             Setup, usage, troubleshooting.
  pyproject.toml        Deps, pinned, project metadata.
  .gitignore            venv, model cache, outputs, __pycache__.
  src/image_to_3d/      (see Architecture)
  tests/                Mirrors src; fixtures/sample.jpg.
  scripts/
    setup_env.py        Verified, reproducible environment bootstrap.
    download_weights.py  Pre-fetch model weights (optional convenience).
```

Key dependencies: `torch` (CPU build), `torchvision`, `transformers`, `einops`,
`omegaconf`, `Pillow`, `numpy`, `rembg` (+ `onnxruntime`), `PyMCubes`,
`trimesh`, `fastapi`, `uvicorn`, `python-multipart`, `pytest`.

## 9. Known Setup Risk & Mitigation

The system Python is **3.13**; some dependencies historically lack Windows /
3.13 prebuilt wheels (notably native marching-cubes builds).

Mitigations baked into the design:

- Use **PyMCubes** instead of `torchmcubes` (broad wheel availability,
  no Torch-CUDA coupling).
- `scripts/setup_env.py` creates an **isolated virtual environment pinned to a
  tested Python (3.10–3.12)**, verifies every dependency imports, and fails
  loudly with guidance if a wheel is unavailable.
- README documents the exact tested Python version and a fallback path.

## 10. Success Criteria

- A user can run one setup command, start the app, open the browser, drop an
  object photo, and within a few minutes download a `.glb` that opens correctly
  in Blender / any glTF viewer and visibly resembles the input object.
- No paid service or API key is ever required.
- `core` can be imported and used without `api` or `web`.
- Test suite (excluding `slow`) passes on the target machine.
