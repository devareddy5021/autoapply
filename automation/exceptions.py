"""
Custom exception hierarchy for the browser automation layer.
"""

class BrowserAutomationError(Exception):
    """Base exception for all automation errors."""
    def __init__(self, message: str, step: str = "", details: str = ""):
        super().__init__(message)
        self.message = message
        self.step = step
        self.details = details

    def __str__(self):
        if self.step:
            return f"[{self.step}] {self.message}"
        return self.message


class LoginRequiredError(BrowserAutomationError):
    """Raised when an external portal requires user authentication."""
    pass


class CaptchaDetectedError(BrowserAutomationError):
    """Raised when CAPTCHA or bot verification challenge is encountered.
    In accordance with safety guidelines, automation immediately halts.
    """
    pass


class JobUnavailableError(BrowserAutomationError):
    """Raised when the job posting has expired, is closed, or returned 404."""
    pass


class FormNotFoundError(BrowserAutomationError):
    """Raised when no application button or form fields could be located."""
    pass


class ResumeMissingError(BrowserAutomationError):
    """Raised when the application has no resume assigned or the PDF is missing."""
    pass


class AutomationTimeoutError(BrowserAutomationError):
    """Raised when page loading or navigation exceeds configured timeouts."""
    pass


class SubmissionConfirmationRequiredError(BrowserAutomationError):
    """Raised when submission is attempted without explicit human-in-the-loop review."""
    pass
