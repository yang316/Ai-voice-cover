"""Cloud API backend for voice conversion."""
import asyncio
import logging
import tempfile
from pathlib import Path

import httpx

from backend.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


class ElevenLabsBackend(ComputeBackend):
    """Voice conversion using ElevenLabs API."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def convert_voice(
        self,
        input_audio: Path,
        voice_id: str,
        output_path: Path,
        pitch_shift: int = 0,
        on_progress: callable | None = None,
    ) -> Path:
        """Convert voice using ElevenLabs voice changer API."""
        if on_progress:
            on_progress(0.1)

        async with httpx.AsyncClient(timeout=300) as client:
            with open(input_audio, "rb") as f:
                audio_data = f.read()

            if on_progress:
                on_progress(0.3)

            # Use voice changer endpoint
            resp = await client.post(
                f"{self.BASE_URL}/speech-to-speech/{voice_id}",
                headers={"xi-api-key": self.api_key},
                files={"audio": ("input.wav", audio_data, "audio/wav")},
                data={
                    "model_id": "eleven_english_sts_v2",
                    "output_format": "wav_44100",
                },
            )

            if resp.status_code != 200:
                raise RuntimeError(f"ElevenLabs API error: {resp.status_code} {resp.text}")

            if on_progress:
                on_progress(0.9)

            output_path.write_bytes(resp.content)

        if on_progress:
            on_progress(1.0)

        return output_path

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/user",
                    headers={"xi-api-key": self.api_key},
                )
                return resp.status_code == 200
        except Exception:
            return False


class FishAudioBackend(ComputeBackend):
    """Voice conversion using Fish Audio API."""

    BASE_URL = "https://api.fish.audio"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def convert_voice(
        self,
        input_audio: Path,
        voice_id: str,
        output_path: Path,
        pitch_shift: int = 0,
        on_progress: callable | None = None,
    ) -> Path:
        """Convert voice using Fish Audio TTS/VC API."""
        if on_progress:
            on_progress(0.1)

        async with httpx.AsyncClient(timeout=300) as client:
            with open(input_audio, "rb") as f:
                audio_data = f.read()

            if on_progress:
                on_progress(0.3)

            # Fish Audio speech-to-speech
            resp = await client.post(
                f"{self.BASE_URL}/v1/speech-to-speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                files={"audio": ("input.wav", audio_data, "audio/wav")},
                data={"reference_id": voice_id},
            )

            if resp.status_code != 200:
                raise RuntimeError(f"Fish Audio API error: {resp.status_code} {resp.text}")

            if on_progress:
                on_progress(0.9)

            output_path.write_bytes(resp.content)

        if on_progress:
            on_progress(1.0)

        return output_path

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False
