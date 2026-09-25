"""
Job Sources Package and Registry for JobAutoApply (Milestone 3).

Exposes all configured connectors and provides registry lookup functions.
"""

from typing import Dict, List, Type, Optional
from .base import BaseJobSource
from .linkedin import LinkedInJobSource
from .naukri import NaukriJobSource
from .indeed import IndeedJobSource
from .foundit import FounditJobSource
from .internshala import InternshalaJobSource
from .wellfound import WellfoundJobSource
from .cutshort import CutshortJobSource
from .instahyre import InstahyreJobSource
from .remotive import RemotiveJobSource
from .arbeitnow import ArbeitnowJobSource

# Registry of all connector classes
SOURCE_REGISTRY: Dict[str, Type[BaseJobSource]] = {
    'linkedin': LinkedInJobSource,
    'remotive': RemotiveJobSource,
    'arbeitnow': ArbeitnowJobSource,
    'naukri': NaukriJobSource,
    'indeed': IndeedJobSource,
    'foundit': FounditJobSource,
    'internshala': InternshalaJobSource,
    'wellfound': WellfoundJobSource,
    'cutshort': CutshortJobSource,
    'instahyre': InstahyreJobSource,
}


def get_source_connector(source_name: str) -> Optional[BaseJobSource]:
    """Retrieves an instantiated connector by name, or None."""
    cls = SOURCE_REGISTRY.get(source_name.lower().strip())
    if cls:
        return cls()
    return None


def get_all_connectors() -> List[BaseJobSource]:
    """Returns a list of all instantiated connectors."""
    return [cls() for cls in SOURCE_REGISTRY.values()]


__all__ = [
    'BaseJobSource',
    'LinkedInJobSource',
    'RemotiveJobSource',
    'ArbeitnowJobSource',
    'NaukriJobSource',
    'IndeedJobSource',
    'FounditJobSource',
    'InternshalaJobSource',
    'WellfoundJobSource',
    'CutshortJobSource',
    'InstahyreJobSource',
    'SOURCE_REGISTRY',
    'get_source_connector',
    'get_all_connectors',
]
