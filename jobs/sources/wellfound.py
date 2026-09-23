"""
Wellfound (formerly AngelList Talent) Source Connector.

Implements the connector interface for Wellfound startup data roles.
Per Section 5 compliance rules: Wellfound utilizes Cloudflare protection;
integrations require Wellfound API / partner access token.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class WellfoundJobSource(BaseJobSource):
    name = "wellfound"
    display_name = "Wellfound"
    is_available = True
    requires_api_key = True
    is_scraping_restricted = True
    restriction_reason = "Wellfound Terms of Service and Cloudflare challenge prohibit unauthenticated scraping; requires GraphQL/REST API token."
    rate_limit_seconds = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        api_token = os.getenv('WELLFOUND_API_TOKEN', '').strip()
        if not api_token:
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
            'salary': raw_job.get('salary', 'Equity + Salary'),
            'experience': raw_job.get('experience', '1 - 3 yrs'),
            'source': Job.Source.WELLFOUND,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
