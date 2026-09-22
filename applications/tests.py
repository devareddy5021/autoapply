from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from jobs.models import Job
from applications.models import Application

class ApplicationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apptestuser', password='Password123!')
        self.job = Job.objects.create(
            title="Django Specialist",
            company="Web Works",
            location="Remote",
            description="Django backend engineering"
        )

    def test_application_creation_and_defaults(self):
        app = Application.objects.create(
            user=self.user,
            job=self.job,
            status=Application.Status.SAVED
        )
        self.assertEqual(app.status, Application.Status.SAVED)
        self.assertEqual(app.automation_status, Application.AutomationStatus.IDLE)

    def test_unique_constraint_user_job(self):
        Application.objects.create(
            user=self.user,
            job=self.job,
            status=Application.Status.SAVED
        )
        with self.assertRaises(IntegrityError):
            Application.objects.create(
                user=self.user,
                job=self.job,
                status=Application.Status.READY
            )
