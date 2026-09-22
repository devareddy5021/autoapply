import abc
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

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
        return False


class LinkedInSource(BaseJobSource):
    source_name = "LinkedIn"
    is_api_supported = True
    is_browser_supported = False  # Explicit compliance restriction

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


CONNECTORS = {
    'LINKEDIN': LinkedInSource,
    'INDEED': IndeedSource,
    'NAUKRI': NaukriSource,
    'WELLFOUND': WellfoundSource,
}

def get_job_source_connector(source_key: str) -> Optional[BaseJobSource]:
    """Factory helper to obtain a connector instance by source key."""
    connector_cls = CONNECTORS.get(source_key.upper())
    if connector_cls:
        return connector_cls()
    return None
