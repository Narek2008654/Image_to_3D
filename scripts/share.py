"""Path A: expose the local app to the internet via a free Cloudflare tunnel.

No Cloudflare account, no cost, HTTPS, reachable from any network (e.g. a
phone on mobile data). The public URL is printed prominently and changes each
run (Cloudflare Quick Tunnel is ephemeral).

Usage:
    python scripts/share.py
Stop with Ctrl+C.
"""

from __future__ import annotations

import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "scripts" / "bin"
PORT = 8000
HEALTH_URL = f"http://localhost:{PORT}/api/health"
LOCAL_URL = f"http://localhost:{PORT}"

_CF_RELEASE = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
)
_TRYCF_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _cloudflared_asset() -> str:
    if platform.system() == "Windows":
        return "cloudflared-windows-amd64.exe"
    arch = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "amd64"
    return f"cloudflared-{platform.system().lower()}-{arch}"


def _ensure_cloudflared() -> Path:
    """Return a usable cloudflared path, downloading it once if missing."""
    exe = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"
    local = BIN_DIR / exe
    if local.is_file():
        return local

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    url = _CF_RELEASE + _cloudflared_asset()
    print(f"Downloading cloudflared (one time) from {url}")
    try:
        urllib.request.urlretrieve(url, local)  # noqa: S310 - official release
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(
            f"Could not download cloudflared automatically ({exc}).\n"
            f"Download it manually from:\n  {url}\n"
            f"and save it as:\n  {local}"
        )
    if platform.system() != "Windows":
        local.chmod(0o755)
    return local


def _server_is_up() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


def _venv_python() -> str:
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    nix = ROOT / ".venv" / "bin" / "python"
    if win.is_file():
        return str(win)
    if nix.is_file():
        return str(nix)
    return sys.executable


def _start_server() -> subprocess.Popen:
    print("Starting the app server on :%d ..." % PORT)
    proc = subprocess.Popen(
        [
            _venv_python(),
            "-m",
            "uvicorn",
            "image_to_3d.api.main:app",
            "--port",
            str(PORT),
        ],
        cwd=str(ROOT),
    )
    for _ in range(60):  # wait up to ~60s for it to come up
        if _server_is_up():
            return proc
        if proc.poll() is not None:
            raise SystemExit("The app server exited before it became ready.")
        time.sleep(1)
    proc.terminate()
    raise SystemExit("The app server did not become ready in time.")


def _banner(url: str) -> None:
    line = "=" * (len(url) + 16)
    print(f"\n{line}\n  PUBLIC URL:  {url}\n{line}")
    print("Open that URL on your phone (works on mobile data).")
    print("Keep this window open. Press Ctrl+C to stop.\n")


def main() -> int:
    cloudflared = _ensure_cloudflared()

    server: subprocess.Popen | None = None
    if _server_is_up():
        print(f"Reusing the app already running at {LOCAL_URL}")
    else:
        server = _start_server()

    tunnel = subprocess.Popen(
        [str(cloudflared), "tunnel", "--url", LOCAL_URL],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        announced = False
        assert tunnel.stdout is not None
        for raw in tunnel.stdout:
            line = raw.rstrip()
            print(line)
            if not announced:
                match = _TRYCF_RE.search(line)
                if match:
                    _banner(match.group(0))
                    announced = True
        return tunnel.wait()
    except KeyboardInterrupt:
        print("\nShutting down ...")
        return 0
    finally:
        tunnel.terminate()
        if server is not None:
            server.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
