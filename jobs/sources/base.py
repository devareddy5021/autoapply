"""
Base Job Source Interface for JobAutoApply (Milestone 3).

Defines the pluggable connector architecture for all job aggregation sources.
All source connectors must adhere to this interface and output a standardized
normalized job schema.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone


class BaseJobSource:
    """
    Abstract base class for all job source connectors.
    """
    name: str = "base"
    display_name: str = "Base Source"
    is_available: bool = True
    requires_api_key: bool = False
    is_scraping_restricted: bool = False
    restriction_reason: str = ""
    rate_limit_seconds: float = 2.0

    def search(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Executes a job search on the target source.
        Returns a list of raw job dictionaries.
        """
        raise NotImplementedError("Subclasses must implement the search method.")

    def normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a raw job dictionary into the standard schema:
        {
            "title": str,
            "company": str,
            "location": str,
            "work_mode": "REMOTE" | "HYBRID" | "ONSITE",
            "description": str,
            "skills": List[str],
            "salary": str,
            "experience": str,
            "source": str,
            "source_job_id": str,
            "url": str,
            "posted_at": Optional[datetime] or ISO string
        }
        """
        raise NotImplementedError("Subclasses must implement the normalize_job method.")

    def fetch_and_normalize(self, query: str, location: Optional[str] = None, remote: bool = False) -> List[Dict[str, Any]]:
        """
        Convenience method to search and normalize in one pass, safely handling errors per job.
        """
        raw_jobs = self.search(query, location=location, remote=remote)
        normalized = []
        for raw in raw_jobs:
            try:
                norm = self.normalize_job(raw)
                if norm and norm.get('title') and norm.get('company'):
                    normalized.append(norm)
            except Exception as e:
                continue
        return normalized
