"""Multi-device support: NVIDIA CUDA, AMD ROCm, Intel XPU, CPU."""
import logging
import platform

logger = logging.getLogger(__name__)


def get_device_info() -> dict:
    """Detect all available compute devices."""
    info = {
        "platform": platform.machine(),
        "devices": [],
        "best_device": "cpu",
        "torch_available": False,
    }

    try:
        import torch
        info["torch_available"] = True
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()

        # NVIDIA CUDA
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                info["devices"].append({
                    "type": "cuda",
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_gb": round(props.total_mem / 1024**3, 1),
                    "compute_capability": f"{props.major}.{props.minor}",
                })
            info["best_device"] = "cuda:0"
            logger.info(f"CUDA: {torch.cuda.device_count()} device(s)")

        # AMD ROCm (uses same torch.cuda interface when ROCm is installed)
        if hasattr(torch.version, "hip") and torch.version.hip is not None:
            info["rocm_available"] = True
            if torch.cuda.is_available():
                info["best_device"] = "cuda:0"  # ROCm maps to cuda in PyTorch
                logger.info("ROCm detected via HIP")

        # Intel XPU (Intel GPU via extension)
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            for i in range(torch.xpu.device_count()):
                info["devices"].append({
                    "type": "xpu",
                    "index": i,
                    "name": torch.xpu.get_device_name(i),
                })
            info["xpu_available"] = True
            info["best_device"] = "xpu:0"
            logger.info(f"Intel XPU: {torch.xpu.device_count()} device(s)")

        # Apple MPS (M1/M2/M3 Mac)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["devices"].append({"type": "mps", "name": "Apple Silicon GPU"})
            info["mps_available"] = True
            info["best_device"] = "mps"
            logger.info("Apple MPS available")

    except ImportError:
        logger.warning("PyTorch not installed, CPU only")

    # CPU fallback
    if not info["devices"]:
        import os
        info["devices"].append({
            "type": "cpu",
            "name": platform.processor() or "Unknown CPU",
            "cores": os.cpu_count(),
        })
        info["best_device"] = "cpu"
        logger.info("CPU only mode")

    return info


def get_device():
    """Get the best available torch device."""
    try:
        import torch
        info = get_device_info()
        device_str = info["best_device"]

        if device_str.startswith("cuda"):
            return torch.device(device_str)
        elif device_str == "xpu":
            return torch.device("xpu:0")
        elif device_str == "mps":
            return torch.device("mps")
        else:
            return torch.device("cpu")
    except ImportError:
        return None


def get_dtype(device_type: str = "cpu"):
    """Get optimal dtype for the device."""
    try:
        import torch
        if device_type in ("cuda", "xpu"):
            return torch.float16
        return torch.float32
    except ImportError:
        return None
