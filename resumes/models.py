import os
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from .services import extract_text_from_pdf, detect_skills_in_text

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    name = models.CharField(max_length=200, help_text="e.g. Senior Python Developer Resume")
    file = models.FileField(
        upload_to='resumes/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload your resume in PDF format only."
    )
    version = models.CharField(max_length=50, default='1.0', help_text="e.g. v1, 2026.1")
    upload_date = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Mark as default resume for automated match and application"
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Extracted plain text for search and automated matching"
    )
    file_size_kb = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-is_default', '-upload_date']

    def __str__(self):
        return f"{self.name} ({self.version}) - {self.user.username}"

    def save(self, *args, **kwargs):
        # Enforce only one default resume per user
        if self.is_default:
            Resume.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        elif not Resume.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).exists():
            # If this is the user's only resume, make it default automatically
            self.is_default = True

        super().save(*args, **kwargs)

        # Extract text if not already extracted or file present
        if self.file and not self.extracted_text:
            try:
                extracted = extract_text_from_pdf(self.file)
                if extracted:
                    self.extracted_text = extracted
                if self.file.size:
                    self.file_size_kb = round(self.file.size / 1024)
                super().save(update_fields=['extracted_text', 'file_size_kb'])
            except Exception:
                pass

    @property
    def detected_skills(self):
        return detect_skills_in_text(self.extracted_text)

    @property
    def filename(self):
        return os.path.basename(self.file.name) if self.file else ''
