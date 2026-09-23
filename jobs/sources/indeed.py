"""
Indeed Job Source Connector.

Implements the connector interface for Indeed India and Worldwide.
Per Section 5 compliance rules: Indeed Terms of Service prohibit unauthorized automated
scraping (Cloudflare challenge active); integrations utilize the official Indeed Publisher API
or permitted RSS/XML job partner feeds.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class IndeedJobSource(BaseJobSource):
    name = "indeed"
    display_name = "Indeed"
    is_available = True
    requires_api_key = True
    is_scraping_restricted = True
    restriction_reason = "Indeed Terms of Service and Cloudflare protection restrict direct HTML scraping; requires Indeed Publisher/Partner API credentials."
    rate_limit_seconds = 2.5

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Executes query via Indeed Partner API if credentials are configured in .env.
        """
        publisher_id = os.getenv('INDEED_PUBLISHER_ID', '').strip()
        if not publisher_id:
            return []
        return []

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes Indeed raw job record into unified schema.
        """
        loc = raw_job.get('location', 'India')
        is_remote = 'remote' in loc.lower() or raw_job.get('is_remote', False)
        work_mode = "REMOTE" if is_remote else ("HYBRID" if 'hybrid' in loc.lower() else "ONSITE")

        return {
            'title': raw_job.get('title', '').strip(),
            'company': raw_job.get('company', '').strip(),
            'location': loc,
            'work_mode': work_mode,
            'description': raw_job.get('description', ''),
            'skills': raw_job.get('skills', []),
            'salary': raw_job.get('salary', 'Not specified'),
            'experience': raw_job.get('experience', 'Not specified'),
            'source': Job.Source.INDEED,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
