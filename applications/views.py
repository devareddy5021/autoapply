from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Application, AutomationLog
from .forms import ApplicationUpdateForm
from jobs.models import Job
from resumes.models import Resume
from automation.manager import AutomationManager


@login_required
def application_list_view(request):
    status_filter = request.GET.get('status', '').strip()
    apps_qs = Application.objects.filter(user=request.user).select_related('job', 'resume').prefetch_related('automation_logs')

    if status_filter:
        apps_qs = apps_qs.filter(status=status_filter)

    # Status counts for tab badges
    all_user_apps = Application.objects.filter(user=request.user)
    counts = {
        'all': all_user_apps.count(),
        'saved': all_user_apps.filter(status=Application.Status.SAVED).count(),
        'review': all_user_apps.filter(status=Application.Status.REVIEW_REQUIRED).count(),
        'in_progress': all_user_apps.filter(status__in=[Application.Status.IN_PROGRESS, Application.Status.QUEUED]).count(),
        'submitted': all_user_apps.filter(status=Application.Status.SUBMITTED).count(),
        'interview': all_user_apps.filter(status=Application.Status.INTERVIEW).count(),
        'failed': all_user_apps.filter(status=Application.Status.FAILED).count(),
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
def application_prepare_view(request, job_id):
    """
    Launches automated browser preparation:
    Navigates to external job, auto-fills form fields, uploads resume,
    flags unknown questions, and pauses for human review.
    """
    job = get_object_or_404(Job, pk=job_id)

    # Validate candidate has a resume
    resumes = Resume.objects.filter(user=request.user)
    if not resumes.exists():
        messages.warning(request, "Please upload a resume first before applying with automation.")
        return redirect('resumes:upload')

    resume_id = request.POST.get('resume_id') or request.GET.get('resume_id')
    selected_resume = None
    if resume_id:
        selected_resume = resumes.filter(pk=resume_id).first()
    if not selected_resume:
        selected_resume = resumes.filter(is_default=True).first() or resumes.first()

    application, created = Application.objects.get_or_create(
        user=request.user,
        job=job,
        defaults={
            'resume': selected_resume,
            'application_url': job.external_url,
            'status': Application.Status.QUEUED,
            'automation_status': Application.AutomationStatus.QUEUED,
        }
    )

    if not created:
        if selected_resume:
            application.resume = selected_resume
        application.status = Application.Status.QUEUED
        application.automation_status = Application.AutomationStatus.QUEUED
        application.error_message = ""
        application.save(update_fields=['resume', 'status', 'automation_status', 'error_message', 'updated_at'])

    # Start browser automation in background thread
    AutomationManager.start_preparation(application, async_exec=True)
    messages.info(request, f"Automation agent started for '{job.title}'. Launching browser...")
    return redirect('applications:review', pk=application.pk)


@login_required
def application_review_view(request, pk):
    """
    The mandatory Human-in-the-Loop review screen.
    Candidates review filled profile fields, supply answers to unknown custom questions,
    inspect audit logs, and confirm final submission.
    """
    application = get_object_or_404(
        Application.objects.select_related('job', 'resume', 'user__profile'),
        pk=pk,
        user=request.user
    )

    if request.method == 'POST':
        # Candidate updated answers to custom questions or notes
        answers = dict(application.answers or {})
        for key, val in request.POST.items():
            if key.startswith('question_'):
                q_field = key[len('question_'):]
                answers[q_field] = val

        application.answers = answers
        if 'notes' in request.POST:
            application.notes = request.POST.get('notes', '')

        application.save(update_fields=['answers', 'notes', 'updated_at'])
        messages.success(request, "Your answers and notes were saved successfully.")
        return redirect('applications:review', pk=application.pk)

    user_resumes = Resume.objects.filter(user=request.user)
    logs = application.automation_logs.order_by('-timestamp')[:25]

    return render(request, 'applications/application_review.html', {
        'application': application,
        'job': application.job,
        'resume': application.resume,
        'user_resumes': user_resumes,
        'filled_fields': application.filled_fields or {},
        'detected_questions': application.detected_questions or [],
        'answers': application.answers or {},
        'logs': logs,
    })


@login_required
@require_POST
def application_confirm_submit_view(request, pk):
    """
    Explicit human confirmation trigger before final submission.
    Ensures no application is submitted without explicit consent.
    """
    application = get_object_or_404(Application, pk=pk, user=request.user)

    # Save any final custom question answers submitted in this POST
    answers = dict(application.answers or {})
    for key, val in request.POST.items():
        if key.startswith('question_'):
            q_field = key[len('question_'):]
            answers[q_field] = val
    application.answers = answers
    application.save(update_fields=['answers', 'updated_at'])

    # Trigger final submission workflow
    AutomationManager.submit_application(application, async_exec=True)
    messages.success(request, "Submission confirmed! Automation agent is finalizing your application.")
    return redirect('applications:review', pk=application.pk)


@login_required
def application_status_api(request, pk):
    """
    AJAX endpoint polled by the UI to update live progress, filled fields,
    questions, and logs in real-time.
    """
    application = get_object_or_404(Application, pk=pk, user=request.user)
    recent_logs = application.automation_logs.order_by('-timestamp')[:15]

    logs_data = [
        {
            'timestamp': log.timestamp.strftime('%H:%M:%S'),
            'level': log.level,
            'action': log.action,
            'message': log.message,
        }
        for log in recent_logs
    ]

    return JsonResponse({
        'id': application.pk,
        'status': application.status,
        'status_display': application.get_status_display(),
        'status_badge': application.status_badge_class,
        'automation_status': application.automation_status,
        'automation_status_display': application.get_automation_status_display(),
        'automation_badge': application.automation_badge_class,
        'error_message': application.error_message,
        'filled_fields_count': len(application.filled_fields or {}),
        'questions_count': len(application.detected_questions or []),
        'is_review_ready': application.status == Application.Status.REVIEW_REQUIRED or application.automation_status == Application.AutomationStatus.WAITING_FOR_REVIEW,
        'is_submitted': application.status == Application.Status.SUBMITTED,
        'is_failed': application.status == Application.Status.FAILED,
        'logs': logs_data,
    })


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

    logs = application.automation_logs.order_by('-timestamp')[:30]

    return render(request, 'applications/application_detail.html', {
        'application': application,
        'form': form,
        'logs': logs,
    })


@login_required
def application_delete_view(request, pk):
    application = get_object_or_404(Application, pk=pk, user=request.user)
    job_title = application.job.title
    application.delete()
    messages.info(request, f"Application tracking for '{job_title}' was removed.")
    return redirect('applications:list')

