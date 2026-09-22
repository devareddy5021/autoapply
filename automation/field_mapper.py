import re
from typing import Dict, Any, Optional, Tuple
from django.contrib.auth.models import User
from .base import FieldMappingResult

FIELD_PATTERNS = {
    'first_name': [
        r'\bfirst[_\-\s]?name\b',
        r'\bfname\b',
        r'\bgiven[_\-\s]?name\b',
    ],
    'last_name': [
        r'\blast[_\-\s]?name\b',
        r'\blname\b',
        r'\bfamily[_\-\s]?name\b',
        r'\bsurname\b',
    ],
    'full_name': [
        r'\bfull[_\-\s]?name\b',
        r'\bcandidate[_\-\s]?name\b',
        r'\byour[_\-\s]?name\b',
        r'^name$',
    ],
    'email': [
        r'\bemail\b',
        r'\be-mail\b',
        r'\bmail\b',
    ],
    'phone': [
        r'\bphone\b',
        r'\bmobile\b',
        r'\bcontact[_\-\s]?number\b',
        r'\bcell\b',
        r'\btel\b',
    ],
    'location': [
        r'\bcity\b',
        r'\blocation\b',
        r'\bcurrent[_\-\s]?location\b',
        r'\baddress\b',
        r'\bresidence\b',
    ],
    'linkedin': [
        r'\blinkedin\b',
        r'\blinked[_\-\s]?in\b',
    ],
    'github': [
        r'\bgithub\b',
        r'\bgit[_\-\s]?hub\b',
    ],
    'portfolio': [
        r'\bportfolio\b',
        r'\bwebsite\b',
        r'\bpersonal[_\-\s]?site\b',
        r'\bhomepage\b',
    ],
    'experience_years': [
        r'\byears?\b.*\bexperience\b',
        r'\btotal[_\-\s]?experience\b',
        r'\byoe\b',
    ],
    'notice_period': [
        r'\bnotice[_\-\s]?period\b',
        r'\bavailability\b',
    ],
    'work_authorization': [
        r'\bwork[_\-\s]?auth\b',
        r'\blegally[_\-\s]?authorized\b',
        r'\bvisa[_\-\s]?status\b',
        r'\bsponsorship\b',
    ],
    'education': [
        r'\beducation\b',
        r'\bdegree\b',
        r'\buniversity\b',
        r'\bcollege\b',
    ],
}


class ProfileFieldMapper:
    """
    Intelligently maps candidate profile attributes to target form field selectors.
    Uses multi-attribute heuristics (name, id, type, label, placeholder, aria-label).
    """
    def __init__(self, user: User):
        self.user = user
        self.profile = getattr(user, 'profile', None)
        self.profile_data = self._extract_profile_data()

    def _extract_profile_data(self) -> Dict[str, str]:
        first_name = self.user.first_name
        last_name = self.user.last_name
        full_name = ""

        if self.profile and self.profile.full_name:
            full_name = self.profile.full_name
            if not first_name or not last_name:
                parts = full_name.split(maxsplit=1)
                first_name = first_name or parts[0]
                if len(parts) > 1:
                    last_name = last_name or parts[1]
        else:
            full_name = f"{first_name} {last_name}".strip() or self.user.username

        data = {
            'first_name': first_name or self.user.username,
            'last_name': last_name or "",
            'full_name': full_name,
            'email': self.user.email or "",
            'phone': self.profile.phone if self.profile else "",
            'location': self.profile.current_location if self.profile else "",
            'linkedin': self.profile.linkedin_url if self.profile else "",
            'github': self.profile.github_url if self.profile else "",
            'portfolio': self.profile.portfolio_url if self.profile else "",
            'experience_years': str(self.profile.years_of_experience) if self.profile and self.profile.years_of_experience else "0",
            'notice_period': str(self.profile.notice_period_days) if self.profile and self.profile.notice_period_days is not None else "30",
            'work_authorization': self.profile.work_authorization if self.profile else "",
            'education': self.profile.education if self.profile else "",
        }
        return data

    def identify_field(self, element_meta: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Inspects element metadata and returns (matched_category, matched_value).
        Returns (None, None) if the field is not a recognized profile field.
        """
        # Exclude password, hidden, submit, button, file fields
        el_type = (element_meta.get('type') or '').lower()
        if el_type in ('password', 'hidden', 'submit', 'button', 'file', 'image', 'reset'):
            return None, None

        # Build search text from all available element hints
        search_tokens = [
            element_meta.get('name', ''),
            element_meta.get('id', ''),
            element_meta.get('placeholder', ''),
            element_meta.get('label', ''),
            element_meta.get('aria_label', ''),
            element_meta.get('autocomplete', ''),
        ]
        combined_text = " ".join(t.lower() for t in search_tokens if t)

        # Explicit HTML5 types
        if el_type == 'email' and self.profile_data.get('email'):
            return 'email', self.profile_data['email']
        if el_type == 'tel' and self.profile_data.get('phone'):
            return 'phone', self.profile_data['phone']

        # Autocomplete attribute mapping
        autocomplete = (element_meta.get('autocomplete') or '').lower()
        if autocomplete:
            if 'given-name' in autocomplete:
                return 'first_name', self.profile_data.get('first_name')
            if 'family-name' in autocomplete:
                return 'last_name', self.profile_data.get('last_name')
            if 'name' in autocomplete:
                return 'full_name', self.profile_data.get('full_name')
            if 'email' in autocomplete:
                return 'email', self.profile_data.get('email')
            if 'tel' in autocomplete:
                return 'phone', self.profile_data.get('phone')

        # Check regex rules in order of specificity
        # First name before full name
        for pattern in FIELD_PATTERNS['first_name']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'first_name', self.profile_data.get('first_name')

        for pattern in FIELD_PATTERNS['last_name']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'last_name', self.profile_data.get('last_name')

        for pattern in FIELD_PATTERNS['email']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'email', self.profile_data.get('email')

        for pattern in FIELD_PATTERNS['phone']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'phone', self.profile_data.get('phone')

        for pattern in FIELD_PATTERNS['linkedin']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'linkedin', self.profile_data.get('linkedin')

        for pattern in FIELD_PATTERNS['github']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'github', self.profile_data.get('github')

        for pattern in FIELD_PATTERNS['portfolio']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'portfolio', self.profile_data.get('portfolio')

        for pattern in FIELD_PATTERNS['location']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'location', self.profile_data.get('location')

        for pattern in FIELD_PATTERNS['experience_years']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'experience_years', self.profile_data.get('experience_years')

        for pattern in FIELD_PATTERNS['notice_period']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'notice_period', self.profile_data.get('notice_period')

        for pattern in FIELD_PATTERNS['work_authorization']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'work_authorization', self.profile_data.get('work_authorization')

        for pattern in FIELD_PATTERNS['education']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'education', self.profile_data.get('education')

        for pattern in FIELD_PATTERNS['full_name']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return 'full_name', self.profile_data.get('full_name')

        return None, None
