import threading
import logging
from typing import Optional
from django import db
from applications.models import Application
from .application_runner import ApplicationRunner
from .base import AutomationResult

logger = logging.getLogger(__name__)


def _run_preparation_worker(application_id: int, headless: Optional[bool] = None):
    """Background thread target for application preparation."""
    db.connections.close_all()
    try:
        app = Application.objects.select_related('user', 'job', 'resume', 'user__profile').get(pk=application_id)
        runner = ApplicationRunner(app, headless=headless)
        runner.run_preparation()
    except Exception as e:
        logger.exception(f"Background automation failed for application {application_id}: {e}")
    finally:
        db.connections.close_all()


def _run_submission_worker(application_id: int, headless: Optional[bool] = None):
    """Background thread target for confirmed submission."""
    db.connections.close_all()
    try:
        app = Application.objects.select_related('user', 'job', 'resume', 'user__profile').get(pk=application_id)
        runner = ApplicationRunner(app, headless=headless)
        runner.run_submission(user_confirmed=True)
    except Exception as e:
        logger.exception(f"Background submission failed for application {application_id}: {e}")
    finally:
        db.connections.close_all()


class AutomationManager:
    """
    High-level facade to launch, monitor, or submit automated applications.
    Supports asynchronous thread dispatch and synchronous execution for tests.
    """

    @staticmethod
    def start_preparation(application: Application, async_exec: bool = True, headless: Optional[bool] = None) -> AutomationResult:
        """
        Starts the automated preparation phase (navigating, detecting, filling, halting at review).
        """
        application.status = Application.Status.QUEUED
        application.automation_status = Application.AutomationStatus.QUEUED
        application.save(update_fields=['status', 'automation_status', 'updated_at'])

        if async_exec:
            thread = threading.Thread(
                target=_run_preparation_worker,
                args=(application.pk, headless),
                name=f"AutomationPrep-{application.pk}",
                daemon=True
            )
            thread.start()
            return AutomationResult(
                success=True,
                status="QUEUED",
                message="Application preparation queued in background worker."
            )
        else:
            runner = ApplicationRunner(application, headless=headless)
            return runner.run_preparation()

    @staticmethod
    def submit_application(application: Application, async_exec: bool = True, headless: Optional[bool] = None) -> AutomationResult:
        """
        Executes final submission after explicit human review and confirmation.
        """
        if async_exec:
            thread = threading.Thread(
                target=_run_submission_worker,
                args=(application.pk, headless),
                name=f"AutomationSubmit-{application.pk}",
                daemon=True
            )
            thread.start()
            return AutomationResult(
                success=True,
                status="SUBMITTING",
                message="Submission dispatched to background worker."
            )
        else:
            runner = ApplicationRunner(application, headless=headless)
            return runner.run_submission(user_confirmed=True)
