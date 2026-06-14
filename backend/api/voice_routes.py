"""Voice model management API routes."""
import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.api.schemas import VoiceInfo
from backend.config import settings

router = APIRouter()


@router.get("/voices", response_model=list[VoiceInfo])
async def list_voices():
    """List all available voice models."""
    voices = []
    if not settings.voices_dir.exists():
        return voices

    for voice_dir in sorted(settings.voices_dir.iterdir()):
        if not voice_dir.is_dir():
            continue

        # Find model and index files
        pth_files = list(voice_dir.glob("*.pth"))
        index_files = list(voice_dir.glob("*.index"))

        model_path = str(pth_files[0]) if pth_files else None
        index_path = str(index_files[0]) if index_files else None

        meta_path = voice_dir / "metadata.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text())
            # Ensure model_path and index_path are set
            if "model_path" not in data and model_path:
                data["model_path"] = model_path
            if "index_path" not in data and index_path:
                data["index_path"] = index_path
            voices.append(VoiceInfo(**data))
        else:
            # Auto-generate metadata from directory name
            voices.append(VoiceInfo(
                id=voice_dir.name,
                name=voice_dir.name.replace("_", " ").title(),
                source="local",
                model_path=model_path,
                index_path=index_path,
            ))

    return voices


@router.post("/voices", response_model=VoiceInfo)
async def upload_voice(
    name: str = Form(...),
    description: str = Form(""),
    model_file: UploadFile = File(...),
    index_file: UploadFile | None = File(None),
):
    """
    Upload a new voice model.

    Requires:
    - model_file: RVC .pth model file
    - index_file: (optional) FAISS .index file
    """
    if not model_file.filename or not model_file.filename.endswith(".pth"):
        raise HTTPException(400, "Model file must be a .pth file")

    # Create voice directory
    voice_id = name.lower().replace(" ", "_").replace("-", "_")
    voice_dir = settings.voices_dir / voice_id
    voice_dir.mkdir(parents=True, exist_ok=True)

    # Save model file
    model_path = voice_dir / model_file.filename
    with open(model_path, "wb") as f:
        content = await model_file.read()
        f.write(content)

    # Save index file if provided
    index_path = None
    if index_file and index_file.filename and index_file.filename.endswith(".index"):
        index_path = voice_dir / index_file.filename
        with open(index_path, "wb") as f:
            content = await index_file.read()
            f.write(content)

    # Save metadata
    voice_info = VoiceInfo(
        id=voice_id,
        name=name,
        description=description,
        source="local",
        model_path=str(model_path),
        index_path=str(index_path) if index_path else None,
    )
    meta_path = voice_dir / "metadata.json"
    meta_path.write_text(json.dumps(voice_info.model_dump(), indent=2, ensure_ascii=False))

    return voice_info


@router.get("/voices/{voice_id}", response_model=VoiceInfo)
async def get_voice(voice_id: str):
    """Get voice model details."""
    voice_dir = settings.voices_dir / voice_id
    if not voice_dir.exists():
        raise HTTPException(404, "Voice not found")

    meta_path = voice_dir / "metadata.json"
    if meta_path.exists():
        data = json.loads(meta_path.read_text())
        return VoiceInfo(**data)

    return VoiceInfo(id=voice_id, name=voice_id)


@router.delete("/voices/{voice_id}")
async def delete_voice(voice_id: str):
    """Delete a voice model."""
    voice_dir = settings.voices_dir / voice_id
    if not voice_dir.exists():
        raise HTTPException(404, "Voice not found")

    shutil.rmtree(voice_dir)
    return {"status": "deleted", "voice_id": voice_id}


@router.get("/voices/{voice_id}/preview")
async def preview_voice(voice_id: str):
    """Download voice model preview audio (if exists)."""
    voice_dir = settings.voices_dir / voice_id
    preview_path = voice_dir / "preview.wav"

    if not preview_path.exists():
        preview_path = voice_dir / "preview.mp3"

    if not preview_path.exists():
        raise HTTPException(404, "Preview not found")

    return FileResponse(preview_path, media_type="audio/wav")
