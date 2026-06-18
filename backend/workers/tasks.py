"""Celery tasks for voice cover processing."""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.workers.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=1)
def process_cover(
    self,
    task_id: str,
    input_path: str,
    voice_id: str,
    backend_type: str,
    pitch_shift: int = 0,
    denoise: bool = True,
    api_key: str | None = None,
):
    """Process a voice cover task."""
    from backend.api.routes import update_task
    from backend.api.schemas import TaskStatus, TaskStep
    from backend.backends.factory import ComputeBackendType, create_backend
    from backend.config import settings
    from backend.core.pipeline import VoiceCoverPipeline

    try:
        update_task(task_id, status=TaskStatus.PROCESSING, step=TaskStep.SEPARATING, progress=5)

        # Create backend
        bt = ComputeBackendType(backend_type)
        backend = create_backend(bt, api_key=api_key)

        # Create pipeline
        pipeline = VoiceCoverPipeline(backend=backend)

        # Progress callback
        def on_progress(step: str, pct: int):
            if "separat" in step.lower():
                task_step = TaskStep.SEPARATING
            elif "convert" in step.lower():
                task_step = TaskStep.CONVERTING
            elif "mix" in step.lower():
                task_step = TaskStep.MIXING
            else:
                task_step = TaskStep.COMPLETE
            update_task(task_id, status=TaskStatus.PROCESSING, step=task_step, progress=pct, message=step)

        # Run pipeline
        output_dir = settings.output_dir / task_id
        loop = asyncio.new_event_loop()
        final_path = loop.run_until_complete(
            pipeline.run(
                input_path=input_path,
                voice_id=voice_id,
                output_dir=output_dir,
                pitch_shift=pitch_shift,
                denoise=denoise,
                on_progress=on_progress,
            )
        )

        update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Cover completed!",
            output_file=str(final_path),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        update_task(
            task_id,
            status=TaskStatus.FAILED,
            message=str(e),
        )
        raise
