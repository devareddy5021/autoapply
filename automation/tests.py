from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import Profile
from jobs.models import Job
from resumes.models import Resume
from applications.models import Application, AutomationLog

from automation.field_mapper import ProfileFieldMapper
from automation.logging import sanitize_message, ApplicationAuditLogger
from automation.exceptions import (
    SubmissionConfirmationRequiredError,
    CaptchaDetectedError,
    LoginRequiredError,
    ResumeMissingError
)
from automation.application_runner import ApplicationRunner
from automation.base import FormDetectionResult, QuestionItem


class AutomationFieldMapperTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testcandidate',
            email='candidate@example.com',
            first_name='Alex',
            last_name='Morgan'
        )
        self.profile = self.user.profile
        self.profile.full_name = 'Alex Morgan'
        self.profile.phone = '+1-555-0199'
        self.profile.current_location = 'San Francisco, CA'
        self.profile.work_authorization = 'Authorized to work in US'
        self.profile.years_of_experience = 5.5
        self.profile.notice_period_days = 15
        self.profile.linkedin_url = 'https://linkedin.com/in/alexmorgan'
        self.profile.github_url = 'https://github.com/alexmorgan'
        self.profile.portfolio_url = 'https://alexmorgan.dev'
        self.profile.save()
        self.mapper = ProfileFieldMapper(self.user)

    def test_identify_email_field(self):
        category, val = self.mapper.identify_field({'name': 'candidate_email', 'type': 'email'})
        self.assertEqual(category, 'email')
        self.assertEqual(val, 'candidate@example.com')

    def test_identify_first_name_field(self):
        category, val = self.mapper.identify_field({'name': 'first_name', 'placeholder': 'First Name'})
        self.assertEqual(category, 'first_name')
        self.assertEqual(val, 'Alex')

    def test_identify_last_name_field(self):
        category, val = self.mapper.identify_field({'id': 'applicant-lname', 'label': 'Last Name'})
        self.assertEqual(category, 'last_name')
        self.assertEqual(val, 'Morgan')

    def test_identify_phone_field(self):
        category, val = self.mapper.identify_field({'name': 'tel', 'type': 'tel'})
        self.assertEqual(category, 'phone')
        self.assertEqual(val, '+1-555-0199')

    def test_identify_linkedin_field(self):
        category, val = self.mapper.identify_field({'placeholder': 'Your LinkedIn Profile URL'})
        self.assertEqual(category, 'linkedin')
        self.assertEqual(val, 'https://linkedin.com/in/alexmorgan')

    def test_unknown_custom_question_returns_none(self):
        category, val = self.mapper.identify_field({
            'name': 'salary_expectations_range',
            'label': 'What is your desired salary range?'
        })
        self.assertIsNone(category)
        self.assertIsNone(val)

    def test_sensitive_or_button_types_ignored(self):
        category, val = self.mapper.identify_field({'type': 'password', 'name': 'password'})
        self.assertIsNone(category)
        category, val = self.mapper.identify_field({'type': 'submit', 'name': 'submit'})
        self.assertIsNone(category)


class SanitizedLoggingTestCase(TestCase):
    def test_sanitize_tokens_and_passwords(self):
        fake_token = "ghp_" + "A" * 36
        raw = f"User password=SuperSecret123; token: {fake_token}"
        cleaned = sanitize_message(raw)
        self.assertNotIn("SuperSecret123", cleaned)
        self.assertNotIn(fake_token, cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_audit_logger_creates_db_record(self):
        user = User.objects.create_user(username='loggeruser', email='log@example.com')
        job = Job.objects.create(
            title='Software Engineer',
            company='Acme Corp',
            location='Remote',
            external_url='https://example.com/job/1'
        )
        app = Application.objects.create(user=user, job=job)

        audit = ApplicationAuditLogger(app)
        log = audit.info("TEST_ACTION", "Testing log creation token=abc123456")

        self.assertEqual(log.application, app)
        self.assertEqual(log.action, "TEST_ACTION")
        self.assertEqual(log.level, AutomationLog.Level.INFO)
        self.assertNotIn("abc123456", log.message)
        self.assertIn("[REDACTED]", log.message)


class ApplicationRunnerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='candidaterunner',
            email='runner@example.com',
            first_name='Sam',
            last_name='Alt'
        )
        self.profile = self.user.profile
        self.profile.full_name = 'Sam Alt'
        self.profile.phone = '555-1234'
        self.profile.save()
        self.job = Job.objects.create(
            title='Backend Python Developer',
            company='TestCo Tech',
            location='San Francisco, CA',
            external_url='https://example.com/jobs/backend-dev'
        )
        self.application = Application.objects.create(
            user=self.user,
            job=self.job
        )

    def test_submission_requires_explicit_confirmation(self):
        runner = ApplicationRunner(self.application)
        with self.assertRaises(SubmissionConfirmationRequiredError):
            runner.run_submission(user_confirmed=False)

    @patch('automation.application_runner.GenericBrowserSource')
    @patch('automation.application_runner.BrowserManager')
    def test_run_preparation_pauses_at_review_required(self, mock_bm_cls, mock_source_cls):
        mock_bm = MagicMock()
        mock_bm_cls.return_value = mock_bm
        mock_page = MagicMock()
        mock_bm.__enter__.return_value = mock_page

        mock_source = MagicMock()
        mock_source_cls.return_value = mock_source

        # Simulate detecting 2 questions and 2 filled fields
        mock_detection = FormDetectionResult(
            found=True,
            captcha_detected=False,
            login_required=False,
            detected_inputs=[{'name': 'first_name', 'value': 'Sam'}],
            unknown_questions=[
                QuestionItem(
                    question_text="Why do you want to work here?",
                    field_name="why_join_us",
                    input_type="textarea"
                )
            ]
        )
        mock_source.navigate_and_detect.return_value = mock_detection
        mock_source.fill_form_fields.return_value = (
            {'first_name': 'Sam', 'email': 'runner@example.com'},
            mock_detection
        )

        runner = ApplicationRunner(self.application)
        result = runner.run_preparation()

        self.assertTrue(result.success)
        self.assertEqual(result.status, "REVIEW_REQUIRED")

        # Verify DB state
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.REVIEW_REQUIRED)
        self.assertEqual(self.application.automation_status, Application.AutomationStatus.WAITING_FOR_REVIEW)
        self.assertEqual(len(self.application.detected_questions), 1)
        self.assertEqual(self.application.detected_questions[0]['field_name'], 'why_join_us')
        self.assertIn('first_name', self.application.filled_fields)

    @patch('automation.application_runner.GenericBrowserSource')
    @patch('automation.application_runner.BrowserManager')
    def test_run_submission_confirmed_success(self, mock_bm_cls, mock_source_cls):
        mock_bm = MagicMock()
        mock_bm_cls.return_value = mock_bm
        mock_bm.__enter__.return_value = MagicMock()

        mock_source = MagicMock()
        mock_source_cls.return_value = mock_source
        mock_source.submit.return_value = (True, "Submission confirmed")

        runner = ApplicationRunner(self.application)
        result = runner.run_submission(user_confirmed=True)

        self.assertTrue(result.success)
        self.assertEqual(result.status, "SUBMITTED")

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SUBMITTED)
        self.assertEqual(self.application.automation_status, Application.AutomationStatus.SUBMITTED)
        self.assertIsNotNone(self.application.submitted_at)
