"""Backend factory - create compute backends by name."""
from enum import Enum

from backend.backends.base import ComputeBackend


class ComputeBackendType(str, Enum):
    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    FISH_AUDIO = "fish_audio"
    GPT_SOVITS = "gpt_sovits"


def create_backend(
    backend_type: ComputeBackendType,
    api_key: str | None = None,
    base_url: str | None = None,
) -> ComputeBackend:
    """Create a compute backend by type."""
    match backend_type:
        case ComputeBackendType.LOCAL:
            from backend.backends.local_gpu import LocalGPUBackend
            return LocalGPUBackend()

        case ComputeBackendType.ELEVENLABS:
            from backend.backends.cloud_api import ElevenLabsBackend
            if not api_key:
                raise ValueError("ElevenLabs requires an API key")
            return ElevenLabsBackend(api_key=api_key)

        case ComputeBackendType.FISH_AUDIO:
            from backend.backends.cloud_api import FishAudioBackend
            if not api_key:
                raise ValueError("Fish Audio requires an API key")
            return FishAudioBackend(api_key=api_key)

        case ComputeBackendType.GPT_SOVITS:
            from backend.backends.gpt_sovits import GPTSoVITSBackend
            return GPTSoVITSBackend(base_url=base_url or "http://127.0.0.1:9880")

        case _:
            raise ValueError(f"Unknown backend: {backend_type}")
