"""TTS API routes."""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.tts.base import TTSEngine
from backend.tts.manager import tts_manager
from backend.config import settings

router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: str = Field(default="zh-CN-XiaoxiaoNeural")
    engine: Optional[TTSEngine] = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-1.0, le=1.0)


class TTSResponse(BaseModel):
    task_id: str
    audio_url: str
    duration: float
    voice_id: str


@router.post("/tts", response_model=TTSResponse)
async def synthesize_tts(req: TTSRequest):
    """Synthesize text to speech."""
    task_id = uuid.uuid4().hex[:12]
    ext = "mp3" if req.engine == TTSEngine.MIMO else "mp3"
    output_path = settings.output_dir / "tts" / f"{task_id}.{ext}"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = await tts_manager.synthesize(
        text=req.text,
        voice_id=req.voice_id,
        output_path=output_path,
        engine=req.engine,
        speed=req.speed,
        pitch=req.pitch,
    )

    return TTSResponse(
        task_id=task_id,
        audio_url=f"/api/v1/tts/{task_id}/audio",
        duration=result.duration,
        voice_id=result.voice_id,
    )


@router.get("/tts/{task_id}/audio")
async def download_tts_audio(task_id: str):
    """Download generated TTS audio."""
    for ext in ("mp3", "wav", "ogg"):
        path = settings.output_dir / "tts" / f"{task_id}.{ext}"
        if path.exists():
            return FileResponse(path, media_type="audio/mpeg")
    raise HTTPException(404, "Audio not found")


class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    engine: str


@router.get("/tts/voices", response_model=list[VoiceInfo])
async def list_tts_voices(
    engine: Optional[TTSEngine] = Query(None),
    language: Optional[str] = Query(None),
):
    """List available TTS voices."""
    voices = await tts_manager.list_voices(engine=engine, language=language)
    return [
        VoiceInfo(
            id=v.id,
            name=v.name,
            language=v.language,
            gender=v.gender,
            engine=v.engine.value,
        )
        for v in voices
    ]
