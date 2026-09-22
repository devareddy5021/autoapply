from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Application
from .forms import ApplicationUpdateForm
from jobs.models import Job
from resumes.models import Resume

@login_required
def application_list_view(request):
    status_filter = request.GET.get('status', '').strip()
    apps_qs = Application.objects.filter(user=request.user).select_related('job', 'resume')

    if status_filter:
        apps_qs = apps_qs.filter(status=status_filter)

    # Status counts for tab badges
    all_user_apps = Application.objects.filter(user=request.user)
    counts = {
        'all': all_user_apps.count(),
        'saved': all_user_apps.filter(status=Application.Status.SAVED).count(),
        'review': all_user_apps.filter(status=Application.Status.REVIEW_REQUIRED).count(),
        'submitted': all_user_apps.filter(status=Application.Status.SUBMITTED).count(),
        'interview': all_user_apps.filter(status=Application.Status.INTERVIEW).count(),
        'rejected': all_user_apps.filter(status=Application.Status.REJECTED).count(),
    }

    return render(request, 'applications/application_list.html', {
        'applications': apps_qs,
        'status_filter': status_filter,
        'counts': counts,
        'statuses': Application.Status.choices,
    })


@login_required
def quick_track_job(request, job_id):
    """Creates or updates an application entry from a Job card."""
    job = get_object_or_404(Job, pk=job_id)
    target_status = request.POST.get('status', Application.Status.SAVED)
    resume_id = request.POST.get('resume_id')

    default_resume = None
    if resume_id:
        default_resume = Resume.objects.filter(pk=resume_id, user=request.user).first()
    if not default_resume:
        default_resume = Resume.objects.filter(user=request.user, is_default=True).first()

    app_obj, created = Application.objects.get_or_create(
        user=request.user,
        job=job,
        defaults={
            'status': target_status,
            'resume': default_resume,
            'application_url': job.external_url,
            'applied_at': timezone.now() if target_status == Application.Status.SUBMITTED else None,
        }
    )

    if not created:
        app_obj.status = target_status
        if default_resume and not app_obj.resume:
            app_obj.resume = default_resume
        if target_status == Application.Status.SUBMITTED and not app_obj.applied_at:
            app_obj.applied_at = timezone.now()
        app_obj.save()

    status_name = dict(Application.Status.choices).get(target_status, target_status)
    messages.success(request, f"Application for '{job.title}' at {job.company} updated to {status_name}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'applications:list'
    return redirect(next_url)


@login_required
def application_detail_view(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ApplicationUpdateForm(request.POST, instance=application, user=request.user)
        if form.is_valid():
            app = form.save(commit=False)
            if app.status == Application.Status.SUBMITTED and not app.applied_at:
                app.applied_at = timezone.now()
            app.save()
            messages.success(request, "Application status updated successfully.")
            return redirect('applications:detail', pk=pk)
    else:
        form = ApplicationUpdateForm(instance=application, user=request.user)

    return render(request, 'applications/application_detail.html', {
        'application': application,
        'form': form,
    })


@login_required
def application_delete_view(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)
    job_title = application.job.title
    application.delete()
    messages.info(request, f"Application tracking for '{job_title}' was removed.")
    return redirect('applications:list')
