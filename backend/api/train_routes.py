"""Training API routes."""
import re
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.training.trainer import (
    TrainingConfig,
    TrainingStatus,
    TrainingProgress,
    DataPreparer,
    FeatureExtractor,
    RVCTrainer,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory training tasks with JSON persistence
_training_tasks: dict[str, TrainingProgress] = {}
_persist_dir = settings.output_dir / "training"
_persist_dir.mkdir(parents=True, exist_ok=True)

_MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB per audio file
_ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


def _save_progress(task_id: str, progress: TrainingProgress):
    """Persist training progress to disk."""
    import json
    data = {
        "task_id": task_id,
        "status": progress.status.value,
        "epoch": progress.epoch,
        "total_epochs": progress.total_epochs,
        "loss": progress.loss,
        "message": progress.message,
        "model_path": progress.model_path,
        "stage_pct": progress.stage_pct,
    }
    path = _persist_dir / task_id / "progress.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning("Failed to persist progress for %s: %s", task_id, e)


def _load_persisted_tasks():
    """Load persisted training tasks on startup."""
    import json
    if not _persist_dir.exists():
        return
    for task_dir in _persist_dir.iterdir():
        progress_file = task_dir / "progress.json"
        if not progress_file.exists():
            continue
        try:
            with open(progress_file) as f:
                data = json.load(f)
            task_id = data.get("task_id", task_dir.name)
            _training_tasks[task_id] = TrainingProgress(
                status=TrainingStatus(data.get("status", "pending")),
                total_epochs=data.get("total_epochs", 0),
                message=data.get("message", ""),
            )
            _training_tasks[task_id].epoch = data.get("epoch", 0)
            _training_tasks[task_id].loss = data.get("loss", 0.0)
            _training_tasks[task_id].model_path = data.get("model_path")
            _training_tasks[task_id].stage_pct = data.get("stage_pct", 0)
        except Exception as e:
            logger.warning("Failed to load progress from %s: %s", progress_file, e)


# Load on import
_load_persisted_tasks()


class TrainingRequest(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=64)
    epoch: int = Field(default=200, ge=10, le=1000)
    batch_size: int = Field(default=4, ge=1, le=32)
    learning_rate: float = Field(default=1e-4, gt=0)
    f0_method: str = Field(default="rmvpe")
    sample_rate: int = Field(default=40000)
    version: str = Field(default="v2")


class TrainingResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/train", response_model=TrainingResponse)
async def start_training(
    model_name: str = Form(...),
    epoch: int = Form(200),
    batch_size: int = Form(4),
    learning_rate: float = Form(1e-4),
    f0_method: str = Form("rmvpe"),
    sample_rate: int = Form(40000),
    version: str = Form("v2"),
    audio_files: list[UploadFile] = File(...),
):
    """Start a new voice model training."""
    if not audio_files:
        raise HTTPException(400, "No audio files uploaded")

    # Validate model_name: alphanumeric with hyphens/underscores, no path traversal
    if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$', model_name):
        raise HTTPException(400, "model_name can only contain letters, numbers, hyphens, underscores, and Chinese characters")
    if '..' in model_name or '/' in model_name or '\\' in model_name:
        raise HTTPException(400, "Invalid model_name")

    task_id = uuid.uuid4().hex[:12]
    work_dir = settings.output_dir / "training" / task_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded audio files with validation
    audio_paths = []
    uploads_dir = work_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    for f in audio_files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in _ALLOWED_AUDIO_EXTS:
            continue
        content = await f.read()
        if len(content) > _MAX_AUDIO_SIZE:
            raise HTTPException(413, f"Audio file '{f.filename}' too large (max 100MB)")
        if len(content) < 1024:  # Skip files smaller than 1KB
            continue
        save_path = uploads_dir / f"{uuid.uuid4().hex[:8]}{ext}"
        with open(save_path, "wb") as fp:
            fp.write(content)
        audio_paths.append(save_path)

    if not audio_paths:
        raise HTTPException(400, "No valid audio files (supported: wav, mp3, flac, ogg, m4a)")

    config = TrainingConfig(
        model_name=model_name,
        sample_rate=sample_rate,
        epoch=epoch,
        batch_size=batch_size,
        learning_rate=learning_rate,
        f0_method=f0_method,
        version=version,
    )

    _training_tasks[task_id] = TrainingProgress(
        status=TrainingStatus.PENDING,
        total_epochs=epoch,
        message=f"Training queued with {len(audio_paths)} audio files",
    )

    # Start training in background
    asyncio.create_task(_run_training(task_id, audio_paths, config, work_dir))

    return TrainingResponse(
        task_id=task_id,
        status=TrainingStatus.PENDING.value,
        message=f"Training started with {len(audio_paths)} audio files",
    )


async def _run_training(task_id: str, audio_paths: list[Path], config: TrainingConfig, work_dir: Path):
    """Background training task."""
    progress = _training_tasks[task_id]

    def _persist():
        _save_progress(task_id, progress)

    try:
        # Step 1: Prepare data (0-15% overall)
        progress.status = TrainingStatus.PREPARING
        progress.message = "Preparing training data..."
        _persist()

        preparer = DataPreparer(work_dir)

        def on_prepare(pct, msg):
            progress.stage_pct = pct
            progress.message = msg

        data_dir = await preparer.prepare(audio_paths, config.sample_rate, on_progress=on_prepare)

        # Step 2: Extract features (15-35% overall)
        progress.status = TrainingStatus.EXTRACTING
        progress.stage_pct = 0
        progress.message = "Extracting HuBERT features..."
        _persist()

        extractor = FeatureExtractor(work_dir, config.f0_method)

        def on_extract(msg):
            progress.message = msg
            # Parse "HuBERT: 3/10" style messages to get progress
            try:
                parts = msg.split(":")[-1].strip().split("/")
                progress.stage_pct = int(parts[0]) / int(parts[1]) * 100
            except (ValueError, IndexError):
                pass

        model_dir = await extractor.extract(data_dir, config.sample_rate, config.pitch_guidance, on_extract)

        # Step 3: Train (35-100% overall)
        progress.status = TrainingStatus.TRAINING
        progress.stage_pct = 0
        progress.message = "Training model..."
        _persist()

        trainer = RVCTrainer(work_dir, config)

        def on_progress(epoch, total, loss):
            progress.epoch = epoch
            progress.total_epochs = total
            progress.loss = loss
            progress.stage_pct = epoch / total * 100
            progress.message = f"Training: epoch {epoch}/{total}, loss={loss:.6f}"
            # Persist every 10 epochs to avoid excessive I/O
            if epoch % 10 == 0 or epoch == total:
                _persist()

        model_path = await trainer.train(model_dir, on_progress=on_progress)

        # Copy model to voices directory
        voices_dir = settings.voices_dir / config.model_name
        voices_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        dest = voices_dir / model_path.name
        shutil.copy2(str(model_path), str(dest))

        progress.status = TrainingStatus.COMPLETED
        progress.message = f"Training complete! Model saved to {dest}"
        progress.model_path = str(dest)
        _persist()
        logger.info(f"Training {task_id} complete: {dest}")

    except Exception as e:
        progress.status = TrainingStatus.FAILED
        progress.message = f"Training failed: {str(e)}"
        _persist()
        logger.error(f"Training {task_id} failed: {e}", exc_info=True)


@router.get("/train/{task_id}")
async def get_training_status(task_id: str):
    """Get training task status."""
    if task_id not in _training_tasks:
        raise HTTPException(404, "Training task not found")

    p = _training_tasks[task_id]

    # Weighted overall progress: preparing 0-15%, extracting 15-35%, training 35-100%
    if p.status == TrainingStatus.PREPARING:
        overall_pct = p.stage_pct * 0.15
    elif p.status == TrainingStatus.EXTRACTING:
        overall_pct = 15 + p.stage_pct * 0.20
    elif p.status == TrainingStatus.TRAINING:
        overall_pct = 35 + p.stage_pct * 0.65
    elif p.status == TrainingStatus.COMPLETED:
        overall_pct = 100
    else:
        overall_pct = 0

    return {
        "task_id": task_id,
        "status": p.status.value,
        "epoch": p.epoch,
        "total_epochs": p.total_epochs,
        "loss": p.loss,
        "message": p.message,
        "model_path": p.model_path,
        "progress_pct": round(overall_pct),
    }


@router.get("/train")
async def list_training_tasks():
    """List all training tasks."""
    results = []
    for task_id, p in _training_tasks.items():
        if p.status == TrainingStatus.PREPARING:
            overall_pct = p.stage_pct * 0.15
        elif p.status == TrainingStatus.EXTRACTING:
            overall_pct = 15 + p.stage_pct * 0.20
        elif p.status == TrainingStatus.TRAINING:
            overall_pct = 35 + p.stage_pct * 0.65
        elif p.status == TrainingStatus.COMPLETED:
            overall_pct = 100
        else:
            overall_pct = 0

        results.append({
            "task_id": task_id,
            "status": p.status.value,
            "epoch": p.epoch,
            "total_epochs": p.total_epochs,
            "loss": p.loss,
            "message": p.message,
            "progress_pct": round(overall_pct),
        })
    return results


@router.get("/train/download/{task_id}")
async def download_trained_model(task_id: str):
    """Download trained model file."""
    if task_id not in _training_tasks:
        raise HTTPException(404, "Training task not found")

    progress = _training_tasks[task_id]

    if progress.status != TrainingStatus.COMPLETED:
        raise HTTPException(400, f"Training not completed. Status: {progress.status.value}")

    if not progress.model_path:
        raise HTTPException(404, "Model file not found")

    model_path = Path(progress.model_path)
    if not model_path.exists():
        raise HTTPException(404, "Model file does not exist on disk")

    # Return model file
    return FileResponse(
        path=str(model_path),
        media_type="application/octet-stream",
        filename=f"{model_path.stem}_{task_id}.pth",
        headers={
            "Content-Disposition": f'attachment; filename="{model_path.stem}_{task_id}.pth"'
        }
    )

