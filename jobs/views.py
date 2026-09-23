from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from .models import Job, UserJob, JobCategory, JobSyncLog
from .forms import JobForm
from . import selectors, services
from .sources import get_all_connectors, get_source_connector
from .tasks import trigger_sync_in_background
from applications.models import Application
from resumes.models import Resume


@login_required
def job_list_view(request):
    """
    Main Job Search & Discovery Dashboard (/jobs/).
    Displays only India & Remote Data-related opportunities with live metrics,
    multi-dimensional filtering, and server-side pagination.
    """
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    employment_type = request.GET.get('employment_type', '').strip()
    category = request.GET.get('category', '').strip()
    source = request.GET.get('source', '').strip()
    min_score_str = request.GET.get('min_score', '').strip()
    min_score = int(min_score_str) if min_score_str.isdigit() else None
    experience = request.GET.get('experience', '').strip()
    date_range = request.GET.get('date', '').strip()
    show_ignored = request.GET.get('show_ignored', '').lower() in ('true', '1', 'on')
    sort_by = request.GET.get('sort', 'newest').strip()

    # Query items using selector (strictly filters India + Remote and Data roles)
    items = selectors.filter_and_search_jobs(
        user=request.user,
        query=query,
        location=location,
        work_mode=work_mode,
        employment_type=employment_type,
        category=category,
        source=source,
        min_score=min_score,
        experience=experience,
        date_range=date_range,
        show_ignored=show_ignored,
        sort_by=sort_by
    )

    # Server-side pagination: 20 jobs per page
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Database statistics (Section 18)
    stats = selectors.get_dashboard_statistics(request.user)
    available_locations = selectors.get_distinct_locations()

    experience_choices = [
        ('', 'All Experience Levels'),
        ('0-1', 'Fresher / Entry (0 - 1 Yrs)'),
        ('1-3', 'Junior (1 - 3 Yrs)'),
        ('3-5', 'Mid-Level (3 - 5 Yrs)'),
        ('5-8', 'Senior (5 - 8 Yrs)'),
        ('8+', 'Lead / Staff (8+ Yrs)'),
    ]

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'total_count': len(items),
        'stats': stats,
        'available_locations': available_locations,
        'job_categories': JobCategory.choices,
        'work_modes': Job.WorkMode.choices,
        'employment_types': Job.EmploymentType.choices,
        'sources': Job.Source.choices,
        'experience_choices': experience_choices,
        # Active filter values
        'query': query,
        'selected_location': location,
        'selected_work_mode': work_mode,
        'selected_employment_type': employment_type,
        'selected_category': category,
        'selected_source': source,
        'selected_min_score': min_score_str,
        'selected_experience': experience,
        'selected_date': date_range,
        'show_ignored': show_ignored,
        'sort_by': sort_by,
    })


@login_required
def sources_dashboard_view(request):
    """
    Source Status Dashboard (/jobs/sources/).
    Displays connectors, compliance and availability status, last sync, jobs count,
    individual sync triggers, and sync audit logs.
    """
    connectors = get_all_connectors()
    sources_data = []

    for conn in connectors:
        last_log = JobSyncLog.objects.filter(source=conn.display_name).first()
        jobs_count = Job.objects.filter(source=conn.name.upper(), is_active=True).count()
        # Also count jobs where this source is recorded in source_urls
        # For simplicity, count direct source or from sync log
        if not jobs_count and last_log:
            jobs_count = last_log.jobs_found

        if conn.is_scraping_restricted and conn.requires_api_key:
            status_badge = "Restricted (API Required)"
            status_class = "warning"
        elif not conn.is_available:
            status_badge = "Unavailable"
            status_class = "danger"
        else:
            status_badge = "Active"
            status_class = "success"

        sources_data.append({
            'name': conn.name,
            'display_name': conn.display_name,
            'status': status_badge,
            'status_class': status_class,
            'is_available': conn.is_available,
            'is_restricted': conn.is_scraping_restricted,
            'restriction_reason': conn.restriction_reason,
            'last_sync': last_log.started_at if last_log else None,
            'last_status': last_log.status if last_log else 'Never',
            'jobs_count': jobs_count,
        })

    recent_logs = JobSyncLog.objects.all()[:20]

    return render(request, 'jobs/sources_status.html', {
        'sources_data': sources_data,
        'recent_logs': recent_logs,
    })


@login_required
@require_POST
def sync_source_view(request):
    """
    Dispatches collection for all sources or a single source in the background (Section 24).
    """
    source_name = request.POST.get('source', '').strip()
    trigger_sync_in_background(source_name=source_name or None, user_id=request.user.pk)

    if source_name:
        display = source_name.title()
        messages.success(request, f"Collection initiated for {display} in the background. Fresh jobs will appear shortly.")
    else:
        messages.success(request, "Collection initiated for all sources in the background. Fresh jobs will appear shortly.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'jobs:sources_status'
    return redirect(next_url)


@login_required
def job_detail_view(request, pk):
    """
    Detailed job view (/jobs/<id>/).
    Per Milestone 3:
    - Application automation is disabled.
    - Displays 'Open Original' button to visit the external job website manually.
    - Displays multi-source discovery links ('Found on: Naukri • LinkedIn').
    """
    job = get_object_or_404(Job, pk=pk)
    user_job = services.calculate_and_sync_user_job_match(request.user, job)

    match_info = {
        'score': user_job.match_score,
        'total_score': user_job.match_score,
        'reasons': user_job.match_reasons or [],
        'missing_skills': user_job.missing_skills or [],
    }

    application = Application.objects.filter(user=request.user, job=job).first()
    user_resumes = Resume.objects.filter(user=request.user)

    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'user_job': user_job,
        'match': match_info,
        'is_saved': user_job.is_saved,
        'is_ignored': user_job.is_ignored,
        'application': application,
        'user_resumes': user_resumes,
    })


@login_required
@require_POST
def job_save_toggle_view(request, pk):
    """Toggles is_saved status for a job."""
    user_job, is_saved = services.toggle_save_job(request.user, pk)
    if not user_job:
        return JsonResponse({'error': 'Job not found'}, status=404)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('format') == 'json':
        return JsonResponse({
            'success': True,
            'is_saved': is_saved,
            'message': 'Job saved to your list' if is_saved else 'Job removed from saved list'
        })

    msg = "Job saved to your saved jobs list." if is_saved else "Job removed from your saved list."
    messages.success(request, msg)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'jobs:list'
    return redirect(next_url)


@login_required
@require_POST
def job_ignore_toggle_view(request, pk):
    """Toggles is_ignored status for a job."""
    user_job, is_ignored = services.toggle_ignore_job(request.user, pk)
    if not user_job:
        return JsonResponse({'error': 'Job not found'}, status=404)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('format') == 'json':
        return JsonResponse({
            'success': True,
            'is_ignored': is_ignored,
            'message': 'Job ignored' if is_ignored else 'Job restored'
        })

    msg = "Job has been ignored and hidden from your default view." if is_ignored else "Job is no longer ignored."
    messages.info(request, msg)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'jobs:list'
    return redirect(next_url)


@login_required
def saved_jobs_view(request):
    """
    Dedicated view for Saved Jobs (/jobs/saved/).
    """
    saved_items = selectors.get_saved_jobs_for_user(request.user)

    paginator = Paginator(saved_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'jobs/saved_jobs.html', {
        'page_obj': page_obj,
        'total_count': len(saved_items),
    })


@login_required
def job_create_view(request):
    """Manual job creation view (/jobs/create/) for testing and manual additions."""
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job, is_dup, user_job = services.create_manual_job(request.user, form.cleaned_data)
            if is_dup:
                messages.warning(
                    request,
                    f"Note: A matching job listing at '{job.company_name}' already exists in the database (ID #{job.id})."
                )
            else:
                messages.success(request, f"Job '{job.title}' at {job.company_name} was successfully created!")
            return redirect('jobs:detail', pk=job.pk)
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = JobForm()

    return render(request, 'jobs/job_form.html', {
        'form': form,
        'title': 'Add Job Manually',
    })


@login_required
def job_delete_view(request, pk):
    """Deletes a job listing."""
    job = get_object_or_404(Job, pk=pk)
    title = job.title
    job.delete()
    messages.info(request, f"Job '{title}' has been removed.")
    return redirect('jobs:list')
