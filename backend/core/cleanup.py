"""Automatic cleanup of temporary/uploaded files."""
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Max age for temp files (in seconds)
_UPLOAD_MAX_AGE = 24 * 3600  # 24 hours for uploads
_OUTPUT_MAX_AGE = 7 * 24 * 3600  # 7 days for outputs
_TRAINING_MAX_AGE = 30 * 24 * 3600  # 30 days for training data


def _cleanup_dir(dir_path: Path, max_age: int, label: str) -> int:
    """Remove files older than max_age from directory. Returns count removed."""
    if not dir_path.exists():
        return 0

    now = time.time()
    removed = 0

    for item in dir_path.iterdir():
        try:
            if item.is_file():
                age = now - item.stat().st_mtime
                if age > max_age:
                    item.unlink()
                    removed += 1
            elif item.is_dir() and label == "training":
                # For training dirs, check the dir's mtime
                age = now - item.stat().st_mtime
                if age > max_age:
                    import shutil
                    shutil.rmtree(item)
                    removed += 1
        except (PermissionError, OSError) as e:
            logger.debug("Could not clean up %s: %s", item, e)

    if removed:
        logger.info("Cleaned up %d old %s files", removed, label)
    return removed


def cleanup_temp_files(upload_dir: Path, output_dir: Path):
    """Run cleanup on upload and output directories."""
    _cleanup_dir(upload_dir, _UPLOAD_MAX_AGE, "upload")
    _cleanup_dir(output_dir / "training", _TRAINING_MAX_AGE, "training")
    # Don't auto-delete completed outputs — user may want to keep those
    # Only clean up orphaned task dirs older than OUTPUT_MAX_AGE
    for task_dir in output_dir.iterdir():
        if not task_dir.is_dir():
            continue
        try:
            age = time.time() - task_dir.stat().st_mtime
            if age > _OUTPUT_MAX_AGE:
                import shutil
                shutil.rmtree(task_dir)
                logger.info("Cleaned up old output: %s", task_dir.name)
        except (PermissionError, OSError):
            pass
