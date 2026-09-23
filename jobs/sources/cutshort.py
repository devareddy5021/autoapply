"""
Cutshort Job Source Connector.

Implements the connector interface for Cutshort India tech & data hiring platform.
Per Section 5 compliance rules: Cutshort Terms of Service require employer/candidate
authentication; connector provides compliant API interface.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class CutshortJobSource(BaseJobSource):
    name = "cutshort"
    display_name = "Cutshort"
    is_available = True
    requires_api_key = True
    is_scraping_restricted = True
    restriction_reason = "Cutshort platform requires authentication and prohibits unauthorized automation; integration relies on partner API."
    rate_limit_seconds = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        api_key = os.getenv('CUTSHORT_API_KEY', '').strip()
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
            'salary': raw_job.get('salary', 'Market Rate'),
            'experience': raw_job.get('experience', '1 - 4 yrs'),
            'source': Job.Source.CUTSHORT,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
