import os
import time
import logging
from typing import Optional, Dict, Any, List
from django.utils import timezone
from applications.models import Application, AutomationLog
from resumes.models import Resume

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


from .base import AutomationResult, FormDetectionResult
from .browser import BrowserManager
from .logging import ApplicationAuditLogger
from .sources.generic_source import GenericBrowserSource
from .exceptions import (
    BrowserAutomationError,
    CaptchaDetectedError,
    LoginRequiredError,
    FormNotFoundError,
    ResumeMissingError,
    AutomationTimeoutError,
    SubmissionConfirmationRequiredError,
)

logger = logging.getLogger(__name__)


class ApplicationRunner:
    """
    Orchestrates the lifecycle of browser automation for a candidate application:
    1. Queues and starts browser (persistent profile or ephemeral).
    2. Navigates to job portal and detects form elements.
    3. Auto-fills known candidate profile fields and attaches resume.
    4. Detects and records any unknown custom questions.
    5. HALTS and transitions status to REVIEW_REQUIRED / WAITING_FOR_REVIEW.
    6. Only upon explicit human confirmation, proceeds to final submission.
    """
    def __init__(self, application: Application, headless: Optional[bool] = None):
        self.application = application
        self.user = application.user
        self.job = application.job
        self.resume = application.resume
        self.audit = ApplicationAuditLogger(application)
        self.source = GenericBrowserSource()
        self.headless = headless

    def _update_status(self, app_status: str, auto_status: str, message: str = ""):
        """Updates Application state in DB and logs audit action."""
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        self.application.status = app_status
        self.application.automation_status = auto_status
        if message:
            self.audit.info(auto_status, message)
        self.application.save(update_fields=['status', 'automation_status', 'updated_at'])

    def run_preparation(self) -> AutomationResult:
        """
        Executes Steps 1 through 4: Opens browser, locates form, fills profile fields,
        attaches resume, flags unknown questions, and pauses for human review.
        """
        self.audit.info("START", f"Starting automated preparation for job: '{self.job.title}' at {self.job.company}")
        self._update_status(
            Application.Status.IN_PROGRESS,
            Application.AutomationStatus.STARTING_BROWSER,
            "Launching Chrome browser instance..."
        )

        job_url = self.application.application_url or self.job.external_url
        if not job_url:
            err = "Job has no external URL or application URL provided."
            self._handle_failure(Application.AutomationStatus.FAILED, err)
            return AutomationResult(success=False, status="FAILED", message=err, error_details=err)

        browser_manager = BrowserManager(headless=self.headless)

        try:
            with browser_manager as page:
                # Step 2: Open job URL
                self._update_status(
                    Application.Status.IN_PROGRESS,
                    Application.AutomationStatus.OPENING_JOB,
                    f"Navigating to {job_url}"
                )

                detection = self.source.navigate_and_detect(page, job_url, self.user)

                if detection.captcha_detected:
                    raise CaptchaDetectedError("CAPTCHA / Bot challenge detected on page. Halting automation.")

                if detection.login_required:
                    raise LoginRequiredError("External portal requires user login before application form can be accessed.")

                # Step 3: Application form detected
                self._update_status(
                    Application.Status.IN_PROGRESS,
                    Application.AutomationStatus.APPLICATION_DETECTED,
                    f"Application portal loaded. Found {len(detection.detected_inputs)} inputs."
                )

                # Step 4: Fill form fields and attach resume
                self._update_status(
                    Application.Status.IN_PROGRESS,
                    Application.AutomationStatus.FILLING_FORM,
                    "Auto-filling profile fields and attaching resume..."
                )

                filled_fields, fresh_detection = self.source.fill_form_fields(
                    page=page,
                    user=self.user,
                    resume=self.resume,
                    detection=detection
                )

                # Convert unknown questions to serializable dicts
                questions_data = [q.to_dict() for q in fresh_detection.unknown_questions]

                # Update application model with detected questions & filled fields
                self.application.filled_fields = filled_fields
                self.application.detected_questions = questions_data
                self.application.error_message = ""
                self.application.save(update_fields=['filled_fields', 'detected_questions', 'error_message', 'updated_at'])

                # Log fields and questions summary
                self.audit.success(
                    "FIELDS_FILLED",
                    f"Auto-filled {len(filled_fields)} fields: {', '.join(filled_fields.keys())}. "
                    f"Identified {len(questions_data)} questions requiring review."
                )

                # Step 5: HALT for user review
                self._update_status(
                    Application.Status.REVIEW_REQUIRED,
                    Application.AutomationStatus.WAITING_FOR_REVIEW,
                    "Application prepared! Stopped for candidate review and confirmation before submission."
                )

                return AutomationResult(
                    success=True,
                    status="REVIEW_REQUIRED",
                    message="Form prepared successfully. Ready for candidate review.",
                    filled_fields=filled_fields,
                    detected_questions=questions_data
                )

        except CaptchaDetectedError as e:
            self.audit.warning("CAPTCHA_DETECTED", str(e))
            self._handle_failure(Application.AutomationStatus.FAILED, str(e), status=Application.Status.REVIEW_REQUIRED)
            return AutomationResult(success=False, status="REVIEW_REQUIRED", message=str(e), error_details=str(e))

        except LoginRequiredError as e:
            self.audit.warning("LOGIN_REQUIRED", str(e))
            self._handle_failure(Application.AutomationStatus.FAILED, str(e), status=Application.Status.REVIEW_REQUIRED)
            return AutomationResult(success=False, status="REVIEW_REQUIRED", message=str(e), error_details=str(e))

        except Exception as e:
            err_msg = str(e)
            logger.exception("Error during automation preparation")
            self.audit.error("ERROR", f"Automation preparation failed: {err_msg}")
            self._handle_failure(Application.AutomationStatus.FAILED, err_msg)
            return AutomationResult(success=False, status="FAILED", message=err_msg, error_details=err_msg)

    def run_submission(self, user_confirmed: bool) -> AutomationResult:
        """
        Step 6: Executes final submission after human confirmation.
        """
        if not user_confirmed:
            err = "Explicit human confirmation is required before final submission."
            self.audit.error("CONFIRMATION_REQUIRED", err)
            raise SubmissionConfirmationRequiredError(err)

        self._update_status(
            Application.Status.IN_PROGRESS,
            Application.AutomationStatus.SUBMITTING,
            "Candidate confirmed submission. Triggering external application submission..."
        )

        job_url = self.application.application_url or self.job.external_url
        browser_manager = BrowserManager(headless=self.headless)

        try:
            with browser_manager as page:
                # In test mode or when submitting, execute submit on portal
                self.source.navigate_and_detect(page, job_url, self.user)
                # Ensure fields are set
                self.source.fill_form_fields(page, self.user, self.resume, FormDetectionResult())
                success, msg = self.source.submit(page, user_confirmed=True)

                if success:
                    now = timezone.now()
                    self.application.submitted_at = now
                    self.application.applied_at = now
                    self._update_status(
                        Application.Status.SUBMITTED,
                        Application.AutomationStatus.SUBMITTED,
                        f"Submission completed successfully! ({msg})"
                    )
                    self.application.save(update_fields=['submitted_at', 'applied_at', 'updated_at'])

                    return AutomationResult(
                        success=True,
                        status="SUBMITTED",
                        message=msg
                    )
                else:
                    raise BrowserAutomationError(msg)

        except Exception as e:
            err_msg = str(e)
            logger.exception("Error during application submission")
            self.audit.error("SUBMIT_FAILED", f"Final submission failed: {err_msg}")
            self._handle_failure(Application.AutomationStatus.FAILED, err_msg)
            return AutomationResult(success=False, status="FAILED", message=err_msg, error_details=err_msg)

    def _handle_failure(self, auto_status: str, error_msg: str, status: str = Application.Status.FAILED):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        self.application.status = status
        self.application.automation_status = auto_status
        self.application.error_message = error_msg
        self.application.save(update_fields=['status', 'automation_status', 'error_message', 'updated_at'])
