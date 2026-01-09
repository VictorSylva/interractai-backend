import os
from celery import Celery
# Pre-load all models to populate SQLAlchemy registry for worker
from database.models import general, workflow, chat, crm

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "interact_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Explicitly import the module containing tasks
celery_app.conf.update(include=["services.workflow_engine"])
