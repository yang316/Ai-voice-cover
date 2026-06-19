"""API routes."""
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.api.schemas import (
    ComputeBackend,
    HealthResponse,
    TaskInfo,
    TaskResponse,
    TaskStatus,
    TaskStep,
    VoiceInfo,
)
from backend.backends.factory import ComputeBackendType, create_backend
from backend.config import settings
from backend.core.database import get_all_tasks, get_task, save_task

router = APIRouter()


def _to_task_info(data: dict) -> TaskInfo:
    """Convert database row to TaskInfo."""
    status = TaskStatus(data["status"])

    # Map old status to step
    step_mapping = {
        TaskStatus.PENDING: TaskStep.SEPARATING,
        TaskStatus.PROCESSING: TaskStep.CONVERTING,
        TaskStatus.COMPLETED: TaskStep.COMPLETE,
        TaskStatus.FAILED: TaskStep.COMPLETE,
    }
    step = step_mapping.get(status, TaskStep.SEPARATING)

    return TaskInfo(
        id=data["task_id"],
        status=status,
        progress=data.get("progress", 0),
        step=step,
        message=data.get("message", ""),
        input_file=data.get("input_file", ""),
        output_file=data.get("output_file") or None,
        voice_id=data.get("voice_id", ""),
        created_at=data.get("created_at", ""),
        completed_at=data.get("completed_at") or None,
        error=data.get("error") or None,
    )


# NOTE: /health is defined in main.py (includes features field)


@router.post("/covers", response_model=TaskResponse)
async def create_cover(
    audio_file: UploadFile = File(...),
    voice_id: str = Form(...),
    backend: ComputeBackend = Form(ComputeBackend.LOCAL),
    pitch_shift: int = Form(0),
    denoise: bool = Form(True),
    api_key: str | None = Form(None),
):
    """Upload a song and create an AI voice cover."""
    if not audio_file.filename:
        raise HTTPException(400, "No file uploaded")

    task_id = uuid.uuid4().hex[:12]
    ext = Path(audio_file.filename).suffix or ".mp3"
    input_path = settings.upload_dir / f"{task_id}{ext}"

    with open(input_path, "wb") as f:
        content = await audio_file.read()
        f.write(content)

    now = datetime.now(timezone.utc).isoformat()
    save_task(
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        progress=0,
        message="Task queued",
        input_file=str(input_path),
        voice_id=voice_id,
        backend=backend.value,
        created_at=now,
    )

    from backend.workers.tasks import process_cover
    process_cover.delay(
        task_id, str(input_path), voice_id,
        backend.value, pitch_shift, denoise, api_key,
    )

    return TaskResponse(task_id=task_id, status=TaskStatus.PENDING, message="Task created")


@router.get("/covers/{task_id}", response_model=TaskInfo)
async def get_task_status(task_id: str):
    """Get task status and progress."""
    data = get_task(task_id)
    if not data:
        raise HTTPException(404, "Task not found")
    return _to_task_info(data)


@router.get("/covers/{task_id}/download")
async def download_result(task_id: str):
    """Download the completed cover."""
    data = get_task(task_id)
    if not data or not data.get("output_file"):
        raise HTTPException(404, "Result not found")
    return FileResponse(
        data["output_file"],
        filename=f"cover_{task_id}.wav",
        media_type="audio/wav",
    )


@router.get("/tasks", response_model=list[TaskInfo])
async def list_tasks():
    """List all tasks."""
    return [_to_task_info(d) for d in get_all_tasks()]


def update_task(task_id: str, **kwargs):
    """Update task info (called by workers)."""
    data = get_task(task_id)
    if not data:
        return

    # Map TaskStatus enum to string
    for k, v in kwargs.items():
        if hasattr(v, "value"):
            kwargs[k] = v.value

    save_task(task_id=task_id, **kwargs)
