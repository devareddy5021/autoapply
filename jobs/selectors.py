from typing import Dict, Any, List, Optional
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Job, UserJob
from accounts.models import Profile
from resumes.models import Resume
from applications.models import Application
from matching.services import calculate_match_score

SORT_ALLOWED_MAPPING = {
    'newest': '-discovered_at',
    'oldest': 'discovered_at',
    'company_asc': 'company_name',
    'company_desc': '-company_name',
    'posted': '-posted_at',
}

def get_job_by_id(job_id: int) -> Optional[Job]:
    """Retrieves a single Job by primary key, or None if not found."""
    return Job.objects.filter(pk=job_id).first()

def get_distinct_locations() -> List[str]:
    """Returns a list of distinct, non-empty locations present in the database."""
    locations = (
        Job.objects.filter(is_active=True)
        .values_list('location', flat=True)
        .distinct()
    )
    clean_locations = sorted(list(set(loc.strip() for loc in locations if loc and loc.strip() and loc.strip().lower() != 'not specified')))
    return clean_locations

def get_dashboard_statistics(user: User) -> Dict[str, int]:
    """
    Computes dashboard metrics using actual database records:
    - Total Jobs: count of all active jobs
    - New Jobs: jobs discovered within the last 7 days
    - Saved Jobs: count of jobs saved by the user
    - High Match Jobs: count of jobs with match score >= 70% for the user
    - Applications: total application records tracked by user
    """
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    total_jobs = Job.objects.filter(is_active=True).count()
    new_jobs = Job.objects.filter(is_active=True, discovered_at__gte=seven_days_ago).count()

    if user and user.is_authenticated:
        saved_jobs = UserJob.objects.filter(user=user, is_saved=True, job__is_active=True).count()
        high_match_jobs = UserJob.objects.filter(user=user, match_score__gte=70, is_ignored=False, job__is_active=True).count()
        applications_count = Application.objects.filter(user=user).count()
    else:
        saved_jobs = 0
        high_match_jobs = 0
        applications_count = 0

    return {
        'total_jobs': total_jobs,
        'new_jobs': new_jobs,
        'saved_jobs': saved_jobs,
        'high_match_jobs': high_match_jobs,
        'applications_count': applications_count,
    }

def filter_and_search_jobs(
    user: User,
    query: str = '',
    location: str = '',
    work_mode: str = '',
    employment_type: str = '',
    source: str = '',
    min_score: Optional[int] = None,
    date_range: str = '',
    show_ignored: bool = False,
    sort_by: str = 'newest'
) -> List[Dict[str, Any]]:
    """
    Core selector for filtering, searching, and sorting jobs.
    Integrates user-specific state (saved, ignored, match score) while keeping business logic out of views.
    """
    qs = Job.objects.filter(is_active=True)

    # Search keyword across title, company, skills, location, description
    if query:
        query_stripped = query.strip()
        qs = qs.filter(
            Q(title__icontains=query_stripped) |
            Q(company_name__icontains=query_stripped) |
            Q(skills__icontains=query_stripped) |
            Q(location__icontains=query_stripped) |
            Q(description__icontains=query_stripped)
        )

    # Location filter
    if location:
        qs = qs.filter(location__icontains=location.strip())

    # Work mode filter
    if work_mode:
        qs = qs.filter(work_mode=work_mode.strip())

    # Employment type filter
    if employment_type:
        qs = qs.filter(employment_type=employment_type.strip())

    # Source filter
    if source:
        qs = qs.filter(source=source.strip())

    # Date posted/discovered filter
    now = timezone.now()
    if date_range == 'today':
        qs = qs.filter(discovered_at__gte=now - timedelta(days=1))
    elif date_range == '3days':
        qs = qs.filter(discovered_at__gte=now - timedelta(days=3))
    elif date_range == '7days':
        qs = qs.filter(discovered_at__gte=now - timedelta(days=7))
    elif date_range == '30days':
        qs = qs.filter(discovered_at__gte=now - timedelta(days=30))

    # User context & precomputed user_jobs map
    user_jobs_map: Dict[int, UserJob] = {}
    profile = None
    default_resume = None

    if user and user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=user)
        default_resume = Resume.objects.filter(user=user, is_default=True).first()

        user_jobs = UserJob.objects.filter(user=user, job__in=qs).select_related('job')
        user_jobs_map = {uj.job_id: uj for uj in user_jobs}

    # Prepare job items list with match information and state
    items: List[Dict[str, Any]] = []

    for job in qs:
        uj = user_jobs_map.get(job.id)

        # Ignore filter
        is_ignored = uj.is_ignored if uj else False
        if is_ignored and not show_ignored:
            continue

        is_saved = uj.is_saved if uj else False

        # Calculate or reuse match score
        if uj and uj.match_score > 0 and uj.match_reasons:
            match_info = {
                'score': uj.match_score,
                'total_score': uj.match_score,
                'reasons': uj.match_reasons,
                'missing_skills': uj.missing_skills or [],
            }
            score = uj.match_score
        elif profile:
            match_info = calculate_match_score(job, profile, default_resume)
            score = match_info['score']
            # Cache in UserJob if exists or create lazily
            if uj:
                uj.match_score = score
                uj.match_reasons = match_info.get('reasons', [])
                uj.missing_skills = match_info.get('missing_skills', [])
                uj.save(update_fields=['match_score', 'match_reasons', 'missing_skills', 'updated_at'])
            else:
                uj = UserJob.objects.create(
                    user=user,
                    job=job,
                    match_score=score,
                    match_reasons=match_info.get('reasons', []),
                    missing_skills=match_info.get('missing_skills', []),
                )
                user_jobs_map[job.id] = uj
        else:
            match_info = {'score': 0, 'total_score': 0, 'reasons': [], 'missing_skills': job.skills_list}
            score = 0

        # Min match score filter
        if min_score is not None and score < min_score:
            continue

        items.append({
            'job': job,
            'score': score,
            'match_info': match_info,
            'is_saved': is_saved,
            'is_ignored': is_ignored,
            'user_job': uj,
        })

    # Sorting using safe allowed-list mapping
    if sort_by == 'match':
        items.sort(key=lambda x: x['score'], reverse=True)
    elif sort_by == 'oldest':
        items.sort(key=lambda x: x['job'].discovered_at)
    elif sort_by == 'company_asc':
        items.sort(key=lambda x: (x['job'].company_name or '').lower())
    elif sort_by == 'company_desc':
        items.sort(key=lambda x: (x['job'].company_name or '').lower(), reverse=True)
    else:  # default 'newest'
        items.sort(key=lambda x: x['job'].discovered_at, reverse=True)

    return items

def get_saved_jobs_for_user(user: User) -> List[Dict[str, Any]]:
    """Retrieves all active jobs saved by the user."""
    if not user or not user.is_authenticated:
        return []

    profile, _ = Profile.objects.get_or_create(user=user)
    default_resume = Resume.objects.filter(user=user, is_default=True).first()

    user_jobs = (
        UserJob.objects.filter(user=user, is_saved=True, job__is_active=True)
        .select_related('job')
        .order_by('-updated_at')
    )

    saved_items = []
    for uj in user_jobs:
        job = uj.job
        if uj.match_score > 0 and uj.match_reasons:
            match_info = {
                'score': uj.match_score,
                'total_score': uj.match_score,
                'reasons': uj.match_reasons,
                'missing_skills': uj.missing_skills or [],
            }
        else:
            match_info = calculate_match_score(job, profile, default_resume)

        saved_items.append({
            'job': job,
            'score': match_info['score'],
            'match_info': match_info,
            'user_job': uj,
            'is_saved': True,
            'is_ignored': uj.is_ignored,
        })

    return saved_items
