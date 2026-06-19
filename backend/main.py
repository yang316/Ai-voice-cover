"""FastAPI application."""
from contextlib import asynccontextmanager
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings

logger = logging.getLogger(__name__)

# Track which features are available
_available_features = set()
_missing_features = set()


def _try_load_router(module_path: str, attr: str, name: str):
    """Try to import a router, return None if dependencies missing."""
    try:
        mod = __import__(module_path, fromlist=[attr])
        router = getattr(mod, attr)
        _available_features.add(name)
        return router
    except ImportError as e:
        _missing_features.add(name)
        logger.warning("Router '%s' unavailable (missing deps: %s)", name, e)
        return None
    except Exception as e:
        _missing_features.add(name)
        logger.warning("Router '%s' failed to load: %s", name, e)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("Available features: %s", ", ".join(sorted(_available_features)) or "none")
    if _missing_features:
        logger.info("Missing features (install ML deps to enable): %s", ", ".join(sorted(_missing_features)))

    # Run temp file cleanup on startup
    try:
        from backend.core.cleanup import cleanup_temp_files
        cleanup_temp_files(settings.upload_dir, settings.output_dir)
    except Exception as e:
        logger.warning("Startup cleanup failed: %s", e)

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.2",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — prevents raw tracebacks leaking to clients."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )

# API routes — each router is optional, app starts regardless
_routers = [
    ("backend.api.routes", "router", "covers", "/api/v1", "covers"),
    ("backend.api.voice_routes", "router", "voices", "/api/v1", "voices"),
    ("backend.api.hf_routes", "router", "huggingface", "/api/v1", "huggingface"),
    ("backend.api.model_routes", "router", "models", "/api/v1", "models"),
    ("backend.api.tts_routes", "router", "tts", "/api/v1", "tts"),
    ("backend.api.train_routes", "router", "training", "/api/v1", "training"),
    ("backend.api.ml_routes", "router", "ml", "/api/v1", "ml"),
]

for module_path, attr, name, prefix, tag in _routers:
    router = _try_load_router(module_path, attr, name)
    if router:
        app.include_router(router, prefix=prefix, tags=[tag])


@app.get("/api/v1/health")
def health():
    """Health check — always available even without ML deps."""
    backends = {}
    for name in _available_features:
        backends[name] = True
    for name in _missing_features:
        backends[name] = False

    # Try to get GPU info if available
    gpu_info = {"available": False, "device": "CPU"}
    device_type = "cpu"
    try:
        from backend.core.device import get_device_info
        device = get_device_info()
        gpu_info = {
            "available": device["best_device"] != "cpu",
            "device": device["devices"][0]["name"] if device["devices"] else "CPU",
        }
        device_type = device["best_device"]
    except Exception:
        pass

    # Check if GPU upgrade is available (CPU-only torch on a GPU machine)
    gpu_upgradeable = False
    gpu_detection = None
    try:
        from backend.api.ml_routes import _check_torch_backend, _detect_gpu
        torch_info = _check_torch_backend()
        gpu_detection = _detect_gpu()
        logger.info("Health check: torch=%s, gpu=%s, upgradeable=%s",
                     torch_info, gpu_detection.get("vendor"), torch_info.get("gpu_upgradeable"))
        if torch_info.get("gpu_upgradeable"):
            gpu_upgradeable = True
    except Exception as e:
        logger.error("Health GPU check failed: %s", e)

    return {
        "status": "online",
        "gpu": gpu_info,
        "backends": backends,
        "device_type": device_type,
        "features": {
            "available": sorted(_available_features),
            "missing": sorted(_missing_features),
        },
        "gpu_upgradeable": gpu_upgradeable,
        "gpu_detection": gpu_detection,
    }


@app.get("/api/v1/features")
def list_features():
    """Report which features are available."""
    return {
        "available": sorted(_available_features),
        "missing": sorted(_missing_features),
    }


# Serve frontend
frontend_dir = settings.base_dir / "frontend-vue" / "dist"
if not frontend_dir.exists():
    frontend_dir = settings.base_dir / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
