"""Local GPU backend using RVC for voice conversion."""
import asyncio
import logging
from pathlib import Path

from backend.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


class LocalGPUBackend(ComputeBackend):
    """Voice conversion using local RVC model."""

    def __init__(self):
        self._model_cache: dict = {}

    async def convert_voice(
        self,
        input_audio: Path,
        voice_id: str,
        output_path: Path,
        pitch_shift: int = 0,
        on_progress: callable | None = None,
    ) -> Path:
        """Convert voice using RVC inference."""
        import asyncio
        from functools import partial

        if on_progress:
            on_progress(0.0)

        def _run_rvc():
            """Run RVC in thread pool to avoid blocking event loop."""
            from backend.core.rvc_infer import rvc_convert
            return rvc_convert(
                input_path=str(input_audio),
                output_path=str(output_path),
                voice_id=voice_id,
                pitch_shift=pitch_shift,
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run_rvc)
        except FileNotFoundError:
            # Voice model not found, fallback to pitch-shift
            logger.warning(f"Voice model '{voice_id}' not found, using pitch-shift fallback")
            await self._fallback_convert(input_audio, output_path, pitch_shift)
        except Exception as e:
            logger.error(f"RVC inference failed: {e}")
            await self._fallback_convert(input_audio, output_path, pitch_shift)

        if on_progress:
            on_progress(1.0)

        return output_path

    async def _fallback_convert(self, input_audio: Path, output_path: Path, pitch_shift: int):
        """Fallback: just pitch-shift the audio using ffmpeg."""
        if pitch_shift == 0:
            # Just copy
            import shutil
            shutil.copy2(str(input_audio), str(output_path))
            return

        # Use rubberband for pitch shifting
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_audio),
            "-af", f"rubberband=pitch={2 ** (pitch_shift / 12):.6f}",
            str(output_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def health_check(self) -> bool:
        """Check if local GPU is available."""
        from backend.core.device import get_device_info
        info = get_device_info()
        return info["best_device"] != "cpu"
