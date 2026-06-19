"""FFmpeg utilities — finds bundled or system ffmpeg."""
import shutil
import sys
from pathlib import Path


def get_ffmpeg_path() -> str:
    """Find ffmpeg binary. Prefers bundled version, falls back to PATH."""
    # Bundled in sidecar: sidecar/bin/ffmpeg(.exe)
    if sys.platform == "win32":
        bundled = Path(__file__).parent.parent.parent / "bin" / "ffmpeg.exe"
    else:
        bundled = Path(__file__).parent.parent.parent / "bin" / "ffmpeg"

    if bundled.exists():
        return str(bundled)

    # System PATH
    system = shutil.which("ffmpeg")
    if system:
        return system

    raise FileNotFoundError(
        "ffmpeg not found. Place ffmpeg.exe in the bin/ directory or add to PATH."
    )
