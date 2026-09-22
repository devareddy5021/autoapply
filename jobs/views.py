from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Job
from .forms import JobForm
from matching.services import calculate_match_score
from resumes.models import Resume
from accounts.models import Profile

@login_required
def job_list_view(request):
    jobs_qs = Job.objects.all()

    # Search query
    query = request.GET.get('q', '').strip()
    if query:
        jobs_qs = jobs_qs.filter(
            Q(title__icontains=query) |
            Q(company__icontains=query) |
            Q(location__icontains=query) |
            Q(skills__icontains=query) |
            Q(description__icontains=query)
        )

    # Filters
    work_mode = request.GET.get('work_mode', '').strip()
    if work_mode:
        jobs_qs = jobs_qs.filter(work_mode=work_mode)

    source = request.GET.get('source', '').strip()
    if source:
        jobs_qs = jobs_qs.filter(source=source)

    status = request.GET.get('status', 'ACTIVE').strip()
    if status and status != 'ALL':
        jobs_qs = jobs_qs.filter(status=status)

    location = request.GET.get('location', '').strip()
    if location:
        jobs_qs = jobs_qs.filter(location__icontains=location)

    # Fetch user profile and default resume for matching
    profile, _ = Profile.objects.get_or_create(user=request.user)
    default_resume = Resume.objects.filter(user=request.user, is_default=True).first()

    # User's tracked applications lookup
    from applications.models import Application
    user_applications = {
        app.job_id: app.status
        for app in Application.objects.filter(user=request.user)
    }

    # Annotate jobs with match scores
    jobs_with_scores = []
    min_score_filter = request.GET.get('min_score', '').strip()
    min_score_val = int(min_score_filter) if min_score_filter.isdigit() else 0

    for job in jobs_qs:
        match_info = calculate_match_score(job, profile, default_resume)
        if match_info['total_score'] >= min_score_val:
            jobs_with_scores.append({
                'job': job,
                'score': match_info['total_score'],
                'match_info': match_info,
                'application_status': user_applications.get(job.id),
            })

    # Sort option
    sort_by = request.GET.get('sort', 'score')
    if sort_by == 'score':
        jobs_with_scores.sort(key=lambda x: x['score'], reverse=True)
    elif sort_by == 'date':
        jobs_with_scores.sort(key=lambda x: x['job'].discovered_at, reverse=True)
    elif sort_by == 'company':
        jobs_with_scores.sort(key=lambda x: x['job'].company.lower())

    paginator = Paginator(jobs_with_scores, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Distinct values for filter dropdowns
    available_sources = Job.Source.choices
    available_work_modes = Job.WorkMode.choices

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'query': query,
        'work_mode_filter': work_mode,
        'source_filter': source,
        'status_filter': status,
        'min_score_filter': min_score_filter,
        'sort_by': sort_by,
        'available_sources': available_sources,
        'available_work_modes': available_work_modes,
        'total_count': len(jobs_with_scores),
    })


@login_required
def job_detail_view(request, pk):
    job = get_object_or_404(Job, pk=pk)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    default_resume = Resume.objects.filter(user=request.user, is_default=True).first()

    match_breakdown = calculate_match_score(job, profile, default_resume)

    from applications.models import Application
    application = Application.objects.filter(user=request.user, job=job).first()
    user_resumes = Resume.objects.filter(user=request.user)

    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'match': match_breakdown,
        'application': application,
        'user_resumes': user_resumes,
    })


@login_required
def job_create_view(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            company = form.cleaned_data.get('company')
            location = form.cleaned_data.get('location')
            ext_url = form.cleaned_data.get('external_url')
            ext_id = form.cleaned_data.get('external_job_id')

            duplicate = Job.find_duplicate(
                company=company,
                title=title,
                location=location,
                external_url=ext_url,
                external_job_id=ext_id
            )
            if duplicate:
                messages.warning(request, f"Note: A matching job listing at '{duplicate.company}' already exists (ID #{duplicate.id}).")

            job = form.save()
            messages.success(request, f"Job '{job.title}' at {job.company} added successfully!")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm()

    return render(request, 'jobs/job_form.html', {
        'form': form,
        'title': 'Post / Add Job Listing',
    })


@login_required
def job_update_view(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, f"Job '{job.title}' updated successfully.")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm(instance=job)

    return render(request, 'jobs/job_form.html', {
        'form': form,
        'job': job,
        'title': f'Edit Job: {job.title}',
    })


@login_required
def job_delete_view(request, pk):
    job = get_object_or_404(Job, pk=pk)
    title = job.title
    job.delete()
    messages.info(request, f"Job '{title}' has been removed.")
    return redirect('jobs:list')
