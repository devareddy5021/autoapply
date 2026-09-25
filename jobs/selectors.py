import re
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

# User-prioritized Data & AI Roles (Main First, followed by other tech roles)
PRIORITIZED_ROLE_KEYWORDS = [
    'data engineer',
    'ai data engineer',
    'data platform engineer',
    'cloud data engineer',
    'data architect',
    'mlops',
    'data security engineer',
    'data governance',
    'data quality',
    'ai/ml',
    'data scientist',
    'analytics engineer',
    'decision scientist',
    'operations research',
    'knowledge engineer',
    'data annotation',
    'data labeling',
]

def get_role_priority(title: str) -> int:
    """Returns priority rank (0 is highest, 999 for next/others)."""
    t = (title or '').lower()
    for idx, kw in enumerate(PRIORITIZED_ROLE_KEYWORDS):
        if kw in t:
            return idx
    return 999

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
    Computes dashboard metrics using actual database records (Section 18):
    - India Data Jobs: count of active India data opportunities
    - Remote Data Jobs: count of active Remote data opportunities
    - New Today: jobs discovered within the past 24 hours
    - High Match (80%+): count of jobs with match score >= 80% for the user
    - Saved Jobs: count of jobs saved by the user
    """
    now = timezone.now()
    one_day_ago = now - timedelta(days=1)

    base_active_data_qs = Job.objects.filter(is_active=True).filter(
        Q(is_india=True) | Q(is_remote=True)
    )

    india_data_jobs = base_active_data_qs.filter(is_india=True).count()
    remote_data_jobs = base_active_data_qs.filter(is_remote=True).count()
    new_today = base_active_data_qs.filter(discovered_at__gte=one_day_ago).count()
    total_data_jobs = base_active_data_qs.count()

    if user and user.is_authenticated:
        saved_jobs = UserJob.objects.filter(user=user, is_saved=True, job__is_active=True).count()
        high_match_jobs = UserJob.objects.filter(
            user=user,
            match_score__gte=80,
            is_ignored=False,
            job__is_active=True
        ).count()
    else:
        saved_jobs = 0
        high_match_jobs = 0

    return {
        'total_jobs': total_data_jobs,
        'total_data_jobs': total_data_jobs,
        'india_data_jobs': india_data_jobs,
        'remote_data_jobs': remote_data_jobs,
        'new_today': new_today,
        'high_match_jobs': high_match_jobs,
        'saved_jobs': saved_jobs,
    }

def filter_and_search_jobs(
    user: User,
    query: str = '',
    location: str = '',
    work_mode: str = '',
    employment_type: str = '',
    category: str = '',
    source: str = '',
    min_score: Optional[int] = None,
    experience: str = '',
    date_range: str = '',
    show_ignored: bool = False,
    sort_by: str = 'newest',
    authenticity: str = ''
) -> List[Dict[str, Any]]:
    """
    Core selector for filtering, searching, and sorting jobs.
    Displays:
    - Active jobs
    - India OR Remote opportunities
    - Category filtering when selected
    - Authenticity / Fake / Agency filtering
    """
    qs = Job.objects.filter(is_active=True).filter(
        Q(is_india=True) | Q(is_remote=True)
    )

    # Category filter
    if category:
        qs = qs.filter(job_category=category.strip())

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

        # Also detect if query explicitly mentions years of experience (e.g. '3 years', '5 yrs')
        if not experience:
            exp_in_query = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs)', query_stripped, re.IGNORECASE)
            if exp_in_query:
                try:
                    target_exp = float(exp_in_query.group(1))
                    qs = qs.filter(
                        Q(experience_min__lte=target_exp + 1.0) &
                        (Q(experience_max__gte=target_exp - 1.0) | Q(experience_max__isnull=True))
                    )
                except ValueError:
                    pass

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

    # Years of experience filter
    if experience:
        exp_clean = experience.strip().lower()
        senior_title_pattern = r'\b(senior|sr\b|sr\.|lead|principal|architect|staff|manager|director|head|iii\b|level[\s\-_]*3|sde[\s\-_]*3|developer[\s\-_]*3|ii\b|level[\s\-_]*2|sde[\s\-_]*2)\b'
        if exp_clean in ('0-2', '0-1', 'entry', 'junior', 'fresher', 'intern'):
            max_limit = 1.5 if exp_clean == '0-1' else 2.5
            qs = qs.filter(
                experience_min__lte=2.0
            ).filter(
                Q(experience_max__lte=max_limit) | Q(experience_max__isnull=True, experience_min__lte=1.0)
            ).exclude(
                Q(title__iregex=senior_title_pattern)
            )
        elif exp_clean in ('1-3',):
            qs = qs.filter(
                Q(experience_min__lte=2.5) &
                (Q(experience_max__lte=4.0) | Q(experience_max__isnull=True))
            ).exclude(
                Q(title__iregex=r'\b(senior|sr\b|sr\.|lead|principal|architect|staff|manager|director|head|iii\b)\b')
            )
        elif exp_clean in ('3-5', 'mid'):
            qs = qs.filter(
                (Q(experience_min__gte=2.0, experience_min__lte=5.5) | Q(experience_max__gte=3.0, experience_max__lte=6.0)) &
                ~Q(title__iregex=r'\b(principal|architect|director|head|staff|lead)\b')
            )
        elif exp_clean in ('5-8', 'senior'):
            qs = qs.filter(
                Q(experience_min__gte=4.0, experience_min__lte=8.5) |
                Q(experience_max__gte=5.0, experience_max__lte=9.0) |
                Q(title__iregex=r'\b(senior|sr\b|sr\.|iii\b|level[\s\-_]*3|sde[\s\-_]*3)\b')
            )
        elif exp_clean in ('8+', 'lead', 'staff', 'principal'):
            qs = qs.filter(
                Q(experience_min__gte=7.5) |
                Q(experience_max__gte=8.0) |
                Q(title__iregex=r'\b(lead|staff|principal|architect|director|head|manager)\b')
            )
        else:
            range_m = re.match(r'^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$', exp_clean)
            if range_m:
                r_low = float(range_m.group(1))
                r_high = float(range_m.group(2))
                qs = qs.filter(
                    Q(experience_min__lte=r_high) &
                    (Q(experience_max__gte=r_low) | Q(experience_max__isnull=True))
                )
                if r_high <= 2.5:
                    qs = qs.exclude(Q(title__iregex=senior_title_pattern))
            else:
                try:
                    exp_num = float(exp_clean)
                    qs = qs.filter(
                        Q(experience_min__lte=exp_num) &
                        (Q(experience_max__gte=exp_num) | Q(experience_max__isnull=True) | Q(experience_max=0))
                    )
                except ValueError:
                    pass

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
        # Authenticity / Fake / Agency filter
        auth_info = job.authenticity_info
        if authenticity == 'verified' and not auth_info.get('is_verified'):
            continue
        elif authenticity == 'direct' and (auth_info.get('is_third_party') or auth_info.get('is_suspicious')):
            continue
        elif authenticity == 'no_suspicious' and auth_info.get('is_suspicious'):
            continue

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
            'authenticity': auth_info,
        })

    # Sorting with Prioritized Target Roles First (Main First, followed by other roles)
    if sort_by == 'match':
        items.sort(key=lambda x: (-x['score'], get_role_priority(x['job'].title), -x['job'].discovered_at.timestamp()))
    elif sort_by == 'oldest':
        items.sort(key=lambda x: (get_role_priority(x['job'].title), x['job'].discovered_at.timestamp()))
    elif sort_by == 'company_asc':
        items.sort(key=lambda x: (x['job'].company_name or '').lower())
    elif sort_by == 'company_desc':
        items.sort(key=lambda x: (x['job'].company_name or '').lower(), reverse=True)
    else:  # default 'newest'
        items.sort(key=lambda x: (get_role_priority(x['job'].title), -x['job'].discovered_at.timestamp()))

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
