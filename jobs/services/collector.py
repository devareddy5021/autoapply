"""
Job Collection Service for JobAutoApply (Milestone 3).

Orchestrates multi-source data job aggregation:
1. Iterates over configured sources with rate limiting and isolated error handling
2. Normalizes raw jobs into standardized schema
3. Validates required attributes (title, company, location/remote, source, url)
4. Filters geography strictly for India & Remote via location_classifier
5. Filters domain strictly for Data roles via job_classifier
6. Applies 4-tier deduplication via JobDeduplicationService
7. Saves/updates canonical Job records with multi-source link preservation
8. Computes and caches profile match scores for registered users
9. Logs detailed audit metrics into JobSyncLog
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

from jobs.models import Job, JobSyncLog, normalize_job_url
from jobs.sources import get_source_connector, get_all_connectors, BaseJobSource
from jobs.services.location_classifier import classify_location
from jobs.services.job_classifier import classify_job, parse_experience_requirements
from jobs.services.deduplication import JobDeduplicationService, generate_content_hash
from accounts.models import Profile
from resumes.models import Resume
from matching.services import calculate_match_score

logger = logging.getLogger(__name__)

# Configurable Search Queries - Prioritizing Students, Freshers & Entry-Level Tech Roles
DEFAULT_DATA_QUERIES = getattr(
    settings,
    'JOB_AGGREGATOR_QUERIES',
    [
        'Internship',
        'Machine Learning Intern',
        'Data Engineering Intern',
        'Software Engineer Intern',
        'Python Intern',
        'Graduate Engineer Trainee',
        'Fresher Software Engineer',
        'Junior Python Developer',
        'Junior Data Analyst',
        'Junior Data Engineer',
        'Associate Software Engineer',
        'Data Engineer',
        'Software Engineer',
        'Python Developer',
        'Full Stack Developer',
        'Data Analyst',
    ]
)

DEFAULT_INDIA_LOCATIONS = getattr(
    settings,
    'JOB_AGGREGATOR_INDIA_LOCATIONS',
    [
        'Bengaluru',
        'Hyderabad',
        'Pune',
        'Gurugram',
        'Noida',
        'Mumbai',
        'Chennai',
        'Delhi NCR',
    ]
)


class JobCollector:
    """
    Main job aggregation orchestrator.
    """

    def __init__(self, queries: Optional[List[str]] = None, user: Optional[User] = None):
        self.queries = queries or DEFAULT_DATA_QUERIES[:5]  # Default to top 5 queries for performance
        self.user = user

    def validate_raw_job(self, norm_job: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates required attributes before processing (Section 9).
        Required: title, company, location OR remote indicator, source, url.
        """
        title = (norm_job.get('title') or '').strip()
        company = (norm_job.get('company') or '').strip()
        location = (norm_job.get('location') or '').strip()
        work_mode = (norm_job.get('work_mode') or '').strip()
        source = (norm_job.get('source') or '').strip()
        url = (norm_job.get('url') or '').strip()

        if not title:
            return False, "Missing title"
        if not company:
            return False, "Missing company"
        if not location and work_mode != 'REMOTE':
            return False, "Missing location and remote indicator"
        if not source:
            return False, "Missing source"
        if not url and not norm_job.get('source_job_id'):
            return False, "Missing url and source_job_id"

        return True, ""

    def process_normalized_job(self, norm_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single normalized job through validation, geography filter,
        role filter, deduplication, and database persistence.
        """
        # 1. Validation
        is_valid, reason = self.validate_raw_job(norm_job)
        if not is_valid:
            return {'status': 'rejected', 'reason': f"Validation: {reason}"}

        title = norm_job['title']
        company = norm_job['company']
        location = norm_job.get('location', '')
        work_mode = norm_job.get('work_mode', 'ONSITE')
        description = norm_job.get('description', '')
        skills_list = norm_job.get('skills', [])
        source = norm_job.get('source', Job.Source.OTHER)
        source_job_id = norm_job.get('source_job_id', '')
        external_url = norm_job.get('url', '')

        # 2. Geography Classification (Section 10)
        loc_res = classify_location(
            location=location,
            work_mode=work_mode,
            description=description,
            title=title
        )
        if not loc_res['is_accepted']:
            return {'status': 'rejected', 'reason': f"Geography rejected: {loc_res['location_type']}"}

        # 3. Domain Role Classification (Section 11 & 12)
        role_res = classify_job(
            title=title,
            description=description,
            skills=skills_list
        )
        if not role_res['is_accepted']:
            return {'status': 'rejected', 'reason': f"Role rejected: {role_res['category']}"}

        # 4. Deduplication & Cross-Source Merging (Section 14)
        content_hash = generate_content_hash(company, title, location, description)

        existing_job = JobDeduplicationService.find_duplicate(
            company_name=company,
            title=title,
            location=location,
            external_url=external_url,
            source_job_id=source_job_id,
            source=source,
            content_hash=content_hash,
            description=description
        )

        if existing_job:
            # Duplicate found: merge source and refresh timestamps
            JobDeduplicationService.register_or_merge_source(
                job=existing_job,
                source=source,
                external_url=external_url,
                source_job_id=source_job_id
            )
            # Sync user match if user attached
            if self.user and self.user.is_authenticated:
                self._sync_user_match(self.user, existing_job)
            return {'status': 'duplicate', 'job': existing_job}

        # 5. Create Canonical Job Record
        skills_str = ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list)
        exp_min, exp_max = parse_experience_requirements(title, description)
        emp_type = norm_job.get('employment_type')
        if not emp_type or emp_type == Job.EmploymentType.FULL_TIME:
            if any(it in title.lower() for it in ['intern', 'internship', 'trainee', 'student']):
                emp_type = Job.EmploymentType.INTERNSHIP

        new_job = Job.objects.create(
            title=title[:255],
            company_name=company[:255],
            location=location[:255],
            work_mode=work_mode,
            employment_type=emp_type or Job.EmploymentType.FULL_TIME,
            experience_min=exp_min,
            experience_max=exp_max,
            job_category=role_res['category'],
            category_confidence=role_res['confidence'],
            country=loc_res['country'],
            is_india=loc_res['is_india'],
            is_remote=loc_res['is_remote'],
            location_type=loc_res['location_type'],
            matched_keywords=role_res['matched_keywords'],
            description=description,
            requirements=norm_job.get('requirements', ''),
            skills=skills_str[:500],
            salary_text=norm_job.get('salary', '')[:150],
            source=source,
            source_job_id=source_job_id[:150],
            external_url=external_url,
            content_hash=content_hash,
            source_urls=[{
                'source': source,
                'url': external_url,
                'source_job_id': source_job_id,
                'discovered_at': timezone.now().isoformat(),
            }],
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            is_active=True
        )

        # 6. Profile Matching for User
        if self.user and self.user.is_authenticated:
            self._sync_user_match(self.user, new_job)

        return {'status': 'new', 'job': new_job}

    def _sync_user_match(self, user: User, job: Job):
        """Calculates and updates user match score."""
        from jobs.models import UserJob
        profile, _ = Profile.objects.get_or_create(user=user)
        resume = Resume.objects.filter(user=user, is_default=True).first()
        match_info = calculate_match_score(job, profile, resume)

        uj, _ = UserJob.objects.get_or_create(
            user=user,
            job=job,
            defaults={
                'match_score': match_info['score'],
                'match_reasons': match_info.get('reasons', []),
                'missing_skills': match_info.get('missing_skills', []),
            }
        )
        uj.match_score = match_info['score']
        uj.match_reasons = match_info.get('reasons', [])
        uj.missing_skills = match_info.get('missing_skills', [])
        uj.save(update_fields=['match_score', 'match_reasons', 'missing_skills', 'updated_at'])

    def collect_from_source(self, connector: BaseJobSource) -> JobSyncLog:
        """
        Runs collection for a specific connector with failure isolation and metrics logging.
        """
        sync_log = JobSyncLog.objects.create(
            source=connector.display_name,
            started_at=timezone.now(),
            status=JobSyncLog.Status.RUNNING
        )

        jobs_found = 0
        jobs_new = 0
        jobs_updated = 0
        jobs_duplicate = 0
        jobs_rejected = 0
        error_msg = ""

        total_queries = 0
        failed_queries = 0
        last_error = ""

        try:
            for query in self.queries[:3]:  # Efficient queries per pass
                # Search India locations
                for loc in ['India', 'Bengaluru', 'Remote']:
                    is_remote = (loc == 'Remote')
                    total_queries += 1
                    try:
                        raw_jobs = connector.search(query=query, location=loc, remote=is_remote)
                    except Exception as exc:
                        failed_queries += 1
                        last_error = str(exc)
                        logger.warning(f"Error querying {connector.name} for '{query}' in '{loc}': {exc}")
                        continue

                    for rj in raw_jobs:
                        jobs_found += 1
                        try:
                            norm = connector.normalize_job(rj)
                            res = self.process_normalized_job(norm)
                            status = res.get('status')
                            if status == 'new':
                                jobs_new += 1
                            elif status == 'duplicate':
                                jobs_duplicate += 1
                            elif status == 'rejected':
                                jobs_rejected += 1
                            elif status == 'updated':
                                jobs_updated += 1
                        except Exception as e:
                            jobs_rejected += 1

                    # Respect connector rate limit
                    if connector.rate_limit_seconds > 0:
                        time.sleep(min(0.5, connector.rate_limit_seconds))

            if failed_queries >= total_queries and total_queries > 0:
                sync_log.status = JobSyncLog.Status.FAILED
                error_msg = last_error
            elif failed_queries > 0:
                sync_log.status = JobSyncLog.Status.PARTIAL
                error_msg = f"{failed_queries}/{total_queries} queries failed: {last_error}"
            else:
                sync_log.status = JobSyncLog.Status.SUCCESS
        except Exception as exc:
            error_msg = str(exc)
            sync_log.status = JobSyncLog.Status.FAILED
            logger.error(f"Collection failure on source {connector.name}: {exc}")

        sync_log.completed_at = timezone.now()
        sync_log.jobs_found = jobs_found
        sync_log.jobs_new = jobs_new
        sync_log.jobs_updated = jobs_updated
        sync_log.jobs_duplicate = jobs_duplicate
        sync_log.jobs_rejected = jobs_rejected
        sync_log.error_message = error_msg
        sync_log.save()

        return sync_log

    def collect_all_sources(self) -> List[JobSyncLog]:
        """
        Runs collection across all registered connectors with failure isolation.
        A failure in one source does NOT halt others (Section 27).
        """
        logs = []
        connectors = get_all_connectors()
        for conn in connectors:
            try:
                log = self.collect_from_source(conn)
                logs.append(log)
            except Exception as e:
                # Isolate failure and continue
                fail_log = JobSyncLog.objects.create(
                    source=conn.display_name,
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    status=JobSyncLog.Status.FAILED,
                    error_message=str(e)
                )
                logs.append(fail_log)
        return logs
