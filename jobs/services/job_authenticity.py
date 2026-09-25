"""
Job Authenticity and Scam / Ghost Job Detector for JobAutoApply.
Detects verified direct corporate employers, third-party staffing consultancies,
and suspicious/scam postings (fees, personal emails, ghost templates).
"""

import re
from typing import Dict, Any, List, Optional

VERIFIED_ENTERPRISES = {
    'flipkart', 'amazon', 'google', 'microsoft', 'deloitte', 'swiggy', 'tcs',
    'tata consultancy services', 'infosys', 'zomato', 'phonepe', 'razorpay',
    'cred', 'meesho', 'inmobi', 'paytm', 'ibm', 'cisco', 'ey', 'ernest & young',
    'pwc', 'accenture', 'schneider electric', 'browserstack', 'postman', 'hasura',
    'zepto', 'dream11', 'freshworks', 'ltimindtree', 'hcl', 'hcl technologies',
    'walmart', 'jpmorgan', 'jpmorganchase', 'goldman sachs', 'morgan stanley',
    'uber', 'netflix', 'atlassian', 'salesforce', 'oracle', 'sap', 'adobe',
    'intuit', 'meta', 'apple', 'nvidia', 'intel', 'qualcomm', 'amd', 'cisco systems',
    'siemens', 'bosch', 'honeywell', 'snaptravel', 'snap analytics', 'innover digital'
}

KNOWN_TRUSTED_ATS_DOMAINS = [
    'greenhouse.io', 'lever.co', 'workday.com', 'myworkdayjobs.com',
    'smartrecruiters.com', 'ashbyhq.com', 'taleo.net', 'icims.com',
    'bamboohr.com', 'jobvite.com', 'recruitee.com', 'flipkartcareers.com',
    'amazon.jobs', 'careers.google.com', 'careers.microsoft.com'
]

SCAM_FEE_PATTERNS = [
    r'\b(?:registration|training|processing|security|documentation|laptop)\s*(?:fee|fees|charge|charges|deposit|cost|amount)\b',
    r'\b(?:pay|deposit|transfer)\s*(?:before|for|to)\s*(?:interview|joining|offer|selection)\b',
    r'\b(?:100%|guaranteed)\s*(?:placement|job)\s*(?:with|after)\s*(?:fee|payment|paid)\b',
]

THIRD_PARTY_AGENCY_PATTERNS = [
    r'\b(?:client\s+of|hiring\s+for\s+(?:our\s+)?client|reputed\s+(?:mnc\s+)?client|tier[\s\-]1\s+client)\b',
    r'\b(?:payroll\s+of|third[\s\-]party\s+payroll|contract\s+to\s+hire\s+for\s+client)\b',
    r'\b(?:staffing\s+solutions|manpower\s+services|recruitment\s+firm|consultancy\s+firm|placement\s+agency)\b',
    r'\b(?:walk[\s\-]in\s+at\s+consultancy|submit\s+cv\s+for\s+future\s+client\s+roles)\b',
]

FREE_EMAIL_PATTERNS = [
    r'[a-zA-Z0-9_.+-]+@(gmail|yahoo|hotmail|outlook|rediffmail)\.[a-zA-Z]{2,}',
]


def evaluate_job_authenticity(job) -> Dict[str, Any]:
    """
    Evaluates a job posting's authenticity, returning a trust score (0-100),
    authenticity level, badges, and actionable reasons.
    """
    company = (getattr(job, 'company_name', '') or '').strip()
    company_lower = company.lower()
    title = (getattr(job, 'title', '') or '').strip()
    desc = (getattr(job, 'description', '') or '').strip()
    desc_lower = desc.lower()
    url = (getattr(job, 'external_url', '') or '').lower()
    source = (getattr(job, 'source', '') or '').upper()

    score = 70  # Baseline neutral score
    flags: List[str] = []
    level = 'AUTHENTIC'

    # 1. Check for Scam / Fee triggers (Immediate Red Flag)
    for pat in SCAM_FEE_PATTERNS:
        if re.search(pat, desc_lower, re.IGNORECASE):
            score -= 50
            flags.append("Warning: Mentions upfront fee, deposit, or paid training")
            level = 'SUSPICIOUS'
            break

    # 2. Check for personal/free email address in JD
    for pat in FREE_EMAIL_PATTERNS:
        m = re.search(pat, desc)
        if m and company_lower not in ('freelance', 'independent'):
            score -= 25
            flags.append(f"Uses public email domain ({m.group(1)}) instead of corporate domain")
            if level != 'SUSPICIOUS':
                level = 'THIRD_PARTY'
            break

    # 3. Check for Third-Party Staffing / Consultancy indicators
    for pat in THIRD_PARTY_AGENCY_PATTERNS:
        if re.search(pat, desc_lower, re.IGNORECASE):
            score -= 20
            flags.append("Third-party recruiter / staffing agency hiring for client")
            if level == 'AUTHENTIC':
                level = 'THIRD_PARTY'
            break

    # 4. Check if Known Verified Enterprise / Tech Unicorn
    is_verified_company = any(
        k in company_lower or company_lower in k
        for k in VERIFIED_ENTERPRISES
    )

    if is_verified_company:
        score += 25
        flags.append(f"Verified enterprise employer: {company}")
        if level != 'SUSPICIOUS':
            level = 'VERIFIED'

    # 5. Check URL authenticity (Official ATS or direct company page)
    is_trusted_ats = any(ats in url for ats in KNOWN_TRUSTED_ATS_DOMAINS)
    if is_trusted_ats:
        score += 15
        flags.append("Direct enterprise ATS application endpoint")
        if level != 'SUSPICIOUS':
            level = 'VERIFIED'

    # 6. Hollow / Ghost Job check (very short description or generic buzzwords)
    if len(desc) < 150 and not getattr(job, 'requirements', None):
        score -= 15
        flags.append("Limited job description details (ghost listing risk)")

    # Bound score
    final_score = max(5, min(100, score))

    if level == 'VERIFIED' or final_score >= 85:
        badge_label = "Verified Employer"
        badge_color = "success"
        badge_icon = "bi-patch-check-fill"
        summary = "Verified direct corporate employer"
    elif level == 'THIRD_PARTY' or (45 <= final_score < 75):
        badge_label = "Staffing Agency / Consultancy"
        badge_color = "warning"
        badge_icon = "bi-buildings"
        summary = "Third-party recruitment or client staffing"
    elif level == 'SUSPICIOUS' or final_score < 45:
        badge_label = "Caution: Unverified / High Risk"
        badge_color = "danger"
        badge_icon = "bi-shield-exclamation"
        summary = "Suspicious signals detected in job posting"
    else:
        badge_label = "Direct Tech Posting"
        badge_color = "primary"
        badge_icon = "bi-shield-check"
        summary = "Standard direct employer job posting"

    return {
        'score': final_score,
        'level': level,
        'badge_label': badge_label,
        'badge_color': badge_color,
        'badge_icon': badge_icon,
        'summary': summary,
        'flags': flags,
        'is_verified': (level == 'VERIFIED' or final_score >= 85),
        'is_suspicious': (level == 'SUSPICIOUS' or final_score < 45),
        'is_third_party': (level == 'THIRD_PARTY'),
    }
