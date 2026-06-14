"""TTS (Text-to-Speech) backend abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TTSEngine(str, Enum):
    EDGE = "edge"           # Microsoft Edge TTS (free, local)
    MIMO = "mimo"           # Xiaomi MiMo TTS API
    LOCAL = "local"         # Local GPU TTS (Coqui/etc)


@dataclass
class TTSVoice:
    """Available TTS voice."""
    id: str                 # e.g. "zh-CN-XiaoxiaoNeural"
    name: str               # Display name
    language: str           # e.g. "zh-CN"
    gender: str             # "male" / "female"
    engine: TTSEngine


@dataclass
class TTSResult:
    """TTS synthesis result."""
    audio_path: Path
    duration: float         # seconds
    sample_rate: int
    voice_id: str


class TTSProvider(ABC):
    """Base class for TTS providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> TTSResult:
        """Synthesize text to speech."""
        ...

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> list[TTSVoice]:
        """List available voices."""
        ...

    @property
    @abstractmethod
    def engine(self) -> TTSEngine:
        ...
