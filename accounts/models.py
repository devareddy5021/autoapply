from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    class WorkPreference(models.TextChoices):
        REMOTE = 'REMOTE', 'Remote'
        HYBRID = 'HYBRID', 'Hybrid'
        OFFICE = 'OFFICE', 'Work From Office'
        FLEXIBLE = 'FLEXIBLE', 'Any / Flexible'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    current_location = models.CharField(max_length=150, blank=True, help_text="e.g. Bengaluru, India")
    preferred_locations = models.CharField(
        max_length=300,
        blank=True,
        help_text="Comma-separated locations, e.g. Bengaluru, Hyderabad, Remote"
    )
    work_authorization = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. Authorized to work in India / US Citizen / Work Permit"
    )
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0.0,
        help_text="Total professional experience in years"
    )
    notice_period_days = models.PositiveIntegerField(
        default=30,
        help_text="Notice period in days (0 for immediate joiner)"
    )
    preferred_job_titles = models.CharField(
        max_length=300,
        blank=True,
        help_text="Target job titles, e.g. Python Developer, Django Engineer, Full Stack Lead"
    )
    skills = models.TextField(
        blank=True,
        help_text="Comma-separated list of skills, e.g. Python, Django, PostgreSQL, Docker, Redis, Celery"
    )
    education = models.TextField(
        blank=True,
        help_text="Educational background, e.g. B.Tech in Computer Science, University of Technology (2020)"
    )
    certifications = models.TextField(
        blank=True,
        help_text="Certifications, e.g. AWS Certified Developer, CKA"
    )
    linkedin_url = models.URLField(max_length=300, blank=True)
    github_url = models.URLField(max_length=300, blank=True)
    portfolio_url = models.URLField(max_length=300, blank=True)

    preferred_salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum expected annual compensation"
    )
    preferred_salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum expected annual compensation"
    )
    salary_currency = models.CharField(max_length=10, default='INR')
    work_preference = models.CharField(
        max_length=20,
        choices=WorkPreference.choices,
        default=WorkPreference.FLEXIBLE
    )

    # Milestone 3 User Discovery Preferences
    target_roles = models.TextField(
        blank=True,
        default="Data Engineer, Junior Data Engineer, Data Analyst, Data Scientist, Machine Learning Engineer",
        help_text="Target roles to aggregate and prioritize"
    )
    min_match_score = models.PositiveIntegerField(
        default=70,
        help_text="Minimum match score threshold (percentage)"
    )
    remote_only = models.BooleanField(
        default=False,
        help_text="Only show fully remote opportunities"
    )
    internship_allowed = models.BooleanField(default=True)
    trainee_allowed = models.BooleanField(default=True)
    full_time_allowed = models.BooleanField(default=True)
    contract_allowed = models.BooleanField(default=True)
    experience_level = models.CharField(
        max_length=30,
        default='ALL',
        choices=[
            ('ALL', 'All Experience Levels'),
            ('FRESHER', 'Fresher / Entry (0-1 yrs)'),
            ('JUNIOR', 'Junior (1-3 yrs)'),
            ('MID', 'Mid-Level (3-5 yrs)'),
            ('SENIOR', 'Senior (5-8 yrs)'),
            ('LEAD', 'Lead / Staff (8+ yrs)'),
        ]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.display_name} ({self.user.username})"

    @property
    def display_name(self):
        if self.full_name:
            return self.full_name
        if self.user.first_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return self.user.username

    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def preferred_job_titles_list(self):
        if not self.preferred_job_titles:
            return []
        return [t.strip() for t in self.preferred_job_titles.split(',') if t.strip()]

    @property
    def preferred_locations_list(self):
        if not self.preferred_locations:
            return []
        return [l.strip() for l in self.preferred_locations.split(',') if l.strip()]
