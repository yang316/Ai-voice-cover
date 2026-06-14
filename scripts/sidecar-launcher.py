#!/usr/bin/env python3
"""Sidecar launcher for AI Voice Cover backend.

This script is bundled with the Tauri app and starts the FastAPI server.
"""
import os
import sys
import signal
import subprocess
import socket
import time

# Find a free port
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def main():
    port = find_free_port()
    # Write port to a file so the frontend can read it
    port_file = os.path.join(os.path.dirname(__file__), ".port")
    with open(port_file, "w") as f:
        f.write(str(port))

    # Set environment
    os.environ["AVC_PORT"] = str(port)
    os.environ["AVC_HOST"] = "127.0.0.1"

    # Get the base directory (where backend/ and frontend/ live)
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.chdir(base_dir)

    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
    ]

    proc = subprocess.Popen(cmd)

    def cleanup(sig, frame):
        proc.terminate()
        proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Print port to stdout for Tauri to read
    print(f"PORT={port}", flush=True)

    proc.wait()

if __name__ == "__main__":
    main()
