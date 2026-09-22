import re
from urllib.parse import urlparse, urlunparse
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

def normalize_job_url(url: str) -> str:
    """Normalizes job URL by stripping query parameters and trailing slashes."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Remove tracking query parameters (utm_*, ref, etc.)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))

class Job(models.Model):
    class WorkMode(models.TextChoices):
        REMOTE = 'REMOTE', 'Remote'
        HYBRID = 'HYBRID', 'Hybrid'
        ONSITE = 'ONSITE', 'Onsite'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    WorkMode.ON_SITE = WorkMode.ONSITE

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        CONTRACT = 'CONTRACT', 'Contract'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        TRAINEE = 'TRAINEE', 'Trainee'
        TEMPORARY = 'TEMPORARY', 'Temporary'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    class Source(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual'
        LINKEDIN = 'LINKEDIN', 'LinkedIn'
        NAUKRI = 'NAUKRI', 'Naukri'
        INDEED = 'INDEED', 'Indeed'
        WELLFOUND = 'WELLFOUND', 'Wellfound'
        OTHER = 'OTHER', 'Other'

    # Core Identifiers & Organization
    title = models.CharField(max_length=255, db_index=True)
    company_name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, blank=True, default='Not specified', db_index=True)
    work_mode = models.CharField(
        max_length=20,
        choices=WorkMode.choices,
        default=WorkMode.REMOTE,
        db_index=True
    )
    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        db_index=True
    )

    # Narrative Content
    description = models.TextField(help_text="Full job description")
    requirements = models.TextField(blank=True, default="", help_text="Specific job requirements and qualifications")
    responsibilities = models.TextField(blank=True, default="", help_text="Key day-to-day responsibilities")

    # Compensation
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD', blank=True)
    salary_text = models.CharField(max_length=150, blank=True, help_text="Raw or formatted salary string")

    # Experience Requirements
    experience_min = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0.0,
        help_text="Minimum required experience in years"
    )
    experience_max = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Maximum required experience in years"
    )

    # Skills
    skills = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated required skills, e.g. Python, Django, PostgreSQL, Docker"
    )

    # Source & Tracking
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.MANUAL,
        db_index=True
    )
    source_job_id = models.CharField(max_length=150, blank=True, db_index=True)
    external_url = models.URLField(max_length=1000, blank=True)
    normalized_url = models.CharField(max_length=500, blank=True, db_index=True)

    # Status & Timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    discovered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-discovered_at']
        indexes = [
            models.Index(fields=['company_name', 'title']),
            models.Index(fields=['source', 'is_active']),
            models.Index(fields=['posted_at']),
        ]

    def __init__(self, *args, **kwargs):
        # Backward compatibility translation for legacy field names
        if 'company' in kwargs and 'company_name' not in kwargs:
            kwargs['company_name'] = kwargs.pop('company')
        if 'external_job_id' in kwargs and 'source_job_id' not in kwargs:
            kwargs['source_job_id'] = kwargs.pop('external_job_id')
        if 'experience_required_years' in kwargs and 'experience_min' not in kwargs:
            kwargs['experience_min'] = kwargs.pop('experience_required_years')
        if 'status' in kwargs and 'is_active' not in kwargs:
            status_val = kwargs.pop('status')
            kwargs['is_active'] = (status_val == 'ACTIVE')
        if kwargs.get('work_mode') == 'ON_SITE':
            kwargs['work_mode'] = Job.WorkMode.ONSITE
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.title} at {self.company_name} ({self.location})"

    def save(self, *args, **kwargs):
        if self.work_mode == 'ON_SITE':
            self.work_mode = Job.WorkMode.ONSITE
        if self.external_url:
            self.normalized_url = normalize_job_url(self.external_url)
        super().save(*args, **kwargs)

    # Backward compatibility properties
    @property
    def company(self) -> str:
        return self.company_name

    @company.setter
    def company(self, value: str):
        self.company_name = value

    @property
    def external_job_id(self) -> str:
        return self.source_job_id

    @external_job_id.setter
    def external_job_id(self, value: str):
        self.source_job_id = value

    @property
    def experience_required_years(self) -> float:
        return float(self.experience_min)

    @experience_required_years.setter
    def experience_required_years(self, value: float):
        self.experience_min = value

    @property
    def status(self) -> str:
        return 'ACTIVE' if self.is_active else 'ARCHIVED'

    @status.setter
    def status(self, value: str):
        self.is_active = (value == 'ACTIVE')

    @classmethod
    def find_duplicate(cls, company: str, title: str, location: str = '', external_url: str = '', external_job_id: str = ''):
        """
        Checks if a job already exists matching source_job_id, normalized_url,
        or company + title + location tuple.
        """
        if external_job_id:
            existing = cls.objects.filter(source_job_id=external_job_id).first()
            if existing:
                return existing

        if external_url:
            norm_url = normalize_job_url(external_url)
            if norm_url:
                existing = cls.objects.filter(normalized_url=norm_url).first()
                if existing:
                    return existing

        query = cls.objects.filter(
            company_name__iexact=company.strip(),
            title__iexact=title.strip()
        )
        if location:
            query = query.filter(location__icontains=location.strip())
        return query.first()

    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def formatted_salary(self):
        if self.salary_text:
            return self.salary_text
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        if self.salary_min:
            return f"From {self.salary_currency} {self.salary_min:,.0f}"
        if self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,.0f}"
        return "Not disclosed"

    @property
    def formatted_experience(self):
        if self.experience_min is not None and self.experience_max is not None:
            if self.experience_min == 0 and self.experience_max <= 2:
                return f"Entry Level (0 - {self.experience_max:g} yrs)"
            return f"{self.experience_min:g} - {self.experience_max:g} yrs"
        if self.experience_min is not None and self.experience_min > 0:
            return f"{self.experience_min:g}+ yrs"
        if self.experience_min == 0:
            return "Entry Level"
        return "Not specified"


    @property
    def is_new(self):
        return self.discovered_at >= timezone.now() - timedelta(days=7)


class UserJob(models.Model):
    """
    Stores user-specific state for a job (saved, ignored, precomputed match score).
    A job itself is global data; UserJob maps user interactions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='user_jobs')
    is_saved = models.BooleanField(default=False, db_index=True)
    is_ignored = models.BooleanField(default=False, db_index=True)
    match_score = models.IntegerField(default=0, db_index=True)
    match_reasons = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'job'], name='unique_user_job')
        ]
        indexes = [
            models.Index(fields=['user', 'is_saved']),
            models.Index(fields=['user', 'is_ignored']),
            models.Index(fields=['user', 'match_score']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.job.title} at {self.job.company_name} (Saved: {self.is_saved}, Ignored: {self.is_ignored})"
