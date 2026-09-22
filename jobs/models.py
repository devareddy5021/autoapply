import re
from urllib.parse import urlparse, urlunparse
from django.db import models
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
        ON_SITE = 'ON_SITE', 'On-site'

    class Source(models.TextChoices):
        LINKEDIN = 'LINKEDIN', 'LinkedIn'
        INDEED = 'INDEED', 'Indeed'
        NAUKRI = 'NAUKRI', 'Naukri'
        WELLFOUND = 'WELLFOUND', 'Wellfound'
        MANUAL = 'MANUAL', 'Manual Entry'
        OTHER = 'OTHER', 'Other Source'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        ARCHIVED = 'ARCHIVED', 'Archived'

    title = models.CharField(max_length=255, db_index=True)
    company = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, blank=True, default='Not specified')
    work_mode = models.CharField(
        max_length=20,
        choices=WorkMode.choices,
        default=WorkMode.REMOTE
    )
    description = models.TextField(help_text="Full job description")
    
    # Compensation
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD', blank=True)
    salary_text = models.CharField(max_length=150, blank=True, help_text="Raw or formatted salary string")

    experience_required_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0.0,
        help_text="Minimum required experience in years"
    )
    skills = models.TextField(
        blank=True,
        help_text="Comma-separated required skills, e.g. Python, Django, PostgreSQL, Docker"
    )

    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.MANUAL
    )
    external_url = models.URLField(max_length=1000, blank=True)
    normalized_url = models.CharField(max_length=500, blank=True, db_index=True)
    external_job_id = models.CharField(max_length=150, blank=True, db_index=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    discovered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-discovered_at']
        indexes = [
            models.Index(fields=['company', 'title']),
            models.Index(fields=['source', 'status']),
        ]

    def __str__(self):
        return f"{self.title} at {self.company} ({self.location})"

    def save(self, *args, **kwargs):
        if self.external_url:
            self.normalized_url = normalize_job_url(self.external_url)
        super().save(*args, **kwargs)

    @classmethod
    def find_duplicate(cls, company: str, title: str, location: str = '', external_url: str = '', external_job_id: str = ''):
        """
        Checks if a job already exists matching external_job_id, normalized_url,
        or company + title + location tuple.
        """
        if external_job_id:
            existing = cls.objects.filter(external_job_id=external_job_id).first()
            if existing:
                return existing

        if external_url:
            norm_url = normalize_job_url(external_url)
            if norm_url:
                existing = cls.objects.filter(normalized_url=norm_url).first()
                if existing:
                    return existing

        # Check company + title + location match
        query = cls.objects.filter(
            company__iexact=company.strip(),
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
    def is_new(self):
        return self.discovered_at >= timezone.now() - timedelta(days=7)
