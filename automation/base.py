import abc
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class QuestionItem:
    """Represents a form question detected on the application page."""
    question_text: str
    field_name: str
    field_id: str = ""
    input_type: str = "text"  # text, textarea, select, radio, checkbox, file
    options: List[str] = field(default_factory=list)
    is_required: bool = False
    current_value: str = ""
    answered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'question_text': self.question_text,
            'field_name': self.field_name,
            'field_id': self.field_id,
            'input_type': self.input_type,
            'options': self.options,
            'is_required': self.is_required,
            'current_value': self.current_value,
            'answered': self.answered,
        }


@dataclass
class FieldMappingResult:
    """Result of mapping user profile data into detected application inputs."""
    mapped_fields: Dict[str, Any] = field(default_factory=dict)
    unmapped_fields: List[str] = field(default_factory=list)
    skipped_fields: List[str] = field(default_factory=list)


@dataclass
class FormDetectionResult:
    """Analysis result of page application structure."""
    found: bool = False
    form_selector: Optional[str] = None
    has_file_input: bool = False
    file_input_selector: Optional[str] = None
    detected_inputs: List[Dict[str, Any]] = field(default_factory=list)
    unknown_questions: List[QuestionItem] = field(default_factory=list)
    captcha_detected: bool = False
    login_required: bool = False
    page_title: str = ""
    current_url: str = ""


@dataclass
class AutomationResult:
    """Outcome of a browser automation run or stage."""
    success: bool
    status: str
    message: str
    filled_fields: Dict[str, Any] = field(default_factory=dict)
    detected_questions: List[Dict[str, Any]] = field(default_factory=list)
    error_details: str = ""
    logs: List[str] = field(default_factory=list)


class BaseJobSource(abc.ABC):
    """
    Abstract base class for all external job sources / connectors.
    Each connector manages discovery, validation, and interaction rules
    in strict adherence to site permissions and legal terms.
    """
    source_name: str = "Base"
    is_api_supported: bool = False
    is_browser_supported: bool = False

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abc.abstractmethod
    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        """
        Discovers jobs matching search criteria.
        Returns a list of normalized job dictionaries.
        """
        pass

    @abc.abstractmethod
    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed description and requirement parameters for a specific job URL.
        """
        pass

    def can_automate_application(self, job_url: str) -> bool:
        """
        Validates whether browser automation is permitted and technically supported
        for the given job URL.
        """
        return self.is_browser_supported


class LinkedInSource(BaseJobSource):
    source_name = "LinkedIn"
    is_api_supported = True
    is_browser_supported = False  # Direct scraping disallowed; requires verified API or manual/direct links

    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_name}] Discovery query='{query}', location='{location}'")
        return []

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None


class IndeedSource(BaseJobSource):
    source_name = "Indeed"
    is_api_supported = True
    is_browser_supported = False

    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_name}] Discovery query='{query}', location='{location}'")
        return []

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None


class NaukriSource(BaseJobSource):
    source_name = "Naukri"
    is_api_supported = False
    is_browser_supported = False

    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_name}] Discovery query='{query}', location='{location}'")
        return []

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None


class WellfoundSource(BaseJobSource):
    source_name = "Wellfound"
    is_api_supported = True
    is_browser_supported = False

    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_name}] Discovery query='{query}', location='{location}'")
        return []

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None


class GenericSource(BaseJobSource):
    """
    Generic job portal / ATS source (Greenhouse, Lever, Workday, company career sites, direct HTML forms).
    Allows browser navigation, form detection, field filling, and review.
    """
    source_name = "Generic"
    is_api_supported = False
    is_browser_supported = True

    def search_jobs(self, query: str, location: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        return []

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None

    def can_automate_application(self, job_url: str) -> bool:
        return True


CONNECTORS = {
    'LINKEDIN': LinkedInSource,
    'INDEED': IndeedSource,
    'NAUKRI': NaukriSource,
    'WELLFOUND': WellfoundSource,
    'GENERIC': GenericSource,
}

def get_job_source_connector(source_key: str) -> Optional[BaseJobSource]:
    """Factory helper to obtain a connector instance by source key."""
    connector_cls = CONNECTORS.get((source_key or '').upper(), GenericSource)
    if connector_cls:
        return connector_cls()
    return GenericSource()

