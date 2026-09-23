"""
Background Collection Tasks for JobAutoApply (Milestone 3).

Executes source synchronization in background worker processes (Celery)
or background threads to ensure large collection operations NEVER run
inside a synchronous HTTP request (Section 24).
"""

import threading
import logging
from typing import Optional
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    # Graceful fallback decorator if celery is not installed in the active environment
    def shared_task(func):
        func.delay = lambda *args, **kwargs: trigger_threaded_sync(func, *args, **kwargs)
        return func


def run_sync_sync(source_name: Optional[str] = None, user_id: Optional[int] = None):
    """Executes collection synchronously."""
    from jobs.services.collector import JobCollector
    from jobs.sources import get_source_connector

    user = User.objects.filter(pk=user_id).first() if user_id else None
    collector = JobCollector(user=user)

    if source_name:
        connector = get_source_connector(source_name)
        if connector:
            collector.collect_from_source(connector)
        else:
            logger.error(f"Cannot sync unknown source: {source_name}")
    else:
        collector.collect_all_sources()


def trigger_threaded_sync(func, *args, **kwargs):
    """Spawns an asynchronous daemon thread for non-blocking execution."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


@shared_task
def sync_all_sources_task(user_id: Optional[int] = None):
    """Celery task to sync all job sources in background."""
    run_sync_sync(source_name=None, user_id=user_id)


@shared_task
def sync_single_source_task(source_name: str, user_id: Optional[int] = None):
    """Celery task to sync a specific job source in background."""
    run_sync_sync(source_name=source_name, user_id=user_id)


import sys

def trigger_sync_in_background(source_name: Optional[str] = None, user_id: Optional[int] = None):
    """
    Triggers source synchronization asynchronously.
    Prefers Celery task execution if configured, or launches an asynchronous
    worker thread so the HTTP response returns immediately without blocking.
    """
    if 'test' in sys.argv:
        # In test suite, avoid spawning background threads against sqlite test database
        return

    try:
        # Check if celery broker is active and can be used
        if source_name:
            sync_single_source_task.delay(source_name=source_name, user_id=user_id)
        else:
            sync_all_sources_task.delay(user_id=user_id)
    except Exception as exc:
        logger.info(f"Celery broker dispatch fallback to background thread: {exc}")
        if source_name:
            trigger_threaded_sync(run_sync_sync, source_name=source_name, user_id=user_id)
        else:
            trigger_threaded_sync(run_sync_sync, source_name=None, user_id=user_id)
