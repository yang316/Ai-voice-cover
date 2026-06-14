"""Training API routes."""
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
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

# In-memory training tasks (use DB in production)
_training_tasks: dict[str, TrainingProgress] = {}


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

    task_id = uuid.uuid4().hex[:12]
    work_dir = settings.output_dir / "training" / task_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded audio files
    audio_paths = []
    uploads_dir = work_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    for f in audio_files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix or ".wav"
        save_path = uploads_dir / f"{uuid.uuid4().hex[:8]}{ext}"
        content = await f.read()
        with open(save_path, "wb") as fp:
            fp.write(content)
        audio_paths.append(save_path)

    if not audio_paths:
        raise HTTPException(400, "No valid audio files")

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

    try:
        # Step 1: Prepare data
        progress.status = TrainingStatus.PREPARING
        progress.message = "Preparing training data..."

        preparer = DataPreparer(work_dir)
        data_dir = await preparer.prepare(audio_paths, config.sample_rate)

        # Step 2: Extract features
        progress.status = TrainingStatus.EXTRACTING
        progress.message = "Extracting features..."

        extractor = FeatureExtractor(work_dir, config.f0_method)
        model_dir = await extractor.extract(data_dir, config.sample_rate, config.pitch_guidance)

        # Step 3: Train
        progress.status = TrainingStatus.TRAINING
        progress.message = "Training model..."

        trainer = RVCTrainer(work_dir, config)

        def on_progress(epoch, total, loss):
            progress.epoch = epoch
            progress.total_epochs = total
            progress.loss = loss
            progress.message = f"Training: epoch {epoch}/{total}, loss={loss:.6f}"

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
        logger.info(f"Training {task_id} complete: {dest}")

    except Exception as e:
        progress.status = TrainingStatus.FAILED
        progress.message = f"Training failed: {str(e)}"
        logger.error(f"Training {task_id} failed: {e}", exc_info=True)


@router.get("/train/{task_id}")
async def get_training_status(task_id: str):
    """Get training task status."""
    if task_id not in _training_tasks:
        raise HTTPException(404, "Training task not found")

    p = _training_tasks[task_id]
    return {
        "task_id": task_id,
        "status": p.status.value,
        "epoch": p.epoch,
        "total_epochs": p.total_epochs,
        "loss": p.loss,
        "message": p.message,
        "model_path": p.model_path,
        "progress_pct": round(p.epoch / max(p.total_epochs, 1) * 100),
    }


@router.get("/train")
async def list_training_tasks():
    """List all training tasks."""
    results = []
    for task_id, p in _training_tasks.items():
        results.append({
            "task_id": task_id,
            "status": p.status.value,
            "epoch": p.epoch,
            "total_epochs": p.total_epochs,
            "loss": p.loss,
            "message": p.message,
            "progress_pct": round(p.epoch / max(p.total_epochs, 1) * 100),
        })
    return results
