"""
Celery Configuration for JobAutoApply (Milestone 3).

Configures Celery tasks and Celery Beat scheduled job collection every 2 hours.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('jobautoapply')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configurable Beat Schedule (Section 25: Every 2 hours)
app.conf.beat_schedule = {
    'scheduled-job-collection-every-2-hours': {
        'task': 'jobs.tasks.sync_all_sources_task',
        'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
        'args': (),
    },
}
