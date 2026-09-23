"""
4-Tier Job Deduplication Engine for JobAutoApply (Milestone 3).

Prevents cross-platform job duplication across Naukri, LinkedIn, Indeed,
Foundit, Internshala, Wellfound, Cutshort, and Instahyre.

Hierarchy:
  Level 1: Exact (source + source_job_id)
  Level 2: Canonical Normalized URL
  Level 3: Normalized Company + Normalized Title + Location
  Level 4: Content Hash (normalized company, title, core description tokens)

Maintains multi-source discovery records in job.source_urls so the user
sees a single canonical job with all platforms where it was discovered.
"""

import re
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from django.utils import timezone
from jobs.models import Job, normalize_job_url


def normalize_string(text: str) -> str:
    """Normalizes string: strips punctuation, extra whitespace, and converts to lowercase."""
    if not text:
        return ""
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return re.sub(r'\s+', ' ', cleaned).strip()


def normalize_title(title: str) -> str:
    """Normalizes job title by removing common noise words and brackets."""
    if not title:
        return ""
    # Remove contents inside parentheses/brackets: e.g. "Data Engineer (Immediate Joiner)" -> "Data Engineer"
    title_clean = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', title)
    title_clean = re.sub(r'\b(immediate joiner|urgent|hiring|fresher|remote|hybrid|full time|contract)\b', '', title_clean, flags=re.I)
    return normalize_string(title_clean)


def generate_content_hash(company_name: str, title: str, location: str = '', description: str = '') -> str:
    """
    Generates a deterministic 64-character SHA256 content hash for Level 4 similarity detection.
    """
    comp = normalize_string(company_name)
    tit = normalize_title(title)
    loc = normalize_string(location)
    desc_sample = normalize_string(description[:200]) if description else ""

    payload = f"{comp}|{tit}|{loc}|{desc_sample}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class JobDeduplicationService:
    """
    Multi-tier deduplication and source merging service.
    """

    @classmethod
    def find_duplicate(
        cls,
        company_name: str,
        title: str,
        location: str = '',
        external_url: str = '',
        source_job_id: str = '',
        source: str = '',
        content_hash: str = '',
        description: str = ''
    ) -> Optional[Job]:
        """
        Executes 4-tier deduplication check against existing active jobs.
        """
        # Level 1: Exact source + source_job_id
        if source_job_id:
            query = Job.objects.filter(source_job_id=source_job_id.strip())
            if source:
                query = query.filter(source=source)
            match_l1 = query.first()
            if match_l1:
                return match_l1

        # Level 2: Canonical Normalized URL
        if external_url:
            norm_url = normalize_job_url(external_url)
            if norm_url:
                match_l2 = Job.objects.filter(normalized_url=norm_url).first()
                if match_l2:
                    return match_l2

        # Level 3: Normalized Company + Normalized Title + Location
        norm_company = normalize_string(company_name)
        norm_t = normalize_title(title)

        if norm_company and norm_t:
            # Query candidate jobs with matching company
            candidates = Job.objects.filter(
                company_name__iexact=company_name.strip()
            )
            for cand in candidates:
                cand_norm_title = normalize_title(cand.title)
                if cand_norm_title == norm_t:
                    # Check location similarity or remote
                    if not location or not cand.location:
                        return cand
                    cand_loc = cand.location.lower()
                    target_loc = location.lower()
                    if (
                        target_loc in cand_loc or
                        cand_loc in target_loc or
                        'remote' in cand_loc or
                        'remote' in target_loc
                    ):
                        return cand

                    # Check meaningful location token overlap (e.g. 'bengaluru' in both 'Bengaluru, India' and 'Bengaluru, Karnataka, India')
                    cand_tokens = set(re.findall(r'\w+', cand_loc))
                    target_tokens = set(re.findall(r'\w+', target_loc))
                    generic_words = {'india', 'in', 'city', 'state', 'location', 'district', 'area'}
                    meaningful_overlap = (cand_tokens & target_tokens) - generic_words
                    if meaningful_overlap:
                        return cand

        # Level 4: SHA256 Content Hash
        target_hash = content_hash or generate_content_hash(company_name, title, location, description)
        if target_hash:
            match_l4 = Job.objects.filter(content_hash=target_hash).first()
            if match_l4:
                return match_l4

        return None

    @classmethod
    def register_or_merge_source(
        cls,
        job: Job,
        source: str,
        external_url: str,
        source_job_id: str = ''
    ) -> Job:
        """
        Appends source to job's source_urls if not already registered,
        updating last_seen_at timestamp.
        """
        if not job.source_urls:
            job.source_urls = []

        norm_incoming_url = normalize_job_url(external_url) if external_url else ""
        existing_sources = [s.get('source') for s in job.source_urls if isinstance(s, dict)]
        existing_urls = [normalize_job_url(s.get('url', '')) for s in job.source_urls if isinstance(s, dict)]

        # If incoming source or URL is not yet recorded, add it
        should_update = False
        if source and (source not in existing_sources or (norm_incoming_url and norm_incoming_url not in existing_urls)):
            job.source_urls.append({
                'source': source,
                'url': external_url,
                'source_job_id': source_job_id,
                'discovered_at': timezone.now().isoformat(),
            })
            should_update = True

        # Refresh last seen
        job.last_seen_at = timezone.now()
        job.is_active = True

        update_fields = ['last_seen_at', 'is_active', 'updated_at']
        if should_update:
            update_fields.append('source_urls')

        job.save(update_fields=update_fields)
        return job
