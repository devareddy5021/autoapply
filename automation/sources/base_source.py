import abc
from typing import Dict, Any, Tuple
from playwright.sync_api import Page
from django.contrib.auth.models import User
from resumes.models import Resume
from ..base import FormDetectionResult, AutomationResult


class BaseBrowserSource(abc.ABC):
    """
    Abstract interface for website-specific or generic browser application workflows.
    """
    source_name: str = "BaseBrowser"

    @abc.abstractmethod
    def navigate_and_detect(self, page: Page, job_url: str, user: User) -> FormDetectionResult:
        """Navigates to the job page and determines the application state/form."""
        pass

    @abc.abstractmethod
    def fill_form_fields(
        self,
        page: Page,
        user: User,
        resume: Resume,
        detection: FormDetectionResult
    ) -> Tuple[Dict[str, Any], FormDetectionResult]:
        """Fills known candidate fields and uploads resume without submitting."""
        pass

    @abc.abstractmethod
    def submit(self, page: Page, user_confirmed: bool) -> Tuple[bool, str]:
        """Executes the final application submission after human confirmation."""
        pass
