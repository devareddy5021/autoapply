"""
LinkedIn Public Guest Job Search Connector.

Uses LinkedIn's public guest job search endpoints to retrieve live public
postings for India & Remote data roles without requiring login.
"""

import re
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class LinkedInJobSource(BaseJobSource):
    name = "linkedin"
    display_name = "LinkedIn"
    is_available = True
    rate_limit_seconds = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Queries LinkedIn's public job search API endpoint across pagination offsets.
        """
        import html as html_mod
        loc = location or ("India" if not remote else "Remote")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        raw_jobs = []
        seen_links = set()

        for start in [0, 25]:
            params = {
                'keywords': query,
                'location': loc,
                'f_TPR': 'r604800',  # Past week
                'position': 1,
                'pageNum': 0,
                'start': start,
            }
            if remote:
                params['f_WT'] = '2'  # Remote filter code on LinkedIn

            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urllib.parse.urlencode(params)}"

            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html_text = resp.read().decode('utf-8', errors='ignore')

                    # Extract job cards via base-card splitting
                    cards = html_text.split('<div class="base-card')[1:]
                    for card in cards:
                        link_m = re.search(r'href="([^"]*linkedin\.com/jobs/view/[^"]+)"', card)
                        title_m = re.search(r'<h3 class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', card, re.DOTALL)
                        comp_m = re.search(r'<h4 class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*(.*?)\s*</a>', card, re.DOTALL)
                        if not comp_m:
                            comp_m = re.search(r'<h4 class="base-search-card__subtitle"[^>]*>\s*(.*?)\s*</h4>', card, re.DOTALL)
                        loc_m = re.search(r'<span class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', card, re.DOTALL)

                        if title_m and comp_m and link_m:
                            title_clean = html_mod.unescape(re.sub(r'<[^>]+>', '', title_m.group(1))).strip()
                            comp_clean = html_mod.unescape(re.sub(r'<[^>]+>', '', comp_m.group(1))).strip()
                            loc_clean = html_mod.unescape(re.sub(r'<[^>]+>', '', loc_m.group(1))).strip() if loc_m else (location or "India")
                            raw_link = html_mod.unescape(link_m.group(1)).strip()
                            clean_url = raw_link.split('?')[0]

                            if clean_url in seen_links:
                                continue
                            seen_links.add(clean_url)

                            # Extract Job ID
                            id_m = re.search(r'/view/.*?(\d+)', clean_url) or re.search(r'-(\d+)$', clean_url)
                            job_id = id_m.group(1) if id_m else clean_url.split('/')[-1]

                            raw_jobs.append({
                                'title': title_clean,
                                'company': comp_clean,
                                'location': loc_clean,
                                'url': clean_url,
                                'job_id': job_id,
                                'source_job_id': f"LI-{job_id}",
                                'description': f"Live job opening for {title_clean} at {comp_clean} in {loc_clean}.",
                                'is_remote': remote or 'remote' in loc_clean.lower(),
                            })
            except Exception:
                pass

        return raw_jobs

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes LinkedIn job posting into standard schema.
        """
        loc = raw_job.get('location', 'India')
        is_remote = raw_job.get('remote', False) or 'remote' in loc.lower()
        work_mode = "REMOTE" if is_remote else ("HYBRID" if 'hybrid' in loc.lower() else "ONSITE")

        title = raw_job.get('title', '').strip()
        title_lower = title.lower()

        skills = []
        if 'python' in title_lower:
            skills.extend(['Python', 'Django', 'FastAPI'])
        if 'data engineer' in title_lower or 'spark' in title_lower:
            skills.extend(['Python', 'SQL', 'Apache Spark', 'ETL', 'Airflow'])
        elif 'data analyst' in title_lower or 'analytics' in title_lower:
            skills.extend(['SQL', 'Power BI', 'Excel', 'Tableau', 'Python'])
        elif 'data science' in title_lower or 'machine learning' in title_lower or 'ai' in title_lower:
            skills.extend(['Python', 'Machine Learning', 'PyTorch', 'TensorFlow', 'SQL'])
        elif 'react' in title_lower or 'frontend' in title_lower:
            skills.extend(['React', 'JavaScript', 'TypeScript', 'HTML/CSS', 'Next.js'])
        elif 'java' in title_lower:
            skills.extend(['Java', 'Spring Boot', 'Microservices', 'SQL'])
        elif 'devops' in title_lower or 'cloud' in title_lower or 'sre' in title_lower:
            skills.extend(['Docker', 'Kubernetes', 'AWS', 'CI/CD', 'Terraform'])
        elif 'full stack' in title_lower:
            skills.extend(['Python', 'React', 'JavaScript', 'SQL', 'Node.js'])
        else:
            skills = ['Python', 'SQL', 'Git', 'Software Development']

        return {
            'title': title,
            'company': raw_job.get('company', '').strip(),
            'location': loc,
            'work_mode': work_mode,
            'description': f"Role: {title} at {raw_job.get('company')}. Location: {loc}.",
            'skills': list(dict.fromkeys(skills)),
            'salary': 'Competitive (India standard)',
            'experience': '1 - 4 yrs',
            'source': Job.Source.LINKEDIN,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': timezone.now().isoformat(),
        }
