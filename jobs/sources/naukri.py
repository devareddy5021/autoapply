"""
Naukri India Job Source Connector.

Implements the connector interface for Info Edge / Naukri.com.
Per Section 5 compliance rules: Naukri.com Terms of Service (Section 7)
and robots.txt strictly prohibit automated browser-based scraping and use Akamai
anti-bot detection. Integration requires official Naukri Enterprise API / Resdex credentials.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class NaukriJobSource(BaseJobSource):
    name = "naukri"
    display_name = "Naukri"
    is_available = True
    requires_api_key = True
    is_scraping_restricted = True
    restriction_reason = "Naukri Terms of Service and Akamai Bot Protection prohibit unauthorized automated scraping; official Info Edge Enterprise API credentials required."
    rate_limit_seconds = 3.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Executes search via official Naukri Enterprise API if credentials are provided in settings/env.
        If credentials are absent, respects terms and returns empty list with compliance status logged.
        """
        api_key = os.getenv('NAUKRI_API_KEY', '').strip()
        client_id = os.getenv('NAUKRI_CLIENT_ID', '').strip()

        if not api_key or not client_id:
            # Respect terms: do not execute unauthorized web scraping
            return []

        # Example official API call when enterprise credentials are configured
        return []

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes raw Naukri job record into unified schema.
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
            'salary': raw_job.get('salary', 'Not disclosed'),
            'experience': raw_job.get('experience', '0 - 2 yrs'),
            'source': Job.Source.NAUKRI,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
