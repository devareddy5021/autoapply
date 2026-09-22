import re
import logging
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, Locator
from .base import FormDetectionResult, QuestionItem
from .field_mapper import ProfileFieldMapper

logger = logging.getLogger(__name__)

CAPTCHA_SELECTORS = [
    'iframe[src*="recaptcha"]',
    'iframe[src*="hcaptcha"]',
    'iframe[src*="turnstile"]',
    'div.g-recaptcha',
    'div.h-captcha',
    'div#cf-turnstile',
    '#cf-challenge-running',
    '.cf-browser-verification',
]

APPLY_BUTTON_PATTERNS = [
    r'\beasy\s+apply\b',
    r'\bapply\s+now\b',
    r'\bapply\s+for\s+this\s+job\b',
    r'\bapply\s+online\b',
    r'\bapply\b',
    r'\bsubmit\s+application\b',
]


class FormDetector:
    """
    Scans a web page to:
    1. Detect CAPTCHA or verification challenges
    2. Detect 'Apply' or 'Easy Apply' action triggers
    3. Detect application form boundaries
    4. Extract form inputs and identify unknown custom questions
    """
    def __init__(self, page: Page):
        self.page = page

    def check_for_captcha(self) -> bool:
        """Inspects DOM for known CAPTCHA / bot challenge indicators."""
        for selector in CAPTCHA_SELECTORS:
            try:
                locator = self.page.locator(selector)
                if locator.count() > 0 and locator.first.is_visible(timeout=500):
                    logger.warning(f"CAPTCHA detected via selector: {selector}")
                    return True
            except Exception:
                continue
        return False

    def check_for_login(self) -> bool:
        """Checks if the page redirects to a login portal."""
        url = self.page.url.lower()
        if any(keyword in url for keyword in ['/login', '/signin', 'accounts.google.com', 'auth0', 'auth/login']):
            return True
        return False

    def find_apply_button(self) -> Optional[Locator]:
        """Searches for an 'Apply' or 'Easy Apply' button on the page."""
        for pattern in APPLY_BUTTON_PATTERNS:
            try:
                # Try finding button or link with matching text
                button = self.page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
                if button.count() > 0 and button.first.is_visible(timeout=1000):
                    return button.first
            except Exception:
                pass

            try:
                link = self.page.get_by_role("link", name=re.compile(pattern, re.IGNORECASE))
                if link.count() > 0 and link.first.is_visible(timeout=1000):
                    return link.first
            except Exception:
                pass

        # Fallback CSS selectors
        fallback_selectors = [
            'button[id*="apply" i]',
            'a[id*="apply" i]',
            'button[class*="apply" i]',
            'a[class*="apply" i]',
            '[data-automation-id*="apply" i]',
        ]
        for sel in fallback_selectors:
            try:
                elem = self.page.locator(sel)
                if elem.count() > 0 and elem.first.is_visible(timeout=1000):
                    return elem.first
            except Exception:
                continue

        return None

    def detect_form_elements(self, mapper: ProfileFieldMapper) -> FormDetectionResult:
        """
        Extracts all relevant form inputs, matches them against user profile,
        and flags unknown questions requiring human verification.
        """
        result = FormDetectionResult(
            page_title=self.page.title(),
            current_url=self.page.url,
        )

        if self.check_for_captcha():
            result.captcha_detected = True
            return result

        if self.check_for_login():
            result.login_required = True
            return result

        # Check for file upload input
        try:
            file_inputs = self.page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                result.has_file_input = True
                result.file_input_selector = 'input[type="file"]'
        except Exception:
            pass

        # Locate form inputs (inputs, textareas, selects)
        # Note: JavaScript extraction inside page context is fast and reliable
        try:
            elements_data = self.page.evaluate('''() => {
                const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                return inputs.map((el, index) => {
                    let labelText = '';
                    if (el.id) {
                        const labelEl = document.querySelector(`label[for="${el.id}"]`);
                        if (labelEl) labelText = labelEl.innerText;
                    }
                    if (!labelText && el.closest('label')) {
                        labelText = el.closest('label').innerText;
                    }

                    let options = [];
                    if (el.tagName.toLowerCase() === 'select') {
                        options = Array.from(el.options).map(o => o.text.trim()).filter(Boolean);
                    }

                    return {
                        index: index,
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type') || (el.tagName.toLowerCase() === 'textarea' ? 'textarea' : 'text'),
                        name: el.getAttribute('name') || '',
                        id: el.getAttribute('id') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        aria_label: el.getAttribute('aria-label') || '',
                        autocomplete: el.getAttribute('autocomplete') || '',
                        required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
                        label: labelText.trim(),
                        options: options,
                        value: el.value || '',
                        isVisible: el.offsetParent !== null
                    };
                });
            }''')
        except Exception as e:
            logger.error(f"Failed to inspect DOM inputs: {e}")
            elements_data = []

        seen_unknown_names = set()

        for el in elements_data:
            if not el.get('isVisible'):
                continue

            tag = el.get('tag')
            el_type = el.get('type', '').lower()

            if el_type in ('hidden', 'submit', 'button', 'reset'):
                continue

            result.detected_inputs.append(el)

            # Check if this input matches a known profile field
            category, matched_val = mapper.identify_field(el)

            if not category and el_type != 'file':
                # This is an unknown or custom question!
                q_text = el.get('label') or el.get('placeholder') or el.get('aria_label') or el.get('name') or "Question"
                clean_q_text = re.sub(r'\s+', ' ', q_text).strip()
                field_ident = el.get('name') or el.get('id') or f"field_{el.get('index')}"

                if field_ident not in seen_unknown_names and len(clean_q_text) > 1:
                    seen_unknown_names.add(field_ident)
                    result.unknown_questions.append(QuestionItem(
                        question_text=clean_q_text,
                        field_name=field_ident,
                        field_id=el.get('id', ''),
                        input_type=el_type,
                        options=el.get('options', []),
                        is_required=el.get('required', False),
                        current_value=el.get('value', ''),
                        answered=bool(el.get('value', '').strip())
                    ))

        result.found = len(result.detected_inputs) > 0 or result.has_file_input
        return result
