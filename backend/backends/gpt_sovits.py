"""GPT-SoVITS backend for voice conversion and TTS."""
import asyncio
import logging
from pathlib import Path

import httpx

from backend.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


class GPTSoVITSBackend(ComputeBackend):
    """Voice conversion using GPT-SoVITS API (local or remote)."""

    def __init__(self, base_url: str = "http://127.0.0.1:9880"):
        self.base_url = base_url.rstrip("/")

    async def convert_voice(
        self,
        input_audio: Path,
        voice_id: str,
        output_path: Path,
        pitch_shift: int = 0,
        on_progress: callable | None = None,
        text: str = "",
        text_lang: str = "zh",
        prompt_text: str = "",
        prompt_lang: str = "zh",
        speed_factor: float = 1.0,
    ) -> Path:
        """Convert voice using GPT-SoVITS API.

        voice_id: path to reference audio file
        text: text to synthesize (for TTS mode)
        For voice conversion, provide input_audio as reference.
        """
        if on_progress:
            on_progress(0.1)

        ref_audio = voice_id  # voice_id is the reference audio path

        async with httpx.AsyncClient(timeout=300) as client:
            if on_progress:
                on_progress(0.3)

            # GPT-SoVITS TTS API
            payload = {
                "text": text or " ",  # Required field
                "text_lang": text_lang,
                "ref_audio_path": str(ref_audio),
                "prompt_text": prompt_text,
                "prompt_lang": prompt_lang,
                "speed_factor": speed_factor,
                "streaming_mode": False,
                "media_type": "wav",
            }

            resp = await client.post(
                f"{self.base_url}/tts",
                json=payload,
            )

            if resp.status_code != 200:
                raise RuntimeError(
                    f"GPT-SoVITS API error: {resp.status_code} {resp.text}"
                )

            if on_progress:
                on_progress(0.9)

            output_path.write_bytes(resp.content)

        if on_progress:
            on_progress(1.0)

        return output_path

    async def set_model(
        self,
        gpt_weights: str | None = None,
        sovits_weights: str | None = None,
    ):
        """Switch GPT-SoVITS model weights."""
        async with httpx.AsyncClient(timeout=60) as client:
            if gpt_weights:
                resp = await client.get(
                    f"{self.base_url}/set_gpt_weights",
                    params={"weights_path": gpt_weights},
                )
                if resp.status_code != 200:
                    logger.error(f"Failed to set GPT weights: {resp.text}")

            if sovits_weights:
                resp = await client.get(
                    f"{self.base_url}/set_sovits_weights",
                    params={"weights_path": sovits_weights},
                )
                if resp.status_code != 200:
                    logger.error(f"Failed to set SoVITS weights: {resp.text}")

    async def health_check(self) -> bool:
        """Check if GPT-SoVITS API is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/")
                return resp.status_code in (200, 404, 405)
        except Exception:
            return False
