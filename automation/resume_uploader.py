import os
import logging
from typing import Tuple
from playwright.sync_api import Page
from resumes.models import Resume
from .exceptions import ResumeMissingError

logger = logging.getLogger(__name__)


class ResumeUploader:
    """
    Handles reliable resume attachment onto file input controls in web forms.
    Safely locates file inputs and uploads the designated candidate PDF resume.
    """
    def __init__(self, page: Page, resume: Resume):
        self.page = page
        self.resume = resume

    def upload(self) -> Tuple[bool, str]:
        """
        Locates the resume file on disk and attaches it to the application form.
        """
        if not self.resume:
            raise ResumeMissingError("No resume attached to this application.")

        if not self.resume.file or not os.path.exists(self.resume.file.path):
            raise ResumeMissingError(
                f"Resume file '{self.resume.name}' could not be found at path: "
                f"{getattr(self.resume.file, 'path', 'N/A')}"
            )

        file_path = os.path.abspath(self.resume.file.path)
        file_name = os.path.basename(file_path)
        logger.info(f"Preparing to upload resume: {file_name} ({file_path})")

        # 1. Look for standard file inputs
        file_inputs = self.page.locator('input[type="file"]')
        count = file_inputs.count()

        if count > 0:
            # Prefer file input matching resume/cv keywords if multiple exist
            target_input = file_inputs.first
            for i in range(count):
                inp = file_inputs.nth(i)
                name = (inp.get_attribute('name') or '').lower()
                id_val = (inp.get_attribute('id') or '').lower()
                aria = (inp.get_attribute('aria-label') or '').lower()
                if any(kw in f"{name} {id_val} {aria}" for kw in ['resume', 'cv', 'file', 'attachment']):
                    target_input = inp
                    break

            try:
                target_input.set_input_files(file_path)
                logger.info(f"Resume {file_name} attached via file input.")
                return True, f"Resume '{file_name}' attached successfully."
            except Exception as e:
                logger.warning(f"Direct set_input_files on file input failed: {e}")

        # 2. Try file chooser event by clicking upload buttons
        upload_buttons = [
            'button:has-text("Upload resume")',
            'button:has-text("Upload CV")',
            'button:has-text("Attach resume")',
            'label:has-text("Upload resume")',
            'label:has-text("Upload CV")',
            '[data-automation-id*="resume"]',
        ]

        for selector in upload_buttons:
            try:
                btn = self.page.locator(selector)
                if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                    with self.page.expect_file_chooser(timeout=3000) as fc_info:
                        btn.first.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(file_path)
                    logger.info(f"Resume {file_name} attached via file chooser dialog.")
                    return True, f"Resume '{file_name}' attached successfully via upload dialog."
            except Exception:
                continue

        logger.info("No file upload input detected on current form stage.")
        return False, "No file upload input found on this application page."
