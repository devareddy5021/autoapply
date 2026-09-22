from django.db import models
from django.contrib.auth.models import User
from jobs.models import Job
from resumes.models import Resume

class Application(models.Model):
    class Status(models.TextChoices):
        SAVED = 'SAVED', 'Saved'
        READY = 'READY', 'Ready to Apply'
        QUEUED = 'QUEUED', 'Queued'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review Required'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        INTERVIEW = 'INTERVIEW', 'Interview'
        REJECTED = 'REJECTED', 'Rejected'

    class AutomationStatus(models.TextChoices):
        IDLE = 'IDLE', 'Idle / Manual'
        QUEUED = 'QUEUED', 'Queued'
        STARTING_BROWSER = 'STARTING_BROWSER', 'Starting Browser'
        OPENING_JOB = 'OPENING_JOB', 'Opening Job Page'
        APPLICATION_DETECTED = 'APPLICATION_DETECTED', 'Application Detected'
        FILLING_FORM = 'FILLING_FORM', 'Filling Form'
        WAITING_FOR_REVIEW = 'WAITING_FOR_REVIEW', 'Waiting For User Review'
        SUBMITTING = 'SUBMITTING', 'Submitting Application'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

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
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when final submission occurred")
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SAVED,
        db_index=True
    )
    automation_status = models.CharField(
        max_length=30,
        choices=AutomationStatus.choices,
        default=AutomationStatus.IDLE,
        db_index=True
    )
    application_url = models.URLField(max_length=1000, blank=True)
    notes = models.TextField(blank=True, help_text="Personal interview notes, follow-up dates, etc.")
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key-value pairs of form questions and answered values"
    )
    filled_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Fields that were successfully mapped and auto-filled"
    )
    detected_questions = models.JSONField(
        default=list,
        blank=True,
        help_text="Questions detected that require human input or verification"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Detailed error explanation if automation fails"
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
            self.Status.QUEUED: 'badge-info',
            self.Status.REVIEW_REQUIRED: 'badge-warning',
            self.Status.IN_PROGRESS: 'badge-primary',
            self.Status.SUBMITTED: 'badge-success',
            self.Status.FAILED: 'badge-danger',
            self.Status.CANCELLED: 'badge-dark',
            self.Status.WITHDRAWN: 'badge-dark',
            self.Status.REJECTED: 'badge-danger',
            self.Status.INTERVIEW: 'badge-gradient-accent',
        }
        return badge_map.get(self.status, 'badge-secondary')

    @property
    def automation_badge_class(self):
        badge_map = {
            self.AutomationStatus.IDLE: 'badge-secondary',
            self.AutomationStatus.QUEUED: 'badge-info',
            self.AutomationStatus.STARTING_BROWSER: 'badge-primary',
            self.AutomationStatus.OPENING_JOB: 'badge-primary',
            self.AutomationStatus.APPLICATION_DETECTED: 'badge-info',
            self.AutomationStatus.FILLING_FORM: 'badge-warning',
            self.AutomationStatus.WAITING_FOR_REVIEW: 'badge-warning',
            self.AutomationStatus.SUBMITTING: 'badge-primary',
            self.AutomationStatus.SUBMITTED: 'badge-success',
            self.AutomationStatus.FAILED: 'badge-danger',
            self.AutomationStatus.CANCELLED: 'badge-dark',
        }
        return badge_map.get(self.automation_status, 'badge-secondary')


# Compatibility aliases
Application.AutomationStatus.WAITING_REVIEW = Application.AutomationStatus.WAITING_FOR_REVIEW
Application.AutomationStatus.FORM_DETECTED = Application.AutomationStatus.APPLICATION_DETECTED
Application.AutomationStatus.FIELDS_FILLED = Application.AutomationStatus.FILLING_FORM
Application.AutomationStatus.ERROR = Application.AutomationStatus.FAILED


class AutomationLog(models.Model):
    class Level(models.TextChoices):
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'
        SUCCESS = 'SUCCESS', 'Success'

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='automation_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    action = models.CharField(max_length=100)
    message = models.TextField()

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] [{self.level}] {self.action}: {self.message[:60]}"

