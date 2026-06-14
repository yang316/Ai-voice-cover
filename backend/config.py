"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Voice Cover"
    debug: bool = False

    base_dir: Path = Path(__file__).parent.parent
    upload_dir: Path = base_dir / "uploads"
    output_dir: Path = base_dir / "output"
    voices_dir: Path = base_dir / "voices"

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

    # i18n
    default_language: str = "zh"  # "zh" or "en"

    class Config:
        env_prefix = "AVC_"
        env_file = ".env"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.voices_dir.mkdir(parents=True, exist_ok=True)
