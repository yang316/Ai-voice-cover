"""Xiaomi MiMo TTS API provider."""
import logging
from pathlib import Path
from typing import Optional

import httpx

from backend.tts.base import TTSProvider, TTSVoice, TTSResult, TTSEngine

logger = logging.getLogger(__name__)


class MiMoTTSProvider(TTSProvider):
    """Xiaomi MiMo TTS API."""

    BASE_URL = "https://api.mimo.xiaomi.com/v1/tts"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def engine(self) -> TTSEngine:
        return TTSEngine.MIMO

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> TTSResult:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "voice": voice_id,
                    "speed": speed,
                    "pitch": pitch,
                    "format": "mp3",
                },
            )
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

        duration = await self._get_duration(output_path)
        logger.info(f"MiMo TTS: '{text[:30]}...' -> {output_path} ({duration:.1f}s)")

        return TTSResult(
            audio_path=output_path,
            duration=duration,
            sample_rate=24000,
            voice_id=voice_id,
        )

    async def list_voices(self, language: Optional[str] = None) -> list[TTSVoice]:
        """Return known MiMo voices."""
        voices = [
            TTSVoice("mimo-zh-female-1", "MiMo 女声", "zh-CN", "female", TTSEngine.MIMO),
            TTSVoice("mimo-zh-male-1", "MiMo 男声", "zh-CN", "male", TTSEngine.MIMO),
        ]
        if language:
            voices = [v for v in voices if v.language.startswith(language)]
        return voices

    @staticmethod
    async def _get_duration(path: Path) -> float:
        try:
            import soundfile as sf
            info = sf.info(str(path))
            return info.duration
        except Exception:
            return 0.0
