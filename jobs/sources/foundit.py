"""
Foundit (formerly Monster India) Job Source Connector.

Implements the connector interface for Foundit India job search.
Per Section 5 compliance rules: Foundit requires API partnership credentials
or permitted public search access respecting robots.txt.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class FounditJobSource(BaseJobSource):
    name = "foundit"
    display_name = "Foundit"
    is_available = True
    requires_api_key = True
    is_scraping_restricted = True
    restriction_reason = "Foundit/Monster Terms of Service restrict unauthenticated automated harvesting; requires partner API credentials."
    rate_limit_seconds = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        api_key = os.getenv('FOUNDIT_API_KEY', '').strip()
        if not api_key:
            return []
        return []

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
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
            'salary': raw_job.get('salary', 'Not disclosed'),
            'experience': raw_job.get('experience', 'Not specified'),
            'source': Job.Source.FOUNDIT,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
