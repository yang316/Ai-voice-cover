"""HuggingFace model search and download API routes."""
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DownloadRequest(BaseModel):
    repo_id: str  # e.g. "lj1995/VoiceConversionWebUI"
    voice_name: str = ""  # Local folder name
    file_pattern: str = "*.pth"  # Filter files


class DownloadStatus(BaseModel):
    status: str
    message: str
    files: list[str] = []


@router.post("/models/download-base", response_model=DownloadStatus)
async def download_base_models():
    """Download all required base/pretrained models (HuBERT, RMVPE, RVC v2)."""
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "download_models.py"
    if not script.exists():
        raise HTTPException(404, "download_models.py not found")

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--base-only"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0:
            return DownloadStatus(
                status="ok",
                message="基础模型下载完成",
                files=[line.strip() for line in result.stdout.split("\n") if "✓" in line],
            )
        else:
            raise HTTPException(500, detail=result.stderr or result.stdout)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "下载超时（10分钟）")


@router.post("/models/download-voice", response_model=DownloadStatus)
async def download_voice_model(req: DownloadRequest):
    """Download a voice model from HuggingFace."""
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "download_models.py"
    if not script.exists():
        raise HTTPException(404, "download_models.py not found")

    cmd = [sys.executable, str(script), "--voice", req.repo_id]
    if req.voice_name:
        cmd += ["--voice-name", req.voice_name]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            return DownloadStatus(
                status="ok",
                message=f"音色模型 {req.repo_id} 下载完成",
                files=[line.strip() for line in result.stdout.split("\n") if "✓" in line],
            )
        else:
            raise HTTPException(500, detail=result.stderr or result.stdout)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "下载超时（10分钟）")


@router.get("/models/voices")
async def list_voice_models():
    """List locally installed voice models."""
    from backend.config import settings
    voices_dir = settings.voices_dir
    voices = []

    if voices_dir.exists():
        for d in sorted(voices_dir.iterdir()):
            if d.is_dir():
                pth_files = list(d.glob("*.pth"))
                index_files = list(d.glob("*.index"))
                if pth_files:
                    voices.append({
                        "id": d.name,
                        "has_model": True,
                        "has_index": len(index_files) > 0,
                        "model_file": pth_files[0].name,
                        "size_mb": round(pth_files[0].stat().st_size / 1024 / 1024, 1),
                    })

    return {"voices": voices, "total": len(voices)}
