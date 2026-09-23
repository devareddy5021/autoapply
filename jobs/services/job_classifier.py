"""
Data-Role Job Classification Service for JobAutoApply (Milestone 3).

Strictly identifies and categorizes data-domain opportunities:
- DATA_ENGINEERING
- DATA_ANALYTICS
- DATA_SCIENCE
- MACHINE_LEARNING
- BI
- DATABASE
- OTHER (rejected)

Enforces primary-role validation: Non-data roles (e.g., Frontend, React,
DevOps, Java, Android, QA, Full Stack) mentioning 'data' or 'SQL' are
classified as OTHER and rejected.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from jobs.models import JobCategory

# Explicit Non-Tech Roles to Exclude
EXCLUDED_PRIMARY_ROLES = [
    r'\bsales\b',
    r'\bmarketing\b',
    r'\bhuman resources\b',
    r'\bhr\b',
    r'\brecruiter\b',
    r'\btalent acquisition\b',
    r'\baccountant\b',
    r'\bfinancial advisor\b',
    r'\blegal\b',
    r'\blawyer\b',
    r'\bmedical\b',
    r'\bnurse\b',
    r'\bcook\b',
    r'\bchef\b',
    r'\bdriver\b',
    r'\bstore manager\b',
    r'\btelecaller\b',
    r'\bcustomer service\b',
    r'\bcustomer support\b',
    r'\bcall center\b',
]

# Domain Title Patterns & Keywords
ROLE_DEFINITIONS: List[Tuple[str, List[str], List[str]]] = [
    (
        JobCategory.DATA_ENGINEERING,
        [
            r'\bdata engineer(ing)?\b',
            r'\betl developer\b',
            r'\betl engineer\b',
            r'\bbig data engineer\b',
            r'\bcloud data engineer\b',
            r'\bazure data engineer\b',
            r'\baws data engineer\b',
            r'\bgcp data engineer\b',
            r'\bdatabricks engineer\b',
            r'\bspark engineer\b',
            r'\bdata platform engineer\b',
            r'\banalytics engineer\b',
            r'\bdata pipeline\b',
            r'\bdata infrastructure\b',
        ],
        ['spark', 'pyspark', 'databricks', 'etl', 'airflow', 'kafka', 'hadoop', 'snowflake', 'dbt', 'data lake', 'pipeline']
    ),
    (
        JobCategory.MACHINE_LEARNING,
        [
            r'\bmachine learning\b',
            r'\bml engineer\b',
            r'\bai/ml\b',
            r'\bml/ai\b',
            r'\bai engineer\b',
            r'\bapplied scientist\b',
            r'\bdeep learning\b',
            r'\bnlp engineer\b',
            r'\bcomputer vision engineer\b',
            r'\bllm engineer\b',
            r'\bmlops\b',
        ],
        ['pytorch', 'tensorflow', 'scikit-learn', 'deep learning', 'nlp', 'computer vision', 'llm', 'mlops', 'model deployment']
    ),
    (
        JobCategory.DATA_SCIENCE,
        [
            r'\bdata scientist\b',
            r'\bdata science\b',
            r'\bapplied data scientist\b',
            r'\bdecision scientist\b',
            r'\bquantitative analyst\b',
            r'\bquant analyst\b',
        ],
        ['pandas', 'numpy', 'statistics', 'predictive modeling', 'machine learning', 'hypothesis testing', 'python', 'r']
    ),
    (
        JobCategory.BI,
        [
            r'\bbi developer\b',
            r'\bbusiness intelligence\b',
            r'\bbi engineer\b',
            r'\bpower bi\b',
            r'\btableau developer\b',
            r'\breporting analyst\b',
            r'\blooker developer\b',
            r'\bqlik developer\b',
        ],
        ['power bi', 'tableau', 'looker', 'dax', 'dashboard', 'reporting', 'kpi', 'qlik', 'business intelligence']
    ),
    (
        JobCategory.DATA_ANALYTICS,
        [
            r'\bdata analyst\b',
            r'\bdata analytics\b',
            r'\bbusiness data analyst\b',
            r'\bproduct data analyst\b',
            r'\bbi analyst\b',
            r'\bmarketing data analyst\b',
            r'\boperations data analyst\b',
        ],
        ['sql', 'excel', 'tableau', 'power bi', 'data visualization', 'metrics', 'insights', 'analytics', 'dashboards']
    ),
    (
        JobCategory.DATABASE,
        [
            r'\bsql developer\b',
            r'\bdatabase developer\b',
            r'\bdatabase engineer\b',
            r'\bdata warehouse\b',
            r'\bdwh engineer\b',
            r'\bdba\b',
            r'\bdatabase administrator\b',
        ],
        ['sql', 'pl/sql', 't-sql', 'postgresql', 'mysql', 'oracle', 'data warehouse', 'stored procedures', 'query optimization']
    ),
    (
        JobCategory.SOFTWARE_ENGINEERING,
        [
            r'\bsoftware engineer(ing)?\b',
            r'\bsoftware developer\b',
            r'\bsde\b',
            r'\bsde\s*[-–—]?\s*(i|ii|iii|1|2|3|lead|senior|principal)\b',
            r'\bfrontend\b',
            r'\bfront-end\b',
            r'\bbackend\b',
            r'\bback-end\b',
            r'\bfull\s*stack\b',
            r'\bweb developer\b',
            r'\bpython developer\b',
            r'\bjava developer\b',
            r'\bnode\.?js developer\b',
            r'\breact developer\b',
            r'\bangular developer\b',
            r'\bgolang developer\b',
            r'\bc\+\+ developer\b',
            r'\bandroid developer\b',
            r'\bios developer\b',
            r'\bmobile developer\b',
            r'\bqa engineer\b',
            r'\bsoftware development engineer\b',
            r'\btech lead\b',
            r'\bengineering manager\b',
            r'\bprogrammer\b',
        ],
        ['python', 'java', 'javascript', 'typescript', 'react', 'node', 'django', 'fastapi', 'spring', 'go', 'c++', 'c#', 'rest', 'api', 'microservices', 'git', 'full stack']
    ),
    (
        JobCategory.CLOUD_DEVOPS,
        [
            r'\bdevops\b',
            r'\bcloud engineer\b',
            r'\bcloud architect\b',
            r'\bsite reliability engineer\b',
            r'\bsre\b',
            r'\bplatform engineer\b',
            r'\binfrastructure engineer\b',
            r'\bsystems engineer\b',
            r'\bkubernetes engineer\b',
            r'\bcloud consultant\b',
        ],
        ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform', 'ci/cd', 'linux', 'ansible', 'helm', 'cloud', 'devops']
    ),
]


def classify_job(
    title: str,
    description: str = '',
    skills: Optional[List[str]] = None,
    responsibilities: str = ''
) -> Dict[str, Any]:
    """
    Classifies a job into one of the designated data categories or OTHER.

    Returns:
    {
        "category": JobCategory choice,
        "confidence": float (0.0 to 1.0),
        "matched_keywords": [ ... ],
        "is_accepted": True / False
    }
    """
    title_clean = (title or '').lower().strip()
    desc_clean = (description or '').lower()[:4000]
    resp_clean = (responsibilities or '').lower()[:2000]
    skills_clean = [s.lower().strip() for s in (skills or []) if s]
    combined_body = f"{desc_clean} {resp_clean} {' '.join(skills_clean)}"

    # 1. Primary Title Anti-Pattern Check
    # If the title is explicitly a non-tech role (e.g. Sales, HR, Driver), reject immediately
    for excluded_pat in EXCLUDED_PRIMARY_ROLES:
        if re.search(excluded_pat, title_clean):
            # Check if there is a tech qualifier e.g. "HR Tech Engineer", "Salesforce Developer"
            tech_override = ['engineer', 'developer', 'analyst', 'architect', 'scientist']
            if not any(to in title_clean for to in tech_override):
                return {
                    'category': JobCategory.OTHER,
                    'confidence': 0.95,
                    'matched_keywords': ['Excluded non-tech role detected'],
                    'is_accepted': False,
                }

    # 2. Check title against target role definitions (Highest Priority)
    for category, title_patterns, tech_keywords in ROLE_DEFINITIONS:
        for pat in title_patterns:
            if re.search(pat, title_clean):
                matched_kw = [kw for kw in tech_keywords if kw in combined_body or kw in title_clean]
                return {
                    'category': category,
                    'confidence': 0.95 if matched_kw else 0.85,
                    'matched_keywords': matched_kw[:6],
                    'is_accepted': True,
                }

    # 3. Check for secondary tech cues with supporting body/skills
    for category, title_patterns, tech_keywords in ROLE_DEFINITIONS:
        matched_body_kw = [kw for kw in tech_keywords if kw in combined_body]
        if len(matched_body_kw) >= 2 and any(t in title_clean for t in ['engineer', 'developer', 'tech', 'data', 'software', 'analyst']):
            return {
                'category': category,
                'confidence': 0.80,
                'matched_keywords': matched_body_kw[:6],
                'is_accepted': True,
            }

    # 4. General Engineering/Developer catch-all
    general_tech_terms = ['engineer', 'developer', 'programmer', 'architect', 'coder', 'sde']
    if any(gtt in title_clean for gtt in general_tech_terms):
        return {
            'category': JobCategory.SOFTWARE_ENGINEERING,
            'confidence': 0.75,
            'matched_keywords': ['general tech role'],
            'is_accepted': True,
        }

    # 5. Fallback to OTHER (Unrelated non-tech domain)
    return {
        'category': JobCategory.OTHER,
        'confidence': 0.90,
        'matched_keywords': [],
        'is_accepted': False,
    }


def parse_experience_requirements(title: str, text: str = '') -> Tuple[float, Optional[float]]:
    """
    Intelligently extracts required years of experience from job title and description.
    Supports formats like:
      - '3 - 5 years of experience' -> (3.0, 5.0)
      - '5+ years' -> (5.0, 8.0)
      - 'at least 2 years' -> (2.0, 5.0)
    Falls back to title seniority cues:
      - 'Principal / Architect / Director' -> (8.0, 15.0)
      - 'Lead / Staff' -> (7.0, 10.0)
      - 'Senior' -> (5.0, 8.0)
      - 'Mid / Intermediate' -> (3.0, 5.0)
      - 'Junior / Entry / Associate / Fresher' -> (0.0, 2.0)
      - 'Intern / Trainee' -> (0.0, 1.0)
    """
    combined = f"{title} {text}".lower()

    # Pattern 1: Range '3 - 5 years' or '3 to 5 years'
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*years?', combined)
    if range_match:
        try:
            min_y = float(range_match.group(1))
            max_y = float(range_match.group(2))
            if 0 <= min_y <= 25 and min_y <= max_y <= 30:
                return min_y, max_y
        except ValueError:
            pass

    # Pattern 2: 'X+ years' or 'at least X years' or 'X years of experience'
    single_match = re.search(r'(?:at least|minimum|min|with)\s*(\d+(?:\.\d+)?)\+?\s*years?', combined)
    if not single_match:
        single_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of\s*)?(?:relevant|hands-on|industry|commercial|professional)?\s*experience', combined)

    if single_match:
        try:
            val = float(single_match.group(1))
            if 0 <= val <= 25:
                return val, round(val + 3.0, 1)
        except ValueError:
            pass

    # Title seniority heuristics
    title_lower = title.lower()
    if any(w in title_lower for w in ['intern', 'internship', 'trainee', 'student', 'co-op']):
        return 0.0, 1.0
    if any(w in title_lower for w in ['junior', 'jr.', 'jr ', 'entry', 'associate', 'fresher', 'freshers', 'graduate', 'campus']):
        return 0.0, 2.0
    if any(w in title_lower for w in ['principal', 'director', 'vp', 'head of', 'architect']):
        return 8.0, 15.0
    if any(w in title_lower for w in ['lead', 'staff', 'manager']):
        return 7.0, 10.0
    if any(w in title_lower for w in ['senior', 'sr.', 'sr ']):
        return 5.0, 8.0
    if any(w in title_lower for w in ['mid', 'intermediate']):
        return 3.0, 5.0

    return 0.0, 2.0  # Default to Fresher / Entry Level friendly in this edition
