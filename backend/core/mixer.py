"""Audio mixing and post-processing."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioMixer:
    """Mix converted vocals with accompaniment."""

    async def mix(
        self,
        vocals: Path,
        accompaniment: Path,
        output_path: Path,
        vocals_gain: float = 0.0,
        accomp_gain: float = 0.0,
    ) -> Path:
        """
        Mix vocals and accompaniment into final output.
        Gains are in dB.
        """
        filter_complex = (
            f"[0:a]volume={10 ** (vocals_gain / 20):.4f}[vocals];"
            f"[1:a]volume={10 ** (accomp_gain / 20):.4f}[accomp];"
            f"[vocals][accomp]amix=inputs=2:duration=longest[out]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(vocals),
            "-i", str(accompaniment),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ar", "44100",
            str(output_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg mix failed: {stderr.decode()}")

        logger.info(f"Mixed output: {output_path}")
        return output_path

    async def denoise(self, audio_path: Path, output_dir: Path) -> Path:
        """Basic noise reduction using ffmpeg highpass/lowpass filter."""
        output_path = output_dir / f"{audio_path.stem}_denoised.wav"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-af", "highpass=f=80,lowpass=f=12000,afftdn=nf=-25",
            str(output_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        return output_path if output_path.exists() else audio_path
