"""
Internshala Job & Internship Source Connector for JobAutoApply (Milestone 3).

Connects to Internshala India public job and internship listings
to fetch real live student, fresher, data, and software opportunities
across Indian tech hubs (Bengaluru, Hyderabad, Pune, Delhi NCR, Mumbai, etc.)
and Work From Home / Remote roles without requiring an API key.
"""

import re
import html
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .base import BaseJobSource
from jobs.models import Job


class InternshalaJobSource(BaseJobSource):
    name = "internshala"
    display_name = "Internshala"
    is_available = True
    requires_api_key = False
    is_scraping_restricted = False
    rate_limit_seconds = 1.5

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Searches Internshala public listings for matching tech internships and fresher jobs in India / Remote.
        """
        clean_query = (query or 'python').strip().lower()
        # Normalize search keyword to clean alphanumeric slug
        slug = re.sub(r'[^a-z0-9]+', '-', clean_query).strip('-') or 'python'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-IN,en;q=0.9',
        }

        urls_to_try = [
            f"https://internshala.com/internships/keywords-{slug}/",
            f"https://internshala.com/jobs/keywords-{slug}/",
        ]

        if remote:
            urls_to_try = [
                f"https://internshala.com/internships/work-from-home-{slug}-internships/",
                f"https://internshala.com/internships/keywords-{slug}/",
            ]

        raw_jobs = []
        seen_urls = set()

        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    page_html = resp.read().decode('utf-8', errors='ignore')

                cards = page_html.split('class="individual_internship')[1:]
                for card in cards:
                    t_m = re.search(r'class="job-title-href"[^>]*>\s*(.*?)\s*</a>', card, re.DOTALL)
                    co_m = (
                        re.search(r'class="company-name"[^>]*>\s*(.*?)\s*</p>', card, re.DOTALL) or
                        re.search(r'class="company_name"[^>]*>\s*(.*?)\s*</div>', card, re.DOTALL)
                    )
                    u_m = re.search(r'href="(/internship/detail/[^"]+|/job/detail/[^"]+)"', card)
                    loc_m = re.search(r'class="row-1-item locations"[^>]*>.*?<span>\s*(.*?)\s*</span>', card, re.DOTALL)
                    st_m = re.search(r'class=[\'"]stipend[\'"][^>]*>\s*(.*?)\s*</span>', card, re.DOTALL)
                    desc_m = re.search(r'class="about_job"[^>]*>.*?class="text">\s*(.*?)\s*</div>', card, re.DOTALL)

                    if t_m and u_m:
                        full_url = "https://internshala.com" + u_m.group(1).strip()
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        title = html.unescape(re.sub(r'<[^>]+>', '', t_m.group(1))).strip()
                        comp = html.unescape(re.sub(r'<[^>]+>', '', co_m.group(1))).strip() if co_m else 'Tech Startup'
                        loc = html.unescape(re.sub(r'<[^>]+>', '', loc_m.group(1))).strip() if loc_m else 'India'
                        stipend = html.unescape(re.sub(r'<[^>]+>', '', st_m.group(1))).strip() if st_m else 'Stipend provided'
                        desc = html.unescape(re.sub(r'<[^>]+>', ' ', desc_m.group(1))).strip() if desc_m else f"Role: {title} at {comp}. Location: {loc}."

                        # Extract Job ID
                        id_m = re.search(r'(\d+)$', full_url)
                        job_id = id_m.group(1) if id_m else str(hash(full_url))

                        raw_jobs.append({
                            'title': title,
                            'company': comp,
                            'location': loc,
                            'url': full_url,
                            'source_job_id': f"INTERNSHALA-{job_id}",
                            'description': desc[:4000],
                            'salary': stipend,
                            'is_remote': remote or 'work from home' in loc.lower() or 'remote' in loc.lower(),
                        })

                        if len(raw_jobs) >= 25:
                            break
            except Exception:
                continue

            if len(raw_jobs) >= 25:
                break

        return raw_jobs

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes Internshala record into unified schema.
        """
        loc = raw_job.get('location', 'India')
        is_remote = raw_job.get('is_remote', False) or 'work from home' in loc.lower() or 'remote' in loc.lower()
        work_mode = "REMOTE" if is_remote else ("HYBRID" if 'hybrid' in loc.lower() else "ONSITE")

        title = raw_job.get('title', '').strip()
        title_lower = title.lower()

        skills = []
        if 'python' in title_lower:
            skills.extend(['Python', 'Django', 'FastAPI'])
        if 'data' in title_lower or 'analyst' in title_lower:
            skills.extend(['Python', 'SQL', 'Data Analytics', 'Excel'])
        elif 'machine learning' in title_lower or 'ai' in title_lower:
            skills.extend(['Python', 'Machine Learning', 'TensorFlow', 'PyTorch'])
        elif 'web' in title_lower or 'developer' in title_lower or 'frontend' in title_lower:
            skills.extend(['JavaScript', 'HTML/CSS', 'React', 'Python'])
        else:
            skills.extend(['Python', 'Software Engineering', 'Problem Solving'])

        clean_loc = "India (Remote)" if is_remote else (loc or "India")

        return {
            'title': title,
            'company': raw_job.get('company', '').strip(),
            'location': clean_loc,
            'work_mode': work_mode,
            'employment_type': Job.EmploymentType.INTERNSHIP,
            'description': raw_job.get('description', ''),
            'skills': list(dict.fromkeys(skills)),
            'salary': raw_job.get('salary', 'Stipend provided'),
            'experience': '0 - 1 yrs (Fresher / Intern)',
            'source': Job.Source.INTERNSHALA,
            'source_job_id': raw_job.get('source_job_id', ''),
            'url': raw_job.get('url', ''),
            'posted_at': timezone.now().isoformat(),
        }
