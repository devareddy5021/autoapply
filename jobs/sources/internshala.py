"""
Internshala Job & Internship Source Connector.

Implements the connector interface for Internshala India data roles,
specializing in Data Engineering Intern, Data Analytics Intern, and Entry-Level Trainees.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class InternshalaJobSource(BaseJobSource):
    name = "internshala"
    display_name = "Internshala"
    is_available = True
    requires_api_key = False
    is_scraping_restricted = True
    restriction_reason = "Internshala Terms of Service restrict unauthenticated bulk automated extraction; connector requires permitted feed / partner access."
    rate_limit_seconds = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        # Integration hook for Internshala partner feed
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
            'skills': raw_job.get('skills', ['Python', 'SQL', 'Data Analytics']),
            'salary': raw_job.get('salary', 'Stipend provided'),
            'experience': raw_job.get('experience', '0 - 1 yrs (Fresher / Intern)'),
            'source': Job.Source.INTERNSHALA,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': raw_job.get('posted_at') or timezone.now().isoformat(),
        }
