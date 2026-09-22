from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from resumes.models import Resume
from resumes.services import detect_skills_in_text

class ResumeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resumetestuser',
            password='Password123!'
        )

    def test_single_default_resume_enforcement(self):
        # Create first resume
        r1 = Resume.objects.create(
            user=self.user,
            name="Resume 1",
            version="1.0"
        )
        r1.refresh_from_db()
        self.assertTrue(r1.is_default)

        # Create second resume marked as default
        r2 = Resume.objects.create(
            user=self.user,
            name="Resume 2",
            version="2.0",
            is_default=True
        )
        r1.refresh_from_db()
        r2.refresh_from_db()

        self.assertTrue(r2.is_default)
        self.assertFalse(r1.is_default)

    def test_detect_skills_in_text(self):
        sample_text = "Proficient in Python, Django, PostgreSQL, and Docker with experience in AWS cloud infrastructure."
        skills = detect_skills_in_text(sample_text)
        self.assertIn("Python", skills)
        self.assertIn("Django", skills)
        self.assertIn("Postgresql", skills)
        self.assertIn("Docker", skills)
        self.assertIn("AWS", skills)
