"""TTS manager - coordinates all TTS providers."""
import logging
from pathlib import Path
from typing import Optional

from backend.tts.base import TTSProvider, TTSVoice, TTSResult, TTSEngine
from backend.tts.edge_tts_provider import EdgeTTSProvider

logger = logging.getLogger(__name__)


class TTSManager:
    """Manages multiple TTS providers."""

    def __init__(self):
        self._providers: dict[TTSEngine, TTSProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize available TTS providers."""
        # Edge TTS always available (free)
        self._providers[TTSEngine.EDGE] = EdgeTTSProvider()
        logger.info("TTS: Edge TTS initialized")

        # MiMo TTS (needs API key)
        try:
            from backend.config import settings
            if settings.mimo_api_key:
                from backend.tts.mimo_provider import MiMoTTSProvider
                self._providers[TTSEngine.MIMO] = MiMoTTSProvider(settings.mimo_api_key)
                logger.info("TTS: MiMo TTS initialized")
        except Exception as e:
            logger.debug(f"MiMo TTS not available: {e}")

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        engine: Optional[TTSEngine] = None,
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> TTSResult:
        """Synthesize text to speech using specified or auto-detected engine."""
        provider = self._get_provider(engine, voice_id)
        return await provider.synthesize(text, voice_id, output_path, speed, pitch)

    async def list_voices(
        self,
        engine: Optional[TTSEngine] = None,
        language: Optional[str] = None,
    ) -> list[TTSVoice]:
        """List all available voices."""
        voices = []
        providers = [self._providers[engine]] if engine else self._providers.values()
        for provider in providers:
            try:
                voices.extend(await provider.list_voices(language))
            except Exception as e:
                logger.warning(f"Failed to list voices for {provider.engine}: {e}")
        return voices

    def _get_provider(self, engine: Optional[TTSEngine], voice_id: str) -> TTSProvider:
        """Get provider by engine or auto-detect from voice_id."""
        if engine and engine in self._providers:
            return self._providers[engine]

        # Auto-detect from voice_id prefix
        for eng, provider in self._providers.items():
            if eng.value in voice_id.lower():
                return provider

        # Default to Edge TTS
        return self._providers[TTSEngine.EDGE]

    @property
    def available_engines(self) -> list[TTSEngine]:
        return list(self._providers.keys())


# Singleton
tts_manager = TTSManager()
