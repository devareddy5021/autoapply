"""
Job Freshness Policy Service for JobAutoApply (Milestone 3).

Applies freshness rules without deleting historical records:
- Tracks first_seen_at and last_seen_at
- Deactivates jobs older than FRESHNESS_EXPIRY_DAYS without source updates
- Preserves all historical job and application records
"""

from datetime import timedelta
from django.utils import timezone
from jobs.models import Job

# Default freshness window: 30 days of inactivity before marking inactive
FRESHNESS_EXPIRY_DAYS = 30


def apply_freshness_policy(expiry_days: int = FRESHNESS_EXPIRY_DAYS) -> int:
    """
    Marks jobs as is_active=False if they have not been seen for over expiry_days.
    Historical records and application links are never deleted.
    Returns the count of deactivated jobs.
    """
    cutoff = timezone.now() - timedelta(days=expiry_days)
    stale_jobs = Job.objects.filter(is_active=True, last_seen_at__lt=cutoff)
    count = stale_jobs.count()
    stale_jobs.update(is_active=False)
    return count
