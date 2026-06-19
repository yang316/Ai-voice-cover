"""ML dependency installation API."""
import subprocess
import sys
import threading
import importlib.util
import platform
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

# Track installation status
_install_status = {
    "running": False,
    "progress": "",
    "error": None,
}

# ROCm index URLs for AMD GPUs (RDNA 3 / RDNA 4)
ROCM_INDEX_URLS = {
    "gfx110X": "https://d2awnip2yjpvqn.cloudfront.net/v2/gfx110X-dgpu/",
    "gfx120X": "https://d2awnip2yjpvqn.cloudfront.net/v2/gfx120X-all/",
}

# GPU architecture mapping (PCI device name → index key)
AMD_GPU_ARCH_MAP = {
    "7900 XTX": "gfx110X",
    "7900 XT": "gfx110X",
    "7900 GRE": "gfx110X",
    "7800 XT": "gfx110X",
    "7700 XT": "gfx110X",
    "7600": "gfx110X",
    "9070 XT": "gfx120X",
    "9070": "gfx120X",
    "9060 XT": "gfx120X",
}


def _check_module(name: str) -> bool:
    """Check if a module is installed without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _detect_amd_gpu() -> str | None:
    """Detect AMD GPU and return architecture key, or None."""
    if platform.system() != "Windows":
        return None
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            gpu_name = result.stdout.strip()
            for pattern, arch in AMD_GPU_ARCH_MAP.items():
                if pattern in gpu_name:
                    return arch
    except Exception:
        pass
    return None


def _check_torch_backend() -> dict:
    """Check installed torch version and backend support."""
    info = {"installed": False, "version": None, "backend": "none", "gpu_upgradeable": False}

    if not _check_module("torch"):
        return info

    info["installed"] = True
    try:
        # Use importlib to get version without full import
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

    # Check if GPU upgrade is available
    arch = _detect_amd_gpu()
    if arch:
        info["gpu_vendor"] = "AMD"
        info["gpu_arch"] = arch
        if info["backend"] == "cpu":
            info["gpu_upgradeable"] = True
            info["upgrade_index"] = ROCM_INDEX_URLS.get(arch)
    else:
        # Check for NVIDIA GPU
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and "NVIDIA" in result.stdout.upper():
                info["gpu_vendor"] = "NVIDIA"
                if info["backend"] == "cpu":
                    info["gpu_upgradeable"] = True
        except Exception:
            pass

    return info


@router.get("/ml/status")
def ml_status():
    """Check if ML dependencies are installed."""
    deps = {}
    for mod in ("torch", "torchaudio", "demucs", "soundfile", "numpy"):
        deps[mod] = _check_module(mod)

    all_installed = all(deps.values())
    torch_info = _check_torch_backend()

    return {
        "installed": all_installed,
        "deps": deps,
        "installing": _install_status["running"],
        "progress": _install_status["progress"],
        "error": _install_status["error"],
        "torch": torch_info,
        "gpu_upgradeable": torch_info.get("gpu_upgradeable", False),
    }


@router.post("/ml/install")
def install_ml():
    """Install ML dependencies in background."""
    if _install_status["running"]:
        return {"status": "already_running", "progress": _install_status["progress"]}

    def _install():
        _install_status["running"] = True
        _install_status["error"] = None
        _install_status["progress"] = "检测 GPU..."

        try:
            # Step 1: Detect AMD GPU
            arch = _detect_amd_gpu()
            req_file = Path(__file__).parent.parent.parent / "requirements-ml.txt"
            if not req_file.exists():
                _install_status["error"] = "requirements-ml.txt not found"
                _install_status["running"] = False
                return

            if arch and arch in ROCM_INDEX_URLS:
                # AMD GPU: uninstall CPU torch first, then install ROCm version
                _install_status["progress"] = f"检测到 AMD GPU ({arch})，准备安装 ROCm PyTorch..."
                index_url = ROCM_INDEX_URLS[arch]

                # Step 1: Uninstall existing torch first (CPU/other version)
                _install_status["progress"] = "卸载旧版 PyTorch..."
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y",
                     "torch", "torchaudio", "torchvision"],
                    capture_output=True, text=True, timeout=300,
                )

                # Step 2: Install ROCm PyTorch
                _install_status["progress"] = f"安装 ROCm PyTorch ({arch})..."
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet",
                     "--no-warn-script-location",
                     "--index-url", index_url,
                     "torch", "torchaudio"],
                    capture_output=True, text=True, timeout=1800,
                )
                if proc.returncode != 0:
                    _install_status["error"] = (
                        f"ROCm PyTorch 安装失败: {proc.stderr[-300:] if proc.stderr else 'Unknown error'}"
                    )
                    _install_status["running"] = False
                    return

                # Step 2: Install remaining ML deps from PyPI (skip torch)
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
                            f"部分依赖安装失败: {proc.stderr[-300:] if proc.stderr else 'Unknown error'}"
                        )
                        _install_status["running"] = False
                        return
            else:
                # NVIDIA / CPU: install everything from PyPI
                _install_status["progress"] = "安装 ML 依赖 (CPU/NVIDIA)..."
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

            _install_status["progress"] = "Done! 请重启应用"
        except subprocess.TimeoutExpired:
            _install_status["error"] = "Installation timed out (30 min)"
        except Exception as e:
            _install_status["error"] = str(e)
        finally:
            _install_status["running"] = False

    threading.Thread(target=_install, daemon=True).start()
    return {"status": "started"}
