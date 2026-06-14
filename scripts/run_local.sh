#!/bin/bash
# Run the app locally without Docker
set -e

echo "Starting Redis..."
redis-server --daemonize yes --port 6379 --requirepass "" 2>/dev/null || true

echo "Starting Celery worker..."
celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1 &
WORKER_PID=$!

echo "Starting FastAPI server..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo ""
echo "========================================="
echo "  AI Voice Cover is running!"
echo "  http://localhost:8000"
echo "========================================="
echo ""
echo "Press Ctrl+C to stop"

trap "kill $WORKER_PID $API_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
