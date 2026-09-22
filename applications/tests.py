from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from jobs.models import Job
from resumes.models import Resume
from applications.models import Application, AutomationLog
from automation.base import AutomationResult


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


class ApplicationAutomationViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='candidatetest', password='Password123!', email='c@example.com')
        self.client.login(username='candidatetest', password='Password123!')

        # Create sample PDF resume
        dummy_pdf = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 test resume content", content_type="application/pdf")
        self.resume = Resume.objects.create(
            user=self.user,
            name="Principal Python Resume",
            file=dummy_pdf,
            is_default=True
        )

        self.job = Job.objects.create(
            title="Senior Platform Engineer",
            company="CloudCorp",
            location="Remote",
            external_url="https://example.com/apply/123"
        )

    @patch('automation.manager.AutomationManager.start_preparation')
    def test_application_prepare_view_triggers_automation(self, mock_start_prep):
        mock_start_prep.return_value = AutomationResult(success=True, status="QUEUED", message="Queued")

        url = reverse('applications:prepare', kwargs={'job_id': self.job.pk})
        resp = self.client.post(url, {'resume_id': self.resume.pk})

        self.assertEqual(resp.status_code, 302)
        app = Application.objects.get(user=self.user, job=self.job)
        self.assertEqual(app.status, Application.Status.QUEUED)
        self.assertEqual(app.resume, self.resume)
        mock_start_prep.assert_called_once()

    def test_application_review_view_get(self):
        app = Application.objects.create(
            user=self.user,
            job=self.job,
            resume=self.resume,
            status=Application.Status.REVIEW_REQUIRED,
            automation_status=Application.AutomationStatus.WAITING_FOR_REVIEW,
            detected_questions=[
                {
                    'question_text': 'Are you authorized to work in US?',
                    'field_name': 'work_auth',
                    'input_type': 'text',
                    'options': [],
                    'is_required': True,
                    'current_value': '',
                    'answered': False
                }
            ]
        )

        url = reverse('applications:review', kwargs={'pk': app.pk})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Senior Platform Engineer")
        self.assertContains(resp, "Are you authorized to work in US?")

    def test_application_review_view_post_saves_answers(self):
        app = Application.objects.create(
            user=self.user,
            job=self.job,
            resume=self.resume,
            status=Application.Status.REVIEW_REQUIRED,
            automation_status=Application.AutomationStatus.WAITING_FOR_REVIEW,
            detected_questions=[
                {
                    'question_text': 'Are you authorized to work in US?',
                    'field_name': 'work_auth',
                    'input_type': 'text',
                    'options': [],
                    'is_required': True,
                    'current_value': '',
                    'answered': False
                }
            ]
        )

        url = reverse('applications:review', kwargs={'pk': app.pk})
        resp = self.client.post(url, {
            'question_work_auth': 'Yes, US Citizen',
            'notes': 'Follow up by Friday'
        })

        self.assertEqual(resp.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.answers.get('work_auth'), 'Yes, US Citizen')
        self.assertEqual(app.notes, 'Follow up by Friday')

    def test_application_status_api_json(self):
        app = Application.objects.create(
            user=self.user,
            job=self.job,
            status=Application.Status.REVIEW_REQUIRED,
            automation_status=Application.AutomationStatus.WAITING_FOR_REVIEW
        )
        AutomationLog.objects.create(
            application=app,
            level=AutomationLog.Level.INFO,
            action="TEST",
            message="Status polling test message"
        )

        url = reverse('applications:status_api', kwargs={'pk': app.pk})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'REVIEW_REQUIRED')
        self.assertEqual(data['automation_status'], 'WAITING_FOR_REVIEW')
        self.assertTrue(data['is_review_ready'])
        self.assertEqual(len(data['logs']), 1)
        self.assertEqual(data['logs'][0]['action'], 'TEST')

    @patch('automation.manager.AutomationManager.submit_application')
    def test_application_confirm_submit_view(self, mock_submit):
        mock_submit.return_value = AutomationResult(success=True, status="SUBMITTED", message="Submitted")

        app = Application.objects.create(
            user=self.user,
            job=self.job,
            status=Application.Status.REVIEW_REQUIRED,
            automation_status=Application.AutomationStatus.WAITING_FOR_REVIEW
        )

        url = reverse('applications:confirm_submit', kwargs={'pk': app.pk})
        resp = self.client.post(url, {'question_custom': 'My custom answer'})

        self.assertEqual(resp.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.answers.get('custom'), 'My custom answer')
        mock_submit.assert_called_once()

