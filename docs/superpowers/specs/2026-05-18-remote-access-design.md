# Remote Access — Design Spec

**Date:** 2026-05-18
**Status:** Approved (pending spec review)
**Builds on:** `2026-05-17-image-to-3d-design.md`

## 1. Goal & Scope

Let the user use the existing image-to-3D app **from a phone, off the home
Wi-Fi, for $0**, without losing the project's "unlimited / no caps / no API
keys" property.

No single free option is simultaneously *unlimited + fast + always-on +
laptop-off*. The user accepted **two complementary free paths**:

- **Path A — Cloudflare Quick Tunnel (laptop on):** full speed, truly
  unlimited, reachable from any network; laptop must be awake.
- **Path B — Hugging Face free Docker Space (laptop off):** available without
  the laptop; slower, cold-starts after ~48 h idle; still $0, no usage caps,
  no credit card.

Both serve the **existing FastAPI + `web/` app unchanged** — the
"thin client + backend" design from the base spec, deployed two ways.

**Out of scope:** a stable custom domain/URL (needs a paid-or-owned domain);
authentication (Space is public by user choice); any paid tier.

## 2. Constraints

- Zero cost, no credit card, no usage meter on either path.
- No new runtime dependencies; `core/api/web` logic unchanged except one
  config touch.
- Reuse the dependency versions already proven to install on cp312
  (`scripts/setup_env.py`).

## 3. Architecture

One config seam plus two thin deployment wrappers around the existing app:

```
core/config.py     output_dir <- env IMAGE_TO_3D_OUTPUT_DIR (else "outputs")
Dockerfile         Path B: build image, run uvicorn :7860      (HF Space)
README.md          HF Space YAML header + Remote-access docs
scripts/share.py   Path A: cloudflared quick tunnel -> public HTTPS URL
.dockerignore      keep build context small
tests/test_config.py  env-set and env-unset behaviour
```

The ASGI app `image_to_3d.api.main:app` is identical in local, tunnel, and
Space use. Path A exposes port 8000; Path B exposes 7860 (HF requirement).

## 4. The One Code Change

`core/config.py` `_default_output_dir()` becomes:

```python
Path(os.environ.get("IMAGE_TO_3D_OUTPUT_DIR", "outputs")).resolve()
```

Rationale: HF Spaces run as a non-root user where only `/tmp` and the app dir
are writable; the container sets `IMAGE_TO_3D_OUTPUT_DIR=/tmp/outputs`. When
the variable is unset (all local/tunnel use) behaviour is byte-for-byte
unchanged. `ReconstructionOptions` already consumes this via
`field(default_factory=_default_output_dir)`, so `api`/`web` need no change.

## 5. Path A — Cloudflare Quick Tunnel

`scripts/share.py` (stdlib + subprocess only):

1. Locate `cloudflared`; if missing, download the official Windows binary to
   `scripts/bin/cloudflared.exe`. On download failure: exit with a clear
   message and the manual download URL (no half-working state).
2. Probe `http://localhost:8000/api/health`; start `uvicorn` only if nothing
   is already serving there.
3. Run `cloudflared tunnel --url http://localhost:8000`, parse stdout for the
   `https://*.trycloudflare.com` URL, and print it prominently.

Free, no Cloudflare account, HTTPS, any network. The URL is **ephemeral**
(changes per run) — documented, accepted.

## 6. Path B — Hugging Face Docker Space

- **`Dockerfile`** (`python:3.12-slim`): install the exact pinned deps from
  `scripts/setup_env.py` (`TORCH_PKGS` via the CPU index, then `PYPI_PKGS`),
  copy the repo, `RUN python scripts/fetch_triposr.py` (vendors + patches
  TripoSR into the image), `pip install -e .`, set
  `IMAGE_TO_3D_OUTPUT_DIR=/tmp/outputs`, `EXPOSE 7860`,
  `CMD uvicorn image_to_3d.api.main:app --host 0.0.0.0 --port 7860`.
- **`README.md`**: prepend HF front-matter (`title`, `emoji`, `colorFrom`,
  `colorTo`, `sdk: docker`, `app_port: 7860`, `pinned: false`). Valid on
  GitHub. Add a "Remote access" section: Path A command, Path B push steps,
  and an honest cold-start note.
- **Deploy:** create a public HF Docker Space, add it as git remote `hf`,
  push. GitHub remains source of truth. Requires the user's HF credentials at
  deploy time (manual step).

Honest free-tier behaviour, documented as expected (not bugs): sleeps after
~48 h idle; ephemeral storage re-downloads the ~2 GB weights on cold start;
shared CPU ≈ laptop speed.

## 6a. `.dockerignore`

Exclude `.venv/`, `outputs/`, `__pycache__/`, `*.egg-info/`, `setup_log.txt`,
`e2e_log.txt`, `.git/`, `.pytest_cache/` so the build context stays small and
the image deterministic.

## 7. Error Handling

| Condition | Behaviour |
|---|---|
| `cloudflared` missing | Auto-download; on failure, exit with manual URL. |
| Server already on :8000 | Reuse it; don't start a second uvicorn. |
| HF Docker build failure | Pinned, pre-verified versions minimize this; README points to HF build logs. |
| HF cold start | First request slow (container + weight download). Documented. |
| Output dir not writable | Container sets `/tmp/outputs`; config seam handles it. |

## 8. Testing

- **`tests/test_config.py`** (fast suite): with `IMAGE_TO_3D_OUTPUT_DIR` set →
  `ReconstructionOptions().output_dir` resolves to it; unset → ends with
  `outputs`. `monkeypatch.setenv`/`delenv`.
- Existing fast suite must stay green (no behaviour change when env unset).
- Dockerfile/tunnel are integration concerns — verified manually
  (local `docker build`/`run`; phone over mobile data; Space with laptop off).

## 9. Success Criteria

- `pytest -m 'not slow'` passes including the new config test.
- Path A: a `trycloudflare.com` URL opens the working app on the phone over
  **mobile data** with the laptop running it.
- Path B: the public HF Space URL opens the working app on the phone with the
  **laptop off**.
- Neither path needs an API key; neither has a usage cap; both are $0.
