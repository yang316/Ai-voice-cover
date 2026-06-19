"""API schemas."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComputeBackend(str, Enum):
    LOCAL = "local"
    GPT_SOVITS = "gpt_sovits"
    ELEVENLABS = "elevenlabs"
    FISH_AUDIO = "fish_audio"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStep(str, Enum):
    SEPARATING = "separating"
    CONVERTING = "converting"
    MIXING = "mixing"
    COMPLETE = "complete"


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str = ""


class TaskInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="id")
    status: TaskStatus
    progress: int = 0
    step: TaskStep = TaskStep.SEPARATING
    message: str = ""
    input_file: str = ""
    output_file: Optional[str] = None
    voice_id: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    error: Optional[str] = None


class VoiceInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: Optional[str] = None
    modelPath: Optional[str] = Field(None, alias="model_path")
    indexPath: Optional[str] = Field(None, alias="index_path")
    source: str = "local"


class DeviceInfo(BaseModel):
    name: str
    type: str
    available: bool
    memory: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    gpu: dict = Field(default_factory=lambda: {"available": False, "device": "CPU"})
    backends: dict = Field(default_factory=dict)
    device_type: str = "cpu"
    device_name: str = "CPU"
    devices: list[DeviceInfo] = Field(default_factory=list)
