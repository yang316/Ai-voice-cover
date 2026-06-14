"""API request/response schemas."""
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    SEPARATING = "separating"
    CONVERTING = "converting"
    MIXING = "mixing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComputeBackend(str, Enum):
    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    FISH_AUDIO = "fish_audio"


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""
    input_file: str = ""
    output_file: str | None = None
    voice_id: str = ""
    created_at: str = ""
    completed_at: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class VoiceInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    preview_url: str | None = None
    source: str = "local"


class HealthResponse(BaseModel):
    status: str
    backends: dict[str, bool]
    device_type: str = "cpu"
    device_name: str = "Unknown"
    devices: list[dict] = []
