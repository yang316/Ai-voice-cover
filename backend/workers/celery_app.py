"""Celery application configuration."""
from celery import Celery

from backend.config import settings

celery = Celery(
    "ai_voice_cover",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery.autodiscover_tasks(["backend.workers"])
