"""ML dependency installation API — auto-detects GPU and installs correct PyTorch."""
import subprocess
import sys
import threading
import importlib.util
import platform
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_install_status = {
    "running": False,
    "progress": "",
    "error": None,
}

# ── PyTorch index URLs ──────────────────────────────────────────────────────
PYTORCH_INDEX_URLS = {
    "nvidia": "https://download.pytorch.org/whl/cu124",
    "rocm_gfx110X": "https://d2awnip2yjpvqn.cloudfront.net/v2/gfx110X-dgpu/",
    "rocm_gfx120X": "https://d2awnip2yjpvqn.cloudfront.net/v2/gfx120X-all/",
}

# AMD GPU name → ROCm arch
AMD_GPU_ARCH_MAP = {
    "7900 XTX": "gfx110X", "7900 XT": "gfx110X", "7900 GRE": "gfx110X",
    "7800 XT": "gfx110X", "7700 XT": "gfx110X", "7600 XT": "gfx110X", "7600": "gfx110X",
    "9070 XT": "gfx120X", "9070": "gfx120X", "9060 XT": "gfx120X",
}


def _check_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _detect_gpu() -> dict:
    """Detect GPU vendor and return install info.

    Returns:
        {
            "vendor": "nvidia" | "amd" | "intel" | "cpu",
            "name": "Radeon RX 7900 XTX",
            "pytorch_index": "https://...",  # None for CPU
            "label": "AMD ROCm (gfx110X)",
        }
    """
    result = {"vendor": "cpu", "name": "CPU", "pytorch_index": None, "label": "CPU"}

    if platform.system() != "Windows":
        # Linux: check for NVIDIA via nvidia-smi
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                result = {
                    "vendor": "nvidia",
                    "name": r.stdout.strip().split("\n")[0],
                    "pytorch_index": PYTORCH_INDEX_URLS["nvidia"],
                    "label": "NVIDIA CUDA",
                }
                return result
        except Exception:
            pass
        # Linux AMD check would need ROCm tools, skip for now
        return result

    # Windows: query all GPUs via PowerShell
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return result

        gpu_lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]

        # Check NVIDIA first (CUDA is most compatible)
        for line in gpu_lines:
            if "NVIDIA" in line.upper():
                result = {
                    "vendor": "nvidia",
                    "name": line,
                    "pytorch_index": PYTORCH_INDEX_URLS["nvidia"],
                    "label": "NVIDIA CUDA",
                }
                return result

        # Check AMD
        for line in gpu_lines:
            if "RADEON" in line.upper() or "AMD" in line.upper():
                # Determine ROCm architecture
                arch = None
                for pattern, a in AMD_GPU_ARCH_MAP.items():
                    if pattern in line:
                        arch = a
                        break
                if arch:
                    index_key = f"rocm_{arch}"
                    result = {
                        "vendor": "amd",
                        "name": line,
                        "pytorch_index": PYTORCH_INDEX_URLS.get(index_key),
                        "label": f"AMD ROCm ({arch})",
                        "arch": arch,
                    }
                else:
                    result = {
                        "vendor": "amd",
                        "name": line,
                        "pytorch_index": None,
                        "label": "AMD (unsupported model)",
                    }
                return result

        # Check Intel
        for line in gpu_lines:
            if "INTEL" in line.upper() and ("ARC" in line.upper() or "IRIS" in line.upper()):
                result = {
                    "vendor": "intel",
                    "name": line,
                    "pytorch_index": None,  # Intel XPU needs special handling
                    "label": "Intel (CPU fallback)",
                }
                return result

    except Exception:
        pass

    return result


def _check_torch_backend() -> dict:
    """Check installed torch version and backend."""
    info = {"installed": False, "version": None, "backend": "none", "gpu_upgradeable": False}

    if not _check_module("torch"):
        return info

    info["installed"] = True
    try:
        import importlib.metadata
        ver = importlib.metadata.version("torch")
        info["version"] = ver
        if "+cpu" in ver:
            info["backend"] = "cpu"
        elif "+rocm" in ver:
            info["backend"] = "rocm"
        elif "+cu" in ver:
            info["backend"] = "cuda"
        else:
            info["backend"] = "unknown"
    except Exception:
        info["backend"] = "unknown"

    # Check if a GPU is available but torch is CPU-only
    gpu = _detect_gpu()
    if gpu["vendor"] != "cpu" and info["backend"] == "cpu" and gpu["pytorch_index"]:
        info["gpu_upgradeable"] = True
        info["gpu_vendor"] = gpu["vendor"]
        info["gpu_name"] = gpu["name"]

    return info


@router.get("/ml/status")
def ml_status():
    """Check ML deps and GPU info."""
    deps = {}
    for mod in ("torch", "torchaudio", "demucs", "soundfile", "numpy"):
        deps[mod] = _check_module(mod)

    torch_info = _check_torch_backend()
    gpu = _detect_gpu()

    return {
        "installed": all(deps.values()),
        "deps": deps,
        "installing": _install_status["running"],
        "progress": _install_status["progress"],
        "error": _install_status["error"],
        "torch": torch_info,
        "gpu": gpu,
        "gpu_upgradeable": torch_info.get("gpu_upgradeable", False),
    }


@router.post("/ml/install")
def install_ml():
    """Install ML deps — auto-detects GPU and installs correct PyTorch."""
    if _install_status["running"]:
        return {"status": "already_running", "progress": _install_status["progress"]}

    def _install():
        _install_status["running"] = True
        _install_status["error"] = None
        _install_status["progress"] = "检测 GPU..."

        try:
            gpu = _detect_gpu()
            req_file = Path(__file__).parent.parent.parent / "requirements-ml.txt"
            if not req_file.exists():
                _install_status["error"] = "requirements-ml.txt not found"
                _install_status["running"] = False
                return

            index_url = gpu.get("pytorch_index")

            if index_url:
                # GPU detected: uninstall old torch, install GPU version
                _install_status["progress"] = f"检测到 {gpu['label']}，卸载旧版 PyTorch..."
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y",
                     "torch", "torchaudio", "torchvision"],
                    capture_output=True, text=True, timeout=300,
                )

                _install_status["progress"] = f"安装 {gpu['label']} 版 PyTorch..."
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet",
                     "--no-warn-script-location",
                     "--index-url", index_url,
                     "torch", "torchaudio"],
                    capture_output=True, text=True, timeout=1800,
                )
                if proc.returncode != 0:
                    _install_status["error"] = (
                        f"{gpu['label']} PyTorch 安装失败: "
                        f"{proc.stderr[-300:] if proc.stderr else 'Unknown error'}"
                    )
                    _install_status["running"] = False
                    return

                # Install remaining deps from PyPI (skip torch)
                _install_status["progress"] = "安装其他 ML 依赖..."
                with open(req_file) as f:
                    lines = f.readlines()
                other_deps = [
                    l.strip() for l in lines
                    if l.strip() and not l.startswith("#")
                    and not l.startswith("torch")
                    and not l.startswith("torchaudio")
                ]
                if other_deps:
                    proc = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--quiet",
                         "--no-warn-script-location"] + other_deps,
                        capture_output=True, text=True, timeout=1800,
                    )
                    if proc.returncode != 0:
                        _install_status["error"] = (
                            f"部分依赖安装失败: {proc.stderr[-300:] if proc.stderr else ''}"
                        )
                        _install_status["running"] = False
                        return

                _install_status["progress"] = f"Done! {gpu['label']} PyTorch 已安装，请重启应用"
            else:
                # CPU-only: install everything from PyPI
                _install_status["progress"] = "安装 ML 依赖 (CPU)..."
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet",
                     "--no-warn-script-location", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=1800,
                )
                if proc.returncode != 0:
                    _install_status["error"] = (
                        proc.stderr[-500:] if proc.stderr else "Unknown error"
                    )
                    _install_status["running"] = False
                    return
                _install_status["progress"] = "Done! CPU 版已安装，请重启应用"

        except subprocess.TimeoutExpired:
            _install_status["error"] = "安装超时 (30 min)"
        except Exception as e:
            _install_status["error"] = str(e)
        finally:
            _install_status["running"] = False

    threading.Thread(target=_install, daemon=True).start()
    return {"status": "started"}
