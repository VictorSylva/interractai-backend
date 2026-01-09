#!/bin/bash
# start.sh

# Start Celery worker in the background
# We use & to detach it so the script continues
echo "Starting Celery Worker..."
celery -A celery_app worker --loglevel=info &

# Start FastAPI application
# Render provides the PORT environment variable
echo "Starting Web Server..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
