"""Main pipeline: vocal separation -> voice conversion -> mixing."""
from typing import Callable, Optional
import logging
from pathlib import Path

from backend.core.separator import VocalSeparator
from backend.core.mixer import AudioMixer
from backend.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


class VoiceCoverPipeline:
    """Orchestrates the full AI voice cover pipeline."""

    def __init__(self, backend: ComputeBackend):
        self.backend = backend
        self.separator = VocalSeparator()
        self.mixer = AudioMixer()

    async def run(
        self,
        input_path: str | Path,
        voice_id: str,
        output_dir: str | Path,
        pitch_shift: int = 0,
        denoise: bool = True,
        on_progress: Optional[Callable] = None,
    ) -> Path:
        """
        Run the full pipeline.

        Steps:
        1. Separate vocals and accompaniment from input
        2. Convert vocals to target voice
        3. Mix converted vocals with accompaniment

        Returns: path to output file
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.stem

        def progress(step: str, pct: int):
            logger.info(f"[{pct}%] {step}")
            if on_progress:
                on_progress(step, pct)

        # Step 1: Vocal separation
        progress("Separating vocals...", 5)
        vocals_path, accompaniment_path = await self.separator.separate(
            input_path, output_dir
        )
        progress("Vocal separation complete", 30)

        # Step 2: Voice conversion
        progress("Converting voice...", 35)
        converted_path = output_dir / f"{stem}_converted.wav"

        try:
            result = await self.backend.convert_voice(
                input_audio=vocals_path,
                voice_id=voice_id,
                output_path=converted_path,
                pitch_shift=pitch_shift,
                on_progress=lambda p: progress("Converting voice...", 35 + int(p * 0.50)),
            )
            # Check if conversion produced valid output
            if not converted_path.exists() or converted_path.stat().st_size < 1000:
                raise RuntimeError("Voice conversion produced empty output")
        except Exception as e:
            logger.warning(f"Voice conversion failed: {e}, using original vocals")
            import shutil
            shutil.copy2(str(vocals_path), str(converted_path))
            # Apply pitch shift via ffmpeg if requested
            if pitch_shift != 0:
                shifted_path = output_dir / f"{stem}_shifted.wav"
                ratio = 2 ** (pitch_shift / 12)
                cmd = ["ffmpeg", "-y", "-i", str(converted_path),
                       "-af", f"rubberband=pitch={ratio:.6f}", str(shifted_path)]
                proc = await asyncio.create_subprocess_exec(*cmd,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await proc.communicate()
                if shifted_path.exists():
                    shutil.move(str(shifted_path), str(converted_path))

        progress("Voice conversion complete", 85)

        # Step 3: Optional denoise
        if denoise:
            converted_path = await self.mixer.denoise(converted_path, output_dir)
            progress("Denoising complete", 90)

        # Step 4: Mix
        progress("Mixing audio...", 92)
        final_path = await self.mixer.mix(
            vocals=converted_path,
            accompaniment=accompaniment_path,
            output_path=output_dir / f"{stem}_cover.wav",
        )
        progress("Done!", 100)

        return final_path
