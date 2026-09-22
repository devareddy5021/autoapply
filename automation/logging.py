import os
import re
import logging
from typing import Optional
from django.utils import timezone
from applications.models import Application, AutomationLog

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


logger = logging.getLogger('automation')

SENSITIVE_PATTERNS = [
    re.compile(r'(password|token|secret|bearer|authorization|auth_token)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE),
    re.compile(r'(ghp_[a-zA-Z0-9]{30,})', re.IGNORECASE),
    re.compile(r'(eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]*)', re.IGNORECASE),
]

def sanitize_message(msg: str) -> str:
    """Removes sensitive credentials, tokens, or passwords from logs."""
    if not msg:
        return ""
    sanitized = str(msg)
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r'\1: [REDACTED]', sanitized)
    return sanitized


class ApplicationAuditLogger:
    """
    Sanitized logger that records human-readable audit trail entries in the database
    linked to a specific Application instance.
    """
    def __init__(self, application: Application):
        self.application = application

    def log(self, level: str, action: str, message: str) -> AutomationLog:
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        clean_msg = sanitize_message(message)
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"[App #{self.application.pk}] [{action}] {clean_msg}"
        )
        return AutomationLog.objects.create(
            application=self.application,
            level=level,
            action=action[:100],
            message=clean_msg
        )

    def info(self, action: str, message: str) -> AutomationLog:
        return self.log(AutomationLog.Level.INFO, action, message)

    def warning(self, action: str, message: str) -> AutomationLog:
        return self.log(AutomationLog.Level.WARNING, action, message)

    def error(self, action: str, message: str) -> AutomationLog:
        return self.log(AutomationLog.Level.ERROR, action, message)

    def success(self, action: str, message: str) -> AutomationLog:
        return self.log(AutomationLog.Level.SUCCESS, action, message)
