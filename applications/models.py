from django.db import models
from django.contrib.auth.models import User
from jobs.models import Job
from resumes.models import Resume

class Application(models.Model):
    class Status(models.TextChoices):
        SAVED = 'SAVED', 'Saved'
        READY = 'READY', 'Ready to Apply'
        REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review Required'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        FAILED = 'FAILED', 'Failed'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        REJECTED = 'REJECTED', 'Rejected'
        INTERVIEW = 'INTERVIEW', 'Interview'

    class AutomationStatus(models.TextChoices):
        IDLE = 'IDLE', 'Idle / Manual'
        QUEUED = 'QUEUED', 'Queued in Celery'
        FORM_DETECTED = 'FORM_DETECTED', 'Form Detected'
        FIELDS_FILLED = 'FIELDS_FILLED', 'Fields Filled'
        WAITING_REVIEW = 'WAITING_REVIEW', 'Waiting For User Review'
        SUBMIT_CONFIRMED = 'SUBMIT_CONFIRMED', 'Submission Confirmed'
        ERROR = 'ERROR', 'Error Encountered'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        help_text="Resume customized or selected for this job"
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SAVED,
        db_index=True
    )
    automation_status = models.CharField(
        max_length=30,
        choices=AutomationStatus.choices,
        default=AutomationStatus.IDLE
    )
    application_url = models.URLField(max_length=1000, blank=True)
    notes = models.TextField(blank=True, help_text="Personal interview notes, follow-up dates, etc.")
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key-value pairs of form questions and answered values"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'job'], name='unique_user_job_application')
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.job.title} at {self.job.company} [{self.get_status_display()}]"

    @property
    def status_badge_class(self):
        badge_map = {
            self.Status.SAVED: 'badge-secondary',
            self.Status.READY: 'badge-info',
            self.Status.REVIEW_REQUIRED: 'badge-warning',
            self.Status.IN_PROGRESS: 'badge-primary',
            self.Status.SUBMITTED: 'badge-success',
            self.Status.FAILED: 'badge-danger',
            self.Status.WITHDRAWN: 'badge-dark',
            self.Status.REJECTED: 'badge-danger',
            self.Status.INTERVIEW: 'badge-gradient-accent',
        }
        return badge_map.get(self.status, 'badge-secondary')
