"""
Arbeitnow Job Source Connector for JobAutoApply (Milestone 3).

Connects to Arbeitnow's free, public job board API (https://www.arbeitnow.com/api/job-board-api)
to fetch real tech, engineering, and remote opportunities without requiring an API key.
"""

import json
import re
import html
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class ArbeitnowJobSource(BaseJobSource):
    name = "arbeitnow"
    display_name = "Arbeitnow"
    is_available = True
    requires_api_key = False
    is_scraping_restricted = False
    rate_limit_seconds = 1.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Queries Arbeitnow public API. Filters by tech and query keywords.
        """
        url = "https://www.arbeitnow.com/api/job-board-api"
        headers = {
            'User-Agent': 'JobAutoApply/1.0 (Contact: aggregator@autoapply.local)',
            'Accept': 'application/json',
        }

        raw_jobs = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                all_jobs = data.get('data', [])

                query_lower = (query or '').strip().lower()
                for j in all_jobs:
                    title = j.get('title', '')
                    desc = j.get('description', '')
                    tags = " ".join(j.get('tags', []))
                    combined = f"{title} {tags} {desc}".lower()

                    if query_lower and query_lower not in combined:
                        continue

                    # If remote was requested, check remote flag or remote in location
                    is_rem = j.get('remote', False) or 'remote' in (j.get('location') or '').lower()
                    if remote and not is_rem:
                        continue

                    raw_jobs.append(j)
                    if len(raw_jobs) >= 50:
                        break
        except Exception:
            pass

        return raw_jobs

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes Arbeitnow job into standard schema.
        """
        raw_desc = raw_job.get('description', '')
        clean_desc = html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc))
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()

        loc = raw_job.get('location', '') or 'Remote'
        is_rem = raw_job.get('remote', False) or 'remote' in loc.lower()
        work_mode = "REMOTE" if is_rem else ("HYBRID" if 'hybrid' in loc.lower() else "ONSITE")

        job_types = [t.lower() for t in raw_job.get('job_types', [])]
        if any('part' in t for t in job_types):
            emp_type = Job.EmploymentType.PART_TIME
        elif any('contract' in t or 'freelance' in t for t in job_types):
            emp_type = Job.EmploymentType.CONTRACT
        elif any('intern' in t for t in job_types):
            emp_type = Job.EmploymentType.INTERNSHIP
        else:
            emp_type = Job.EmploymentType.FULL_TIME

        slug = raw_job.get('slug') or str(hash(raw_job.get('url', '')))

        return {
            'title': raw_job.get('title', '').strip(),
            'company': raw_job.get('company_name', '').strip(),
            'location': loc,
            'work_mode': work_mode,
            'employment_type': emp_type,
            'description': clean_desc[:4000],
            'skills': raw_job.get('tags', [])[:8],
            'salary': 'Competitive / Disclosed on site',
            'experience': '1 - 4 yrs',
            'source': Job.Source.ARBEITNOW,
            'source_job_id': f"ARBEITNOW-{slug}",
            'url': raw_job.get('url', '').strip(),
            'posted_at': timezone.now().isoformat(),
        }
