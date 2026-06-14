"""FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as covers_router
from backend.api.voice_routes import router as voices_router
from backend.api.hf_routes import router as hf_router
from backend.api.model_routes import router as models_router
from backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(covers_router, prefix="/api/v1", tags=["covers"])
app.include_router(voices_router, prefix="/api/v1", tags=["voices"])
app.include_router(hf_router, prefix="/api/v1", tags=["huggingface"])
app.include_router(models_router, prefix="/api/v1", tags=["models"])

# Serve frontend
frontend_dir = settings.base_dir / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
