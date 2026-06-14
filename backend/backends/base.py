"""Abstract compute backend interface."""
from abc import ABC, abstractmethod
from pathlib import Path


class ComputeBackend(ABC):
    """Base class for voice conversion backends."""

    @abstractmethod
    async def convert_voice(
        self,
        input_audio: Path,
        voice_id: str,
        output_path: Path,
        pitch_shift: int = 0,
        on_progress: callable | None = None,
    ) -> Path:
        """
        Convert voice in input_audio to target voice_id.

        Args:
            input_audio: path to input vocals WAV
            voice_id: target voice model/ID
            output_path: where to save output
            pitch_shift: semitone shift (+/- 12)
            on_progress: callback(0.0~1.0)

        Returns: path to converted audio
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is available."""
        ...
