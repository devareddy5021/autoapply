import re
import json
import html
import urllib.request
import logging
from typing import Optional, Tuple, Dict, Any, List
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Job, UserJob, normalize_job_url
from accounts.models import Profile
from resumes.models import Resume
from matching.services import calculate_match_score

logger = logging.getLogger(__name__)


def clean_html_text(raw_html: str) -> str:
    """Strips HTML tags and unescapes HTML entities to clean text."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_experience_requirements(title: str, text: str) -> Tuple[float, Optional[float]]:
    """
    Intelligently extracts required years of experience from job title and description.
    Supports formats like:
      - '3 - 5 years of experience' -> (3.0, 5.0)
      - '5+ years' -> (5.0, 8.0)
      - 'at least 2 years' -> (2.0, 5.0)
    Falls back to title seniority cues:
      - 'Principal / Architect / Director' -> (8.0, 15.0)
      - 'Lead / Staff' -> (7.0, 10.0)
      - 'Senior' -> (5.0, 8.0)
      - 'Mid / Intermediate' -> (3.0, 5.0)
      - 'Junior / Entry / Associate' -> (1.0, 3.0)
      - 'Intern / Trainee' -> (0.0, 1.0)
    """
    combined = f"{title} {text}".lower()

    # Pattern 1: Range '3 - 5 years' or '3 to 5 years'
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*years?', combined)
    if range_match:
        try:
            min_y = float(range_match.group(1))
            max_y = float(range_match.group(2))
            if 0 <= min_y <= 25 and min_y <= max_y <= 30:
                return min_y, max_y
        except ValueError:
            pass

    # Pattern 2: 'X+ years' or 'at least X years' or 'X years of experience'
    single_match = re.search(r'(?:at least|minimum|min|with)\s*(\d+(?:\.\d+)?)\+?\s*years?', combined)
    if not single_match:
        single_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of\s*)?(?:relevant|hands-on|industry|commercial|professional)?\s*experience', combined)

    if single_match:
        try:
            val = float(single_match.group(1))
            if 0 <= val <= 25:
                return val, round(val + 3.0, 1)
        except ValueError:
            pass

    # Title seniority heuristics
    title_lower = title.lower()
    if any(w in title_lower for w in ['principal', 'director', 'vp', 'head of', 'architect']):
        return 8.0, 15.0
    if any(w in title_lower for w in ['lead', 'staff', 'manager']):
        return 7.0, 10.0
    if any(w in title_lower for w in ['senior', 'sr.', 'sr ']):
        return 5.0, 8.0
    if any(w in title_lower for w in ['mid', 'intermediate']):
        return 3.0, 5.0
    if any(w in title_lower for w in ['junior', 'jr.', 'jr ', 'entry', 'associate', 'fresh']):
        return 1.0, 3.0
    if any(w in title_lower for w in ['intern', 'internship', 'trainee', 'student']):
        return 0.0, 1.0

    return 2.0, 5.0  # Industry standard default


class JobDeduplicationService:
    """
    Reusable deduplication engine to prevent duplicate Job records.
    Priority order:
    1. source + source_job_id
    2. normalized_url (when available)
    3. company_name + title + location match
    """
    @classmethod
    def find_duplicate(
        cls,
        company_name: str,
        title: str,
        location: str = '',
        external_url: str = '',
        source_job_id: str = '',
        source: str = ''
    ) -> Optional[Job]:
        # 1. Match source + source_job_id
        if source_job_id:
            query = Job.objects.filter(source_job_id=source_job_id.strip())
            if source:
                query = query.filter(source=source)
            existing = query.first()
            if existing:
                return existing

        # 2. Match normalized URL
        if external_url:
            norm_url = normalize_job_url(external_url)
            if norm_url:
                existing = Job.objects.filter(normalized_url=norm_url).first()
                if existing:
                    return existing

        # 3. Match normalized company, title, and location
        if company_name and title:
            query = Job.objects.filter(
                company_name__iexact=company_name.strip(),
                title__iexact=title.strip()
            )
            if location:
                query = query.filter(location__icontains=location.strip())
            return query.first()

        return None


def calculate_and_sync_user_job_match(user: User, job: Job) -> UserJob:
    """
    Calculates deterministic match score against user's profile and saves it to UserJob.
    """
    profile, _ = Profile.objects.get_or_create(user=user)
    default_resume = Resume.objects.filter(user=user, is_default=True).first()

    match_info = calculate_match_score(job, profile, default_resume)

    user_job, _ = UserJob.objects.get_or_create(
        user=user,
        job=job,
        defaults={
            'match_score': match_info['score'],
            'match_reasons': match_info.get('reasons', []),
            'missing_skills': match_info.get('missing_skills', []),
        }
    )
    user_job.match_score = match_info['score']
    user_job.match_reasons = match_info.get('reasons', [])
    user_job.missing_skills = match_info.get('missing_skills', [])
    user_job.save(update_fields=['match_score', 'match_reasons', 'missing_skills', 'updated_at'])

    return user_job


def toggle_save_job(user: User, job_id: int) -> Tuple[Optional[UserJob], bool]:
    """
    Toggles the is_saved status for a user and job.
    Returns (UserJob, is_saved_status).
    """
    job = Job.objects.filter(pk=job_id).first()
    if not job:
        return None, False

    user_job, created = UserJob.objects.get_or_create(user=user, job=job)
    user_job.is_saved = not user_job.is_saved
    user_job.save(update_fields=['is_saved', 'updated_at'])

    return user_job, user_job.is_saved


def toggle_ignore_job(user: User, job_id: int) -> Tuple[Optional[UserJob], bool]:
    """
    Toggles the is_ignored status for a user and job.
    Returns (UserJob, is_ignored_status).
    """
    job = Job.objects.filter(pk=job_id).first()
    if not job:
        return None, False

    user_job, created = UserJob.objects.get_or_create(user=user, job=job)
    user_job.is_ignored = not user_job.is_ignored
    user_job.save(update_fields=['is_ignored', 'updated_at'])

    return user_job, user_job.is_ignored


def create_manual_job(user: User, form_cleaned_data: Dict[str, Any]) -> Tuple[Job, bool, UserJob]:
    """
    Creates a job manually:
    1. Checks for duplicates using JobDeduplicationService.
    2. Saves the job.
    3. Calculates match against the user.
    4. Creates/updates UserJob.
    Returns (Job, is_duplicate, UserJob).
    """
    company_name = form_cleaned_data.get('company_name', '')
    title = form_cleaned_data.get('title', '')
    location = form_cleaned_data.get('location', '')
    external_url = form_cleaned_data.get('external_url', '')
    source_job_id = form_cleaned_data.get('source_job_id', '')
    source = form_cleaned_data.get('source', Job.Source.MANUAL)

    duplicate = JobDeduplicationService.find_duplicate(
        company_name=company_name,
        title=title,
        location=location,
        external_url=external_url,
        source_job_id=source_job_id,
        source=source
    )

    if duplicate:
        user_job = calculate_and_sync_user_job_match(user, duplicate)
        return duplicate, True, user_job

    job = Job.objects.create(**form_cleaned_data)
    user_job = calculate_and_sync_user_job_match(user, job)

    return job, False, user_job


def fetch_and_sync_real_jobs(user: Optional[User] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Fetches real live job listings from public APIs (Remotive and Arbeitnow),
    parses their experience requirements, skills, and details, and saves them
    into the database using JobDeduplicationService.
    """
    created_count = 0
    updated_count = 0
    total_scanned = 0
    errors = []

    # 1. Fetch from Remotive (Software Dev Remote Jobs)
    try:
        req = urllib.request.Request(
            f'https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}',
            headers={'User-Agent': 'Mozilla/5.0 (JobAutoApply Agent)'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            remotive_jobs = data.get('jobs', [])
            for rj in remotive_jobs:
                total_scanned += 1
                title = rj.get('title', '').strip()
                company = rj.get('company_name', '').strip()
                if not title or not company:
                    continue

                location = rj.get('candidate_required_location', '').strip() or 'Remote'
                url = rj.get('url', '').strip()
                source_job_id = f"REMOTIVE-{rj.get('id')}"
                raw_desc = rj.get('description', '')
                clean_desc = clean_html_text(raw_desc)
                skills_list = rj.get('tags', [])
                skills_str = ", ".join(skills_list) if skills_list else ""
                salary_str = rj.get('salary', '')

                exp_min, exp_max = parse_experience_requirements(title, clean_desc)

                # Check duplicate
                existing = JobDeduplicationService.find_duplicate(
                    company_name=company,
                    title=title,
                    location=location,
                    external_url=url,
                    source_job_id=source_job_id,
                    source=Job.Source.OTHER
                )

                if existing:
                    existing.last_seen_at = timezone.now()
                    existing.is_active = True
                    if not existing.skills and skills_str:
                        existing.skills = skills_str
                    existing.save(update_fields=['last_seen_at', 'is_active', 'skills', 'updated_at'])
                    updated_count += 1
                    target_job = existing
                else:
                    target_job = Job.objects.create(
                        title=title[:255],
                        company_name=company[:255],
                        location=location[:255],
                        work_mode=Job.WorkMode.REMOTE,
                        employment_type=Job.EmploymentType.FULL_TIME if 'contract' not in (rj.get('job_type') or '').lower() else Job.EmploymentType.CONTRACT,
                        description=clean_desc[:5000],
                        requirements=f"Experience required: {exp_min:g}+ years. Tech stack: {skills_str}",
                        experience_min=exp_min,
                        experience_max=exp_max,
                        skills=skills_str[:500],
                        salary_text=salary_str[:150] if salary_str else "",
                        external_url=url,
                        source=Job.Source.OTHER,
                        source_job_id=source_job_id,
                        is_active=True
                    )
                    created_count += 1

                if user and user.is_authenticated:
                    calculate_and_sync_user_job_match(user, target_job)

    except Exception as e:
        logger.error(f"Error fetching from Remotive: {e}")
        errors.append(f"Remotive: {str(e)}")

    # 2. Fetch from Arbeitnow (Tech / Engineering Jobs)
    try:
        req = urllib.request.Request(
            'https://www.arbeitnow.com/api/job-board-api',
            headers={'User-Agent': 'Mozilla/5.0 (JobAutoApply Agent)'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            arbeit_jobs = data.get('data', [])

            tech_keywords = ['developer', 'engineer', 'python', 'software', 'backend', 'frontend', 'data', 'cloud', 'devops']
            tech_jobs = [
                aj for aj in arbeit_jobs
                if any(kw in (aj.get('title', '') + ' ' + ' '.join(aj.get('tags', []))).lower() for kw in tech_keywords)
            ][:limit]

            for aj in tech_jobs:
                total_scanned += 1
                title = aj.get('title', '').strip()
                company = aj.get('company_name', '').strip()
                if not title or not company:
                    continue

                location = aj.get('location', '').strip() or 'Remote'
                url = aj.get('url', '').strip()
                slug = aj.get('slug', '')
                source_job_id = f"ARBEITNOW-{slug}" if slug else ""
                raw_desc = aj.get('description', '')
                clean_desc = clean_html_text(raw_desc)
                skills_list = aj.get('tags', [])
                skills_str = ", ".join(skills_list) if skills_list else ""

                exp_min, exp_max = parse_experience_requirements(title, clean_desc)

                work_mode = Job.WorkMode.REMOTE if aj.get('remote') else Job.WorkMode.HYBRID

                existing = JobDeduplicationService.find_duplicate(
                    company_name=company,
                    title=title,
                    location=location,
                    external_url=url,
                    source_job_id=source_job_id,
                    source=Job.Source.OTHER
                )

                if existing:
                    existing.last_seen_at = timezone.now()
                    existing.is_active = True
                    existing.save(update_fields=['last_seen_at', 'is_active', 'updated_at'])
                    updated_count += 1
                    target_job = existing
                else:
                    target_job = Job.objects.create(
                        title=title[:255],
                        company_name=company[:255],
                        location=location[:255],
                        work_mode=work_mode,
                        employment_type=Job.EmploymentType.FULL_TIME,
                        description=clean_desc[:5000],
                        requirements=f"Experience required: {exp_min:g}+ years. Tech stack: {skills_str}",
                        experience_min=exp_min,
                        experience_max=exp_max,
                        skills=skills_str[:500],
                        external_url=url,
                        source=Job.Source.OTHER,
                        source_job_id=source_job_id,
                        is_active=True
                    )
                    created_count += 1

                if user and user.is_authenticated:
                    calculate_and_sync_user_job_match(user, target_job)

    except Exception as e:
        logger.error(f"Error fetching from Arbeitnow: {e}")
        errors.append(f"Arbeitnow: {str(e)}")

    return {
        'created': created_count,
        'updated': updated_count,
        'total_scanned': total_scanned,
        'errors': errors
    }

