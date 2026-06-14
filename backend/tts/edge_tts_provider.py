"""Microsoft Edge TTS provider (free, no API key required)."""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from backend.tts.base import TTSProvider, TTSVoice, TTSResult, TTSEngine

logger = logging.getLogger(__name__)

# Popular Chinese + English voices
POPULAR_VOICES = [
    ("zh-CN-XiaoxiaoNeural", "晓晓（女）", "zh-CN", "female"),
    ("zh-CN-YunxiNeural", "云希（男）", "zh-CN", "male"),
    ("zh-CN-YunjianNeural", "云健（男）", "zh-CN", "male"),
    ("zh-CN-XiaoyiNeural", "晓依（女）", "zh-CN", "female"),
    ("zh-CN-YunyangNeural", "云扬（男）", "zh-CN", "male"),
    ("zh-CN-XiaochenNeural", "晓辰（女）", "zh-CN", "female"),
    ("zh-CN-XiaohanNeural", "晓涵（女）", "zh-CN", "female"),
    ("zh-CN-XiaomengNeural", "晓梦（女）", "zh-CN", "female"),
    ("zh-CN-XiaomoNeural", "晓墨（女）", "zh-CN", "female"),
    ("zh-CN-XiaoruiNeural", "晓睿（女）", "zh-CN", "female"),
    ("zh-CN-XiaoshuangNeural", "晓双（女童）", "zh-CN", "female"),
    ("zh-CN-XiaoxuanNeural", "晓萱（女）", "zh-CN", "female"),
    ("zh-CN-XiaoyanNeural", "晓颜（女）", "zh-CN", "female"),
    ("zh-CN-XiaozhenNeural", "晓甄（女）", "zh-CN", "female"),
    ("en-US-JennyNeural", "Jenny (F)", "en-US", "female"),
    ("en-US-GuyNeural", "Guy (M)", "en-US", "male"),
    ("en-US-AriaNeural", "Aria (F)", "en-US", "female"),
    ("en-US-DavisNeural", "Davis (M)", "en-US", "male"),
    ("ja-JP-NanamiNeural", "Nanami (F)", "ja-JP", "female"),
    ("ja-JP-KeitaNeural", "Keita (M)", "ja-JP", "male"),
    ("ko-KR-SunHiNeural", "SunHi (F)", "ko-KR", "female"),
    ("ko-KR-InJoonNeural", "InJoon (M)", "ko-KR", "male"),
]


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS - free, runs locally, no API key needed."""

    @property
    def engine(self) -> TTSEngine:
        return TTSEngine.EDGE

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> TTSResult:
        import edge_tts

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert speed/pitch to SSML rate/pitch
        rate = f"{int((speed - 1) * 100):+d}%"
        pitch_str = f"{int(pitch * 100):+d}Hz"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate,
            pitch=pitch_str,
        )

        await communicate.save(str(output_path))

        # Get duration from the saved file
        duration = await self._get_duration(output_path)

        logger.info(f"Edge TTS: '{text[:30]}...' -> {output_path} ({duration:.1f}s)")

        return TTSResult(
            audio_path=output_path,
            duration=duration,
            sample_rate=24000,
            voice_id=voice_id,
        )

    async def list_voices(self, language: Optional[str] = None) -> list[TTSVoice]:
        voices = []
        for vid, name, lang, gender in POPULAR_VOICES:
            if language and not lang.startswith(language):
                continue
            voices.append(TTSVoice(
                id=vid,
                name=name,
                language=lang,
                gender=gender,
                engine=TTSEngine.EDGE,
            ))
        return voices

    @staticmethod
    async def _get_duration(path: Path) -> float:
        """Get audio duration using soundfile."""
        try:
            import soundfile as sf
            info = sf.info(str(path))
            return info.duration
        except Exception:
            return 0.0
