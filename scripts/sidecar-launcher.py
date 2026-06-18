#!/usr/bin/env python3
"""Sidecar launcher for AI Voice Cover backend.

Bundled with the Tauri app. Finds/installs dependencies and starts FastAPI.
Works with both embedded Python (bundled) and system Python.
"""
import os
import sys
import subprocess
import logging
import traceback
import importlib.util
from pathlib import Path

# ── Writable data directory ──────────────────────────────────────────────────
# sidecar files may be in a read-only location (e.g. /usr/lib/ on Linux)
# so we put logs, pip cache, and data in a user-writable directory.
if sys.platform == "win32":
    _data_dir = Path(os.environ.get("APPDATA", Path.home())) / "AI Voice Cover"
elif sys.platform == "darwin":
    _data_dir = Path.home() / "Library" / "Application Support" / "AI Voice Cover"
else:
    _data_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ai-voice-cover"

_data_dir.mkdir(parents=True, exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = str(_data_dir / "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "sidecar.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("sidecar")
logger.info("Log file: %s", log_file)
logger.info("Data dir: %s", _data_dir)


# ── Helpers ──────────────────────────────────────────────────────────────────
def is_embedded_python() -> bool:
    """Check if running from Python embeddable package (Windows)."""
    return hasattr(sys, "_base_executable") and "python" in os.path.basename(
        sys._base_executable
    ).lower() and os.path.exists(os.path.join(os.path.dirname(sys.executable), "python311._pth"))


def setup_pip(python: str) -> bool:
    """Bootstrap pip for embedded Python. Returns True if pip is available."""
    try:
        subprocess.check_call(
            [python, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    logger.info("pip not found, bootstrapping with ensurepip...")
    try:
        subprocess.check_call([python, "-m", "ensurepip", "--upgrade"])
        logger.info("pip bootstrapped successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("ensurepip failed (exit %s): %s", e.returncode, e)
        # Fallback: try get-pip.py
        logger.info("Trying get-pip.py fallback...")
        try:
            import urllib.request
            get_pip = str(_data_dir / "get-pip.py")
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)
            subprocess.check_call([python, get_pip, "--no-warn-script-location"])
            logger.info("pip installed via get-pip.py")
            return True
        except Exception as e2:
            logger.error("get-pip.py also failed: %s", e2)
            return False


def install_deps(python: str) -> bool:
    """Install core dependencies from requirements.txt."""
    req_file = os.path.join(base_dir, "requirements.txt")
    if not os.path.exists(req_file):
        logger.warning("requirements.txt not found at %s, skipping install", req_file)
        return True

    logger.info("Installing dependencies from %s ...", req_file)
    try:
        result = subprocess.run(
            [python, "-m", "pip", "install", "--quiet", "--no-warn-script-location",
             "--cache-dir", str(_data_dir / "pip-cache"),
             "-r", req_file],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logger.error("pip install failed (exit %s):\nstdout: %s\nstderr: %s",
                        result.returncode, result.stdout[-500:], result.stderr[-500:])
            return False
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install dependencies: %s", e)
        return False


def check_core_deps() -> bool:
    """Check if core dependencies are importable."""
    for mod in ("fastapi", "uvicorn"):
        if importlib.util.find_spec(mod) is None:
            return False
    return True


def find_free_port() -> int:
    """Find an available port on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    try:
        _main()
    except Exception:
        logger.error("Fatal error:\n%s", traceback.format_exc())
        raise


def _main():
    # Ensure sidecar dir is on sys.path so `backend` is importable
    # (embedded Python's ._pth file only includes its own directory)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    os.chdir(base_dir)
    logger.info("Python: %s (%s)", sys.executable, sys.version)
    logger.info("Embedded: %s", is_embedded_python())
    logger.info("Base dir: %s", base_dir)
    logger.info("sys.path[0]: %s", sys.path[0])

    python = sys.executable

    # Ensure pip is available (needed for embedded Python)
    if not setup_pip(python):
        logger.error("Cannot proceed without pip")
        sys.exit(1)

    # Install core dependencies if missing
    if not check_core_deps():
        if not install_deps(python):
            logger.error("Cannot proceed without core dependencies")
            sys.exit(1)
    else:
        logger.info("Core dependencies already installed")

    # ── Start backend ────────────────────────────────────────────────────────
    port = int(os.environ.get("AVC_PORT", 0)) or find_free_port()
    host = "127.0.0.1"

    os.environ["AVC_PORT"] = str(port)
    os.environ["AVC_HOST"] = host

    # Optional: check ML deps
    try:
        import torch
        logger.info("PyTorch %s (device: %s)", torch.__version__,
                     torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    except ImportError:
        logger.warning("PyTorch not installed — ML features unavailable")

    try:
        import edge_tts
        logger.info("edge-tts available")
    except ImportError:
        logger.warning("edge-tts not installed — TTS unavailable")

    logger.info("Starting backend on %s:%s", host, port)

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
