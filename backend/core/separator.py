"""Vocal separation using Demucs."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VocalSeparator:
    """Separate vocals from accompaniment using Demucs."""

    def __init__(self, model_name: str = "htdemucs"):
        self.model_name = model_name

    async def separate(
        self,
        input_path: Path,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """
        Separate input audio into vocals and accompaniment.

        Returns: (vocals_path, accompaniment_path)
        """
        vocals_path = output_dir / "vocals.wav"
        accomp_path = output_dir / "accompaniment.wav"

        if vocals_path.exists() and accomp_path.exists():
            logger.info("Using cached separated files")
            return vocals_path, accomp_path

        # Run Demucs in subprocess to avoid blocking
        import sys
        cmd = [
            sys.executable, "-m", "demucs",
            "--two-stems", "vocals",
            "-n", self.model_name,
            "-o", str(output_dir),
            str(input_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Demucs failed: {stderr.decode()}")

        # Demucs output structure: output_dir / model_name / stem / vocals.wav
        stem = input_path.stem
        demucs_out = output_dir / self.model_name / stem

        # Move files to expected locations
        import shutil
        voc = demucs_out / "vocals.wav"
        no_voc = demucs_out / "no_vocals.wav"

        if voc.exists():
            shutil.move(str(voc), str(vocals_path))
        else:
            raise FileNotFoundError(f"Demucs vocals output not found at {voc}")

        if no_voc.exists():
            shutil.move(str(no_voc), str(accomp_path))

        # Cleanup demucs subdirectory
        shutil.rmtree(output_dir / self.model_name, ignore_errors=True)

        return vocals_path, accomp_path
