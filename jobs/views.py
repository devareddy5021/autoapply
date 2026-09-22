from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from .models import Job, UserJob
from .forms import JobForm
from . import selectors, services
from applications.models import Application
from resumes.models import Resume


@login_required
def job_list_view(request):
    """
    Main Job Search & Discovery Dashboard (/jobs/).
    Integrates live metrics, search query, multi-factor filtering, safe sorting,
    and server-side pagination (20 per page).
    """
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    employment_type = request.GET.get('employment_type', '').strip()
    source = request.GET.get('source', '').strip()
    min_score_str = request.GET.get('min_score', '').strip()
    min_score = int(min_score_str) if min_score_str.isdigit() else None
    experience = request.GET.get('experience', '').strip()
    date_range = request.GET.get('date', '').strip()
    show_ignored = request.GET.get('show_ignored', '').lower() in ('true', '1', 'on')
    sort_by = request.GET.get('sort', 'newest').strip()

    # Query items using selector
    items = selectors.filter_and_search_jobs(
        user=request.user,
        query=query,
        location=location,
        work_mode=work_mode,
        employment_type=employment_type,
        source=source,
        min_score=min_score,
        experience=experience,
        date_range=date_range,
        show_ignored=show_ignored,
        sort_by=sort_by
    )

    # Server-side pagination: exactly 20 jobs per page as requested
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Real database statistics
    stats = selectors.get_dashboard_statistics(request.user)
    available_locations = selectors.get_distinct_locations()

    experience_choices = [
        ('', 'All Experience Levels'),
        ('0-2', '0 - 2 Years (Entry / Junior)'),
        ('3-5', '3 - 5 Years (Mid-Level)'),
        ('5-8', '5 - 8 Years (Senior)'),
        ('8+', '8+ Years (Lead / Staff)'),
    ]

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'total_count': len(items),
        'stats': stats,
        'available_locations': available_locations,
        'work_modes': Job.WorkMode.choices,
        'employment_types': Job.EmploymentType.choices,
        'sources': Job.Source.choices,
        'experience_choices': experience_choices,
        # Active filter values
        'query': query,
        'selected_location': location,
        'selected_work_mode': work_mode,
        'selected_employment_type': employment_type,
        'selected_source': source,
        'selected_min_score': min_score_str,
        'selected_experience': experience,
        'selected_date': date_range,
        'show_ignored': show_ignored,
        'sort_by': sort_by,
    })


@login_required
@require_POST
def fetch_real_jobs_view(request):
    """Fetches real live jobs from external APIs and syncs with candidate profile."""
    limit = int(request.POST.get('limit', 30))
    result = services.fetch_and_sync_real_jobs(user=request.user, limit=limit)

    msg = f"Synced real live jobs! Added {result['created']} new opportunities."
    if result['updated']:
        msg += f" Refreshed {result['updated']} active postings."
    messages.success(request, msg)

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'jobs:list'
    return redirect(next_url)



@login_required
def job_detail_view(request, pk):
    """
    Detailed job view (/jobs/<id>/).
    Displays complete specifications, explainable match score with reasons & missing skills,
    and actions: Save, Ignore, Open Original, and Prepare Application (disabled placeholder).
    """
    job = get_object_or_404(Job, pk=pk)

    # Sync and get user-specific match info & UserJob state
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
    Shows only jobs saved by the authenticated user with options to view, unsave, or ignore.
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
    """
    Manual job creation view (/jobs/create/) for testing and manual additions.
    Checks for duplicates, calculates user match, creates UserJob, and redirects to job details.
    """
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
