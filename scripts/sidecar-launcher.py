#!/usr/bin/env python3
"""Sidecar launcher for AI Voice Cover backend.

This script is bundled with the Tauri app and starts the FastAPI server.
"""
import os
import sys
import signal


def find_free_port():
    """Find an available port on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
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

    # Print port so Tauri / logs can see it
    print(f"Starting AI Voice Cover backend on {host}:{port}", flush=True)

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
