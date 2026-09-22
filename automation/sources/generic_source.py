import re
import time
import logging
from typing import Dict, Any, Tuple
from django.conf import settings
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from django.contrib.auth.models import User
from resumes.models import Resume

from .base_source import BaseBrowserSource
from ..base import FormDetectionResult
from ..field_mapper import ProfileFieldMapper
from ..form_detector import FormDetector
from ..resume_uploader import ResumeUploader
from ..exceptions import (
    BrowserAutomationError,
    CaptchaDetectedError,
    LoginRequiredError,
    FormNotFoundError,
    SubmissionConfirmationRequiredError,
    AutomationTimeoutError,
)

logger = logging.getLogger(__name__)


class GenericBrowserSource(BaseBrowserSource):
    """
    Generic portal connector that handles modern career portals, Greenhouse,
    Lever, and custom direct application forms.
    """
    source_name = "Generic"

    def navigate_and_detect(self, page: Page, job_url: str, user: User) -> FormDetectionResult:
        logger.info(f"Navigating to job URL: {job_url}")
        try:
            page.goto(job_url, timeout=35000, wait_until='domcontentloaded')
            page.wait_for_timeout(1500)  # Brief pause for client-side hydration
        except PlaywrightTimeoutError as e:
            raise AutomationTimeoutError(f"Navigation timed out while opening {job_url}") from e
        except Exception as e:
            raise BrowserAutomationError(f"Failed to open {job_url}: {str(e)}") from e

        detector = FormDetector(page)
        mapper = ProfileFieldMapper(user)

        # 1. Check for CAPTCHA
        if detector.check_for_captcha():
            raise CaptchaDetectedError("A CAPTCHA or bot verification challenge was detected. Automation stopped for safety.")

        # 2. Check for Login Wall
        if detector.check_for_login():
            raise LoginRequiredError("External portal requires login credentials to access application form.")

        # 3. First detection attempt on current page
        detection = detector.detect_form_elements(mapper)

        # 4. If no form fields found, attempt to click an 'Apply' or 'Apply Now' button
        if not detection.found or (len(detection.detected_inputs) == 0 and not detection.has_file_input):
            apply_btn = detector.find_apply_button()
            if apply_btn:
                logger.info("Found apply trigger button. Clicking to reveal form...")
                try:
                    apply_btn.click()
                    page.wait_for_timeout(2000)
                    detection = detector.detect_form_elements(mapper)
                except Exception as e:
                    logger.warning(f"Could not click apply button: {e}")

        # Check captcha again after any modal trigger
        if detector.check_for_captcha():
            raise CaptchaDetectedError("CAPTCHA detected after clicking apply button. Halting automation.")

        return detection

    def fill_form_fields(
        self,
        page: Page,
        user: User,
        resume: Resume,
        detection: FormDetectionResult
    ) -> Tuple[Dict[str, Any], FormDetectionResult]:
        """
        Fills known profile fields into detected form inputs, attaches resume,
        and leaves unknown questions untouched for human review.
        """
        mapper = ProfileFieldMapper(user)
        filled_fields: Dict[str, Any] = {}

        # 1. Fill detected inputs
        for inp in detection.detected_inputs:
            category, val = mapper.identify_field(inp)
            if not category or not val:
                continue

            field_ident = inp.get('name') or inp.get('id')
            if not field_ident:
                continue

            tag = inp.get('tag', 'input')
            el_type = inp.get('type', 'text')

            # Select the element using name or id
            selector = f"{tag}[name='{field_ident}']" if inp.get('name') else f"#{inp.get('id')}"

            try:
                elem = page.locator(selector).first
                if elem.count() > 0 and elem.is_visible(timeout=1000):
                    if tag == 'select':
                        # Try to select option by label or value
                        try:
                            elem.select_option(label=str(val))
                        except Exception:
                            elem.select_option(value=str(val))
                    elif el_type in ('checkbox', 'radio'):
                        if str(val).lower() in ('true', 'yes', '1'):
                            elem.check()
                    else:
                        elem.fill(str(val))

                    filled_fields[category] = val
                    logger.info(f"Filled '{category}' with value: {val}")
            except Exception as e:
                logger.warning(f"Could not fill field {field_ident} ({category}): {e}")

        # 2. Upload resume if available
        if resume:
            try:
                uploader = ResumeUploader(page, resume)
                success, msg = uploader.upload()
                if success:
                    filled_fields['resume'] = resume.filename or resume.name
            except Exception as e:
                logger.warning(f"Resume upload failed: {e}")

        # 3. Refresh unknown questions list with current form values
        detector = FormDetector(page)
        fresh_detection = detector.detect_form_elements(mapper)

        return filled_fields, fresh_detection

    def submit(self, page: Page, user_confirmed: bool) -> Tuple[bool, str]:
        """
        Executes submission only when explicitly confirmed by user.
        """
        if not user_confirmed:
            raise SubmissionConfirmationRequiredError("User review and confirmation is strictly required before submission.")

        # In test mode, we avoid submitting external portals unless expressly enabled
        if getattr(settings, 'AUTOMATION_TEST_MODE', True):
            logger.info("[TEST MODE] AUTOMATION_TEST_MODE is True. Simulating successful submission confirmation.")
            return True, "Test mode: Application submission confirmed and simulated successfully."

        # Locate submit button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit application")',
            'button:has-text("Submit")',
            'button:has-text("Apply now")',
        ]

        submit_btn = None
        for sel in submit_selectors:
            try:
                btn = page.locator(sel)
                if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                    submit_btn = btn.first
                    break
            except Exception:
                continue

        if not submit_btn:
            raise FormNotFoundError("Submission button could not be located on final review page.")

        try:
            submit_btn.click()
            page.wait_for_timeout(3000)
            return True, "Application successfully submitted to external portal."
        except Exception as e:
            raise BrowserAutomationError(f"Error clicking final submission button: {e}")
