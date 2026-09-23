"""
Jobs Services Package for JobAutoApply (Milestone 3).

Exposes all core services:
- Location classification
- Data domain classification
- 4-Tier deduplication
- Collector orchestrator
- Freshness tracking
- User actions & match synchronization
"""

from .location_classifier import classify_location
from .job_classifier import classify_job
from .deduplication import JobDeduplicationService, generate_content_hash, normalize_title, normalize_string
from .collector import JobCollector
from .freshness import apply_freshness_policy
from .user_actions import (
    calculate_and_sync_user_job_match,
    toggle_save_job,
    toggle_ignore_job,
    create_manual_job,
    clean_html_text,
    parse_experience_requirements,
    fetch_and_sync_real_jobs,
)

__all__ = [
    'classify_location',
    'classify_job',
    'JobDeduplicationService',
    'generate_content_hash',
    'normalize_title',
    'normalize_string',
    'JobCollector',
    'apply_freshness_policy',
    'calculate_and_sync_user_job_match',
    'toggle_save_job',
    'toggle_ignore_job',
    'create_manual_job',
    'clean_html_text',
    'parse_experience_requirements',
    'fetch_and_sync_real_jobs',
]
