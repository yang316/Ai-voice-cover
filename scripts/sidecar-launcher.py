#!/usr/bin/env python3
"""Sidecar launcher for AI Voice Cover backend.

This script is bundled with the Tauri app and starts the FastAPI server.
"""
import os
import sys
import logging
import traceback

# Setup logging — both console (for Tauri to capture) and file (for debugging)
log_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "logs")
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


def find_free_port():
    """Find an available port on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    try:
        _main()
    except Exception:
        logger.error("Fatal error:\n%s", traceback.format_exc())
        raise


def _main():
    # Read port from Rust (Tauri passes AVC_PORT env var), or find one
    port = int(os.environ.get("AVC_PORT", 0)) or find_free_port()
    host = "127.0.0.1"

    # Ensure env vars are set for the backend
    os.environ["AVC_PORT"] = str(port)
    os.environ["AVC_HOST"] = host

    # Get the base directory (where backend/ and frontend/ live)
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — data files are next to the executable
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.chdir(base_dir)
    logger.info("Executable: %s", sys.executable)
    logger.info("Base directory: %s", base_dir)
    logger.info("Frozen: %s", getattr(sys, "frozen", False))
    if getattr(sys, "frozen", False):
        logger.info("MEIPASS: %s", getattr(sys, "_MEIPASS", "N/A"))
    logger.info("sys.path: %s", sys.path[:5])

    # Check what's available
    try:
        import torch
        logger.info("PyTorch %s available (device: %s)", torch.__version__, torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    except ImportError:
        logger.warning("PyTorch not installed — ML features (cover, training) will be unavailable")

    try:
        import edge_tts
        logger.info("edge-tts available")
    except ImportError:
        logger.warning("edge-tts not installed — TTS will be unavailable")

    # Print port so Tauri / logs can see it
    logger.info("Starting AI Voice Cover backend on %s:%s", host, port)

    # Start uvicorn in-process (works correctly inside PyInstaller bundles)
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
