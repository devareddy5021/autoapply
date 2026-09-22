from typing import Optional, Tuple, Dict, Any
from django.contrib.auth.models import User
from .models import Job, UserJob, normalize_job_url
from accounts.models import Profile
from resumes.models import Resume
from matching.services import calculate_match_score

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
