---
title: Image To 3D
emoji: 🧊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Image → 3D

Turn **one 2D photo of an object** into a **rotatable, downloadable 3D model**.
Runs entirely on your own machine — **free, unlimited, no API keys, no cloud**.

Powered by [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT) running
on CPU, with the unbuildable `torchmcubes` dependency swapped for
[PyMCubes](https://github.com/pmneila/PyMCubes).

## What it does

Upload an image of a **single object** (toy, product, character, furniture) →
get back a 3D mesh as `.glb`, `.obj`, and `.stl`, with a live in-browser
rotatable preview.

It does **not** reconstruct full scenes or landscapes — that is out of scope
for current free single-image models.

## Requirements

- **Python 3.10–3.12** (the setup script finds one automatically; Python 3.13
  is unsupported because some dependencies have no 3.13 wheels).
- ~6 GB free RAM and ~3 GB disk for model weights (downloaded once).
- No GPU required (CPU-only by design).

## Setup

One command creates an isolated `.venv`, installs CPU-only dependencies,
vendors + patches TripoSR, and verifies every import:

```sh
python scripts/setup_env.py
```

## Run

```sh
.venv\Scripts\python -m uvicorn image_to_3d.api.main:app
```

Open <http://localhost:8000>, drop in a photo, and download the result.
First reconstruction downloads the model weights (~2 GB, one time); after that
it works fully offline. Expect **~30 s – 2 min per image** on a laptop CPU.

## Remote access (use it from your phone, free)

Two free paths — no cost, no API keys, no usage caps.

### Path A — your laptop, reachable anywhere (fast)

Your laptop runs it; a free Cloudflare tunnel exposes it over HTTPS so any
device on any network can reach it.

```sh
.venv\Scripts\python scripts\share.py
```

It prints a public `https://<random>.trycloudflare.com` URL. Open that on your
phone (works on mobile data). Full speed, truly unlimited. The laptop must
stay awake and online; the URL changes each run (Cloudflare Quick Tunnel is
ephemeral — a stable URL would need an owned domain).

### Path B — Hugging Face Space (works with the laptop off)

This repo is also a Hugging Face **Docker Space** (see the header at the top of
this file and the `Dockerfile`). Push it to a public HF Space and it runs in
the cloud for free:

```sh
git remote add hf https://huggingface.co/spaces/<your-username>/image-to-3d
git push hf master
```

Then open the Space URL on any device, anytime — no laptop needed.

Honest free-tier behaviour (expected, not bugs): the Space **sleeps after
~48 h idle** and takes ~1–2 min to wake; storage is ephemeral so the ~2 GB
model re-downloads on the first request after a cold start; the shared CPU is
roughly laptop-speed. Still $0, with no usage caps.

## Architecture

Three independent layers (`core` has no web knowledge; the future phone app is
a sibling of `web`, reusing the same API unchanged):

```
src/
  tsr/                 Vendored TripoSR, isosurface patched to PyMCubes
  image_to_3d/
    core/              image -> mesh (pure Python)
      config.py preprocessing.py model.py mesh.py pipeline.py
    api/               FastAPI: POST /api/reconstruct, GET /api/jobs/{id},
                       GET /api/health  (single-worker job queue)
    web/               Static UI with <model-viewer> preview
scripts/
  setup_env.py         Reproducible bootstrap
  fetch_triposr.py     Vendor + patch TripoSR
patches/
  isosurface_pymcubes.py   The torchmcubes -> PyMCubes replacement
```

The single public entry point is `image_to_3d.core.reconstruct(image, options)`.

## Tests

```sh
.venv\Scripts\python -m pytest            # fast suite (model mocked)
.venv\Scripts\python -m pytest -m slow    # real TripoSR end-to-end
```

## Tuning quality vs. speed

`mc_resolution` (marching-cubes grid) trades detail for CPU time — exposed in
the web UI as Fast / Balanced / High (128 / 192 / 256).

## Future: phone app

The architecture targets a **thin client + self-hosted backend**: a future
phone app uploads to a backend you run (this app, on your PC or any host you
control). The phone never runs the heavy model, so it works on any device and
stays free and unlimited. No backend changes are needed — the phone app is just
another frontend to the existing API.

## License

MIT. TripoSR code and weights are also MIT (commercial use permitted).
