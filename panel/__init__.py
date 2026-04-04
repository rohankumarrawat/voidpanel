
# Ensure the Celery app is loaded when Django starts
# so the @shared_task decorator works in all apps.
from panel.celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)
