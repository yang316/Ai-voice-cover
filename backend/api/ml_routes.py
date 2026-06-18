"""ML dependency installation API."""
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

# Track installation status
_install_status = {
    "running": False,
    "progress": "",
    "error": None,
}


@router.get("/ml/status")
def ml_status():
    """Check if ML dependencies are installed."""
    deps = {}
    for mod in ("torch", "torchaudio", "demucs", "soundfile", "numpy"):
        try:
            __import__(mod)
            deps[mod] = True
        except ImportError:
            deps[mod] = False

    all_installed = all(deps.values())
    return {
        "installed": all_installed,
        "deps": deps,
        "installing": _install_status["running"],
        "progress": _install_status["progress"],
        "error": _install_status["error"],
    }


@router.post("/ml/install")
def install_ml():
    """Install ML dependencies in background."""
    if _install_status["running"]:
        return {"status": "already_running", "progress": _install_status["progress"]}

    def _install():
        _install_status["running"] = True
        _install_status["error"] = None
        _install_status["progress"] = "Installing PyTorch..."

        req_file = Path(__file__).parent.parent.parent / "requirements-ml.txt"
        if not req_file.exists():
            _install_status["error"] = "requirements-ml.txt not found"
            _install_status["running"] = False
            return

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--no-warn-script-location", "-r", str(req_file)],
                capture_output=True, text=True, timeout=1800,
            )
            if proc.returncode != 0:
                _install_status["error"] = proc.stderr[-500:] if proc.stderr else "Unknown error"
            else:
                _install_status["progress"] = "Done!"
        except subprocess.TimeoutExpired:
            _install_status["error"] = "Installation timed out (30 min)"
        except Exception as e:
            _install_status["error"] = str(e)
        finally:
            _install_status["running"] = False

    threading.Thread(target=_install, daemon=True).start()
    return {"status": "started"}
