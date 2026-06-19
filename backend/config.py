"""Application configuration."""
import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_data_dir() -> Path:
    """Get a writable data directory for the app."""
    # Check if running from a packaged app (sidecar next to read-only install)
    sidecar_dir = Path(__file__).parent.parent

    # If sidecar dir is writable, use it (development mode)
    if os.access(str(sidecar_dir), os.W_OK):
        return sidecar_dir

    # Otherwise use platform-specific user data directory
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "AI Voice Cover"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AI Voice Cover"
    else:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ai-voice-cover"


_data_dir = _get_data_dir()
_data_dir.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AVC_", env_file=".env")

    app_name: str = "AI Voice Cover"
    debug: bool = False

    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = _data_dir
    upload_dir: Path = _data_dir / "uploads"
    output_dir: Path = _data_dir / "output"
    voices_dir: Path = _data_dir / "voices"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker: str = "redis://localhost:6379/0"
    celery_backend: str = "redis://localhost:6379/1"

    # Audio
    sample_rate: int = 44100
    demucs_model: str = "htdemucs"

    # Device (auto-detect if empty)
    device: str = ""  # "cpu", "cuda:0", "xpu:0", "mps"
    compute_dtype: str = "float32"  # "float16" for GPU, "float32" for CPU

    # HuggingFace
    hf_token: str = ""  # For private models
    hf_cache_dir: str = ""  # Custom cache directory

    # Cloud API
    elevenlabs_api_key: str = ""
    fish_audio_api_key: str = ""

    # GPT-SoVITS
    gpt_sovits_url: str = "http://127.0.0.1:9880"

    # MiMo TTS
    mimo_api_key: str = ""

    # Training
    models_dir: Path = _data_dir / "models"

    # i18n
    default_language: str = "zh"  # "zh" or "en"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.voices_dir.mkdir(parents=True, exist_ok=True)
