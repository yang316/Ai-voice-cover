"""FFmpeg utilities — finds bundled or system ffmpeg."""
import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """Find ffmpeg binary. Prefers bundled version, falls back to PATH.

    Search order:
    1. PyInstaller frozen bundle (sys._MEIPASS / sys.executable parent)
    2. Sidecar bundle (relative to project root)
    3. System PATH
    """
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

    # 1. PyInstaller frozen bundle
    if getattr(sys, 'frozen', False):
        meipass = Path(getattr(sys, '_MEIPASS', ''))
        candidates = [meipass / exe, meipass / "bin" / exe]
        # Also check next to the executable
        candidates.append(Path(sys.executable).parent / exe)
        candidates.append(Path(sys.executable).parent / "bin" / exe)
        for c in candidates:
            if c.exists():
                logger.debug("ffmpeg found at (frozen): %s", c)
                return str(c)

    # 2. Sidecar bundle — walk up from this file
    base = Path(__file__).parent.parent.parent  # backend/core -> backend -> project root
    candidates = [
        base / "sidecar" / "bin" / exe,
        base / "bin" / exe,
        base / "ffmpeg",
        base / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.exists():
            logger.debug("ffmpeg found at (sidecar): %s", c)
            return str(c)

    # 3. System PATH
    system = shutil.which("ffmpeg")
    if system:
        logger.debug("ffmpeg found at (PATH): %s", system)
        return system

    raise FileNotFoundError(
        "ffmpeg not found. Place ffmpeg in sidecar/bin/, project bin/, or add to PATH."
    )
