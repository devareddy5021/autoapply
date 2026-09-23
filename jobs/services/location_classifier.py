"""
Location Classification Service for JobAutoApply (Milestone 3).

Strictly filters for India and Remote opportunities while discarding jobs
restricted to other countries (e.g. USA only, UK only, Europe only).
"""

import re
from typing import Dict, Any, List, Optional
from jobs.models import LocationType

# Primary and emerging Indian IT hubs
INDIAN_CITIES = [
    'bengaluru', 'bangalore', 'hyderabad', 'chennai', 'delhi', 'new delhi',
    'delhi ncr', 'noida', 'greater noida', 'gurugram', 'gurgaon', 'mumbai',
    'pune', 'ahmedabad', 'kolkata', 'kochi', 'cochin', 'jaipur', 'chandigarh',
    'indore', 'bhubaneswar', 'bhubaneshwar', 'visakhapatnam', 'vizag',
    'thiruvananthapuram', 'trivandrum', 'coimbatore', 'nagpur', 'mysore', 'mysuru',
    'surat', 'vadodara', 'baroda', 'lucknow', 'kanpur', 'patna', 'bhopal',
    'ludhiana', 'agra', 'nashik', 'rajkot', 'varanasi', 'srinagar', 'aurangabad',
    'dhanbad', 'amritsar', 'navi mumbai', 'allahabad', 'prayagraj', 'ranchi',
    'howrah', 'jabalpur', 'gwalior', 'vijayawada', 'jodhpur', 'raipur',
    'kota', 'guwahati', 'mangalore', 'mangaluru', 'dehradun'
]

INDIAN_STATES = [
    'karnataka', 'telangana', 'tamil nadu', 'maharashtra', 'delhi',
    'uttar pradesh', 'haryana', 'west bengal', 'gujarat', 'kerala',
    'rajasthan', 'punjab', 'madhya pradesh', 'odisha', 'andhra pradesh'
]

# Patterns explicitly restricting remote work to foreign jurisdictions
FOREIGN_RESTRICTIONS = [
    r'\busa?\s*only\b',
    r'\bunited states\s*(only)?\b',
    r'\bu\.?s\.?\s*only\b',
    r'\bu\.?s\.?\s*citizens?\b',
    r'\buk\s*only\b',
    r'\bunited kingdom\s*(only)?\b',
    r'\bcanada\s*only\b',
    r'\beurope\s*(only)?\b',
    r'\beu\s*only\b',
    r'\bgermany\s*only\b',
    r'\bfrance\s*only\b',
    r'\baustralia\s*only\b',
    r'\blatam\s*only\b',
    r'\bemea\s*only\b',
    r'\bapac\s*only\b',
    r'\bus\s*timezones?\b',
    r'\best\s*timezone\s*only\b',
    r'\bpst\s*timezone\s*only\b',
    r'\bcst\s*timezone\s*only\b',
    r'\bnorth america\s*(only)?\b',
]

# Known non-Indian international locations/cities
FOREIGN_LOCATIONS = [
    'london', 'berlin', 'munich', 'paris', 'tokyo', 'sydney', 'toronto',
    'vancouver', 'san francisco', 'new york', 'seattle', 'austin', 'chicago',
    'los angeles', 'boston', 'amsterdam', 'dublin', 'singapore', 'warsaw',
    'krakow', 'zurich', 'vienna', 'madrid', 'barcelona', 'sao paulo', 'buenos aires',
    'united states', 'united kingdom', 'germany', 'canada', 'australia', 'france',
    'netherlands', 'ireland', 'poland', 'spain', 'brazil', 'mexico'
]

# Remote keywords
REMOTE_TERMS = [
    'remote', 'work from home', 'wfh', 'telecommute', 'anywhere', 'worldwide', 'virtual', 'distributed'
]


def classify_location(
    location: str,
    work_mode: str = '',
    description: str = '',
    title: str = ''
) -> Dict[str, Any]:
    """
    Classifies a job's geographic eligibility.

    Returns:
    {
        "country": "India" | "Worldwide" | "Other",
        "is_india": True / False,
        "is_remote": True / False,
        "location_type": LocationType choice,
        "is_accepted": True / False,
        "matched_locations": [ ... ]
    }
    """
    loc_clean = (location or '').lower().strip()
    mode_clean = (work_mode or '').lower().strip()
    desc_clean = (description or '').lower()[:3000]
    title_clean = (title or '').lower()
    combined_text = f"{loc_clean} {desc_clean} {title_clean}"

    is_remote_flag = (
        'remote' in mode_clean or
        any(rt in loc_clean for rt in REMOTE_TERMS) or
        any(rt in title_clean for rt in ['remote', 'wfh'])
    )

    # 1. Check for explicit foreign-only restrictions
    has_foreign_restriction = False
    for pat in FOREIGN_RESTRICTIONS:
        if re.search(pat, loc_clean) or re.search(pat, desc_clean):
            has_foreign_restriction = True
            break

    if has_foreign_restriction:
        # If it says e.g. "Remote - US only" or "USA only", reject immediately
        return {
            'country': 'Foreign (Restricted)',
            'is_india': False,
            'is_remote': is_remote_flag,
            'location_type': LocationType.OUTSIDE_INDIA,
            'is_accepted': False,
            'matched_locations': ['Foreign restriction detected'],
        }

    # 2. Check for explicit foreign city/country without any India context
    has_foreign_loc = any(fl in loc_clean for fl in FOREIGN_LOCATIONS)
    has_india_mention = (
        'india' in loc_clean or
        any(c in loc_clean for c in INDIAN_CITIES) or
        any(s in loc_clean for s in INDIAN_STATES)
    )

    if has_foreign_loc and not has_india_mention:
        return {
            'country': 'Foreign',
            'is_india': False,
            'is_remote': is_remote_flag,
            'location_type': LocationType.OUTSIDE_INDIA,
            'is_accepted': False,
            'matched_locations': ['Foreign location'],
        }

    # 3. Detect Indian cities
    matched_indian_cities = [c for c in INDIAN_CITIES if c in loc_clean]
    if not matched_indian_cities and ('india' in loc_clean or any(s in loc_clean for s in INDIAN_STATES)):
        matched_indian_cities = ['india']

    # 4. Determine Location Type
    if is_remote_flag:
        # Remote India or Remote Worldwide
        if has_india_mention or 'india' in combined_text or 'in' in loc_clean:
            loc_type = LocationType.REMOTE_INDIA
            country = 'India'
            is_india = True
        elif any(gw in loc_clean for gw in ['worldwide', 'global', 'anywhere', 'work from anywhere']) or loc_clean in ('remote', 'virtual'):
            loc_type = LocationType.REMOTE_GLOBAL
            country = 'Worldwide'
            is_india = True  # Worldwide includes India candidates unless restricted
        else:
            loc_type = LocationType.REMOTE_INDIA if has_india_mention else LocationType.REMOTE_GLOBAL
            country = 'India' if has_india_mention else 'Worldwide'
            is_india = True

        return {
            'country': country,
            'is_india': is_india,
            'is_remote': True,
            'location_type': loc_type,
            'is_accepted': True,
            'matched_locations': matched_indian_cities or ['Remote'],
        }

    # Onsite / Hybrid with Indian Cities
    if len(matched_indian_cities) > 1:
        return {
            'country': 'India',
            'is_india': True,
            'is_remote': False,
            'location_type': LocationType.INDIA_MULTI_CITY,
            'is_accepted': True,
            'matched_locations': matched_indian_cities,
        }
    elif len(matched_indian_cities) == 1:
        return {
            'country': 'India',
            'is_india': True,
            'is_remote': False,
            'location_type': LocationType.INDIA_CITY,
            'is_accepted': True,
            'matched_locations': matched_indian_cities,
        }

    # No recognizable India city and not remote
    return {
        'country': 'Unknown',
        'is_india': False,
        'is_remote': False,
        'location_type': LocationType.UNKNOWN,
        'is_accepted': False,
        'matched_locations': [],
    }
