"""
Remotive Job Source Connector for JobAutoApply (Milestone 3).

Connects to Remotive's official public REST API (https://remotive.com/api/remote-jobs)
to fetch 100% real live remote developer and data opportunities with genuine direct URLs.
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class RemotiveJobSource(BaseJobSource):
    name = "remotive"
    display_name = "Remotive"
    is_available = True
    requires_api_key = False
    is_scraping_restricted = False
    rate_limit_seconds = 1.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Queries Remotive's public remote jobs API.
        """
        params = {}
        if query:
            params['search'] = query.strip()
        params['limit'] = 100

        url = f"https://remotive.com/api/remote-jobs?{urllib.parse.urlencode(params)}"
        headers = {
            'User-Agent': 'JobAutoApply/1.0 (Contact: aggregator@autoapply.local)',
            'Accept': 'application/json',
        }

        raw_jobs = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_jobs = data.get('jobs', [])
        except Exception:
            # Fallback gracefully if network times out
            pass

        return raw_jobs

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes Remotive job into standard schema.
        """
        import html
        import re

        raw_desc = raw_job.get('description', '')
        clean_desc = html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc))
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()

        candidate_loc = raw_job.get('candidate_required_location', '') or 'Worldwide'
        job_id = str(raw_job.get('id', ''))

        emp_type_raw = (raw_job.get('job_type') or '').lower()
        if 'part_time' in emp_type_raw:
            emp_type = Job.EmploymentType.PART_TIME
        elif 'contract' in emp_type_raw:
            emp_type = Job.EmploymentType.CONTRACT
        elif 'intern' in emp_type_raw:
            emp_type = Job.EmploymentType.INTERNSHIP
        else:
            emp_type = Job.EmploymentType.FULL_TIME

        return {
            'title': raw_job.get('title', '').strip(),
            'company': raw_job.get('company_name', '').strip(),
            'location': f"Remote ({candidate_loc})",
            'work_mode': 'REMOTE',
            'employment_type': emp_type,
            'description': clean_desc[:4000],
            'skills': raw_job.get('tags', [])[:8],
            'salary': raw_job.get('salary', 'Competitive / Disclosed on site') or 'Not disclosed',
            'experience': '1 - 5 yrs',
            'source': Job.Source.REMOTIVE,
            'source_job_id': f"REMOTIVE-{job_id}",
            'url': raw_job.get('url', '').strip(),
            'posted_at': raw_job.get('publication_date') or timezone.now().isoformat(),
        }
