from datetime import timedelta
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Count
from jobs.models import Job
from resumes.models import Resume
from applications.models import Application
from accounts.models import Profile
from matching.services import calculate_match_score

def index_view(request):
    if not request.user.is_authenticated:
        # Show public landing overview with product features
        total_public_jobs = Job.objects.filter(status=Job.Status.ACTIVE).count()
        recent_public_jobs = Job.objects.filter(status=Job.Status.ACTIVE)[:6]
        return render(request, 'dashboard/landing.html', {
            'total_jobs': total_public_jobs,
            'recent_jobs': recent_public_jobs,
        })

    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    default_resume = Resume.objects.filter(user=user, is_default=True).first()
    resumes_count = Resume.objects.filter(user=user).count()

    # Time boundaries
    seven_days_ago = timezone.now() - timedelta(days=7)

    # Job metrics
    all_jobs = Job.objects.filter(status=Job.Status.ACTIVE)
    total_jobs_count = all_jobs.count()
    new_jobs_count = all_jobs.filter(discovered_at__gte=seven_days_ago).count()

    # User applications
    user_apps = Application.objects.filter(user=user)
    total_applications = user_apps.count()
    saved_count = user_apps.filter(status=Application.Status.SAVED).count()
    ready_count = user_apps.filter(status=Application.Status.READY).count()
    review_required_count = user_apps.filter(status=Application.Status.REVIEW_REQUIRED).count()
    submitted_count = user_apps.filter(status=Application.Status.SUBMITTED).count()
    interview_count = user_apps.filter(status=Application.Status.INTERVIEW).count()
    rejected_count = user_apps.filter(status=Application.Status.REJECTED).count()

    # Compute matches for active jobs
    scored_jobs = []
    high_match_count = 0
    app_status_by_job = {app.job_id: app for app in user_apps}

    for job in all_jobs:
        match_info = calculate_match_score(job, profile, default_resume)
        score = match_info['total_score']
        if score >= 65:
            high_match_count += 1
        scored_jobs.append({
            'job': job,
            'score': score,
            'match_info': match_info,
            'application': app_status_by_job.get(job.id),
        })

    # Sort descending by score
    scored_jobs.sort(key=lambda x: x['score'], reverse=True)
    top_matched_jobs = scored_jobs[:6]

    # Recent application activity
    recent_applications = user_apps.select_related('job', 'resume').order_by('-updated_at')[:5]

    # Profile readiness score
    profile_checklist = [
        bool(profile.full_name),
        bool(profile.preferred_job_titles),
        bool(profile.skills),
        bool(profile.preferred_locations),
        bool(profile.years_of_experience > 0),
        bool(default_resume),
    ]
    readiness_percentage = round((sum(profile_checklist) / len(profile_checklist)) * 100)

    context = {
        'total_jobs_count': total_jobs_count,
        'new_jobs_count': new_jobs_count,
        'high_match_count': high_match_count,
        'total_applications': total_applications,
        'saved_count': saved_count,
        'ready_count': ready_count,
        'review_required_count': review_required_count,
        'submitted_count': submitted_count,
        'interview_count': interview_count,
        'rejected_count': rejected_count,
        'top_matched_jobs': top_matched_jobs,
        'recent_applications': recent_applications,
        'profile': profile,
        'default_resume': default_resume,
        'resumes_count': resumes_count,
        'readiness_percentage': readiness_percentage,
    }

    return render(request, 'dashboard/index.html', context)
