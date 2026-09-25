"""
Smart Job Extractor Service for JobAutoApply.

Extracts structured job attributes from:
1. Job Posting URLs (LinkedIn, Indeed, Internshala, Naukri, Greenhouse, Lever, etc.)
   using JSON-LD schemas, OpenGraph metadata, DOM container extractors, and
   headless Playwright for dynamic/client-rendered content (expanding "Show more").
2. Raw pasted Job Description text using NLP keyword, boundary, and section heuristics.
3. Automatically formats descriptions into clean paragraphs and crisp bullet points,
   separating Overview, Responsibilities, and Requirements.
4. Accurately determines Employment Type (Full-time, Contract, Internship, Trainee)
   and Work Mode (Remote, Hybrid, Onsite).
5. Runs real-time 4-tier deduplication against existing database jobs.
"""

import re
import html
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from jobs.models import Job
from jobs.services.job_classifier import parse_experience_requirements
from jobs.services.deduplication import JobDeduplicationService

COMMON_TECH_SKILLS = [
    'Python', 'SQL', 'Apache Spark', 'Spark', 'PySpark', 'Databricks', 'Airflow', 'Apache Kafka', 'Kafka',
    'Snowflake', 'dbt', 'AWS', 'Azure', 'GCP', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
    'Docker', 'Kubernetes', 'FastAPI', 'Django', 'Flask', 'Java', 'Scala', 'Golang',
    'Hadoop', 'Hive', 'Presto', 'Trino', 'ClickHouse', 'Machine Learning', 'Deep Learning',
    'PyTorch', 'TensorFlow', 'Scikit-Learn', 'Pandas', 'NumPy', 'Power BI', 'Tableau',
    'React', 'JavaScript', 'TypeScript', 'Node.js', 'System Design', 'ETL', 'Data Lake',
    'Data Governance', 'Data Quality', 'MLOps', 'LLM', 'NLP', 'Computer Vision'
]

INDIAN_CITIES = [
    'Bengaluru', 'Bangalore', 'Hyderabad', 'Pune', 'Gurugram', 'Gurgaon',
    'Noida', 'Mumbai', 'Chennai', 'Delhi', 'New Delhi', 'Kolkata', 'Ahmedabad', 'Kochi'
]

RESP_HEADERS = [
    r'(?:key\s+|core\s+|job\s+)?(?:responsibilities|duties|accountabilities)',
    r'roles?\s+(?:and|&)\s+responsibilities',
    r'what\s+you(?:\'ll|\s+will)\s+do(?:ing)?',
    r'day\s+in\s+the\s+life',
    r'your\s+(?:role|mission|impact)',
    r'what\s+you\s+will\s+be\s+working\s+on',
]

REQ_HEADERS = [
    r'(?:key\s+|basic\s+|minimum\s+|preferred\s+|mandatory\s+|required\s+)?(?:requirements|qualifications|skills|competencies|eligibility)(?:\s+(?:and|&)\s+(?:qualifications|requirements|skills|experience))?',
    r'what\s+we(?:\'re|\s+are)\s+looking\s+for',
    r'what\s+you\s+(?:bring|should\s+have|need)',
    r'who\s+you\s+are',
    r'ideal\s+candidate',
    r'education\s+(?:and|&)\s+experience',
    r'must[\s\-]have\s+skills',
]

OVERVIEW_HEADERS = [
    r'about\s+(?:us|the\s+company|the\s+role|the\s+team|the\s+client)',
    r'job\s+overview',
    r'position\s+summary',
    r'role\s+summary',
    r'company\s+overview',
    r'the\s+opportunity',
    r'who\s+we\s+are',
]

EEO_HEADERS = [
    r'equal\s+opportunity\s+employer',
    r'we\s+do\s+not\s+discriminate',
    r'diversity,\s*inclusion',
    r'diversity\s*(?:and|&)\s*belonging',
]

CONTAINER_PATTERNS = [
    r'<div[^>]*class=[\'"][^\'"]*show-more-less-html__markup[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<section[^>]*class=[\'"][^\'"]*show-more-less-html[^\'"]*[\'"][^>]*>(.*?)</section>',
    r'<div[^>]*class=[\'"][^\'"]*description__text[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*decorated-job-posting__details[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*jobs-description-content__text[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*jobs-box__html-content[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*id=[\'"]jobDescriptionText[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*jobsearch-jobDescriptionText[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*id=[\'"]content[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*job-description[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<div[^>]*class=[\'"][^\'"]*job__description[^\'"]*[\'"][^>]*>(.*?)</div>',
    r'<section[^>]*class=[\'"][^\'"]*job-description[^\'"]*[\'"][^>]*>(.*?)</section>',
    r'<div[^>]*id=[\'"]job-details[\'"][^>]*>(.*?)</div>',
    r'<article[^>]*>(.*?)</article>',
]


def is_teaser_description(text: str) -> bool:
    """Detects whether text is merely a social media teaser or truncated meta description."""
    if not text:
        return True
    t = text.strip()
    if 'See this and similar jobs on LinkedIn' in t or 'similar jobs on LinkedIn' in t:
        return True
    if len(t) < 250 and (t.startswith('Posted ') or t.endswith('…') or t.endswith('...')):
        return True
    return False


def clean_teaser_artifacts(text: str) -> str:
    """Removes platform teaser boilerplate from description text."""
    if not text:
        return ""
    cleaned = re.sub(r'Posted\s+\d+:\d+(?::\d+)?\s+[AP]M\.\s*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'(?:…|\.\.\.)?\s*See this and similar jobs on (?:LinkedIn|Indeed|Naukri).*$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def clean_html_to_markdown_or_text(text: str) -> str:
    """
    Converts raw HTML job descriptions into clean, formatted text preserving
    paragraphs, headings, and bullet points.
    """
    if not text:
        return ""

    # 1. Remove non-content tags completely
    cleaned = re.sub(
        r'<(script|style|svg|noscript|header|footer|nav|button|iframe)[^>]*>.*?</\1>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # 2. Convert line break tags
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)

    # 3. Convert headers
    cleaned = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n### \1\n\n', cleaned, flags=re.DOTALL | re.IGNORECASE)

    # 4. Convert list items to bullet points
    cleaned = re.sub(r'<li[^>]*>(.*?)</li>', r'\n• \1', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<li[^>]*>', '\n• ', cleaned, flags=re.IGNORECASE)

    # 5. Convert block elements to double newlines
    cleaned = re.sub(r'</?(?:p|div|section|article|blockquote)[^>]*>', '\n\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:ul|ol)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)

    # 6. Strip all remaining tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)

    # 7. Unescape HTML entities (&amp;, &nbsp;, &lt;, etc.)
    cleaned = html.unescape(cleaned)

    # 8. Normalize special characters & non-breaking spaces
    cleaned = cleaned.replace('\xa0', ' ').replace('\u200b', '').replace('\ufeff', '')

    # 9. Format lines: strip trailing/leading spaces, fix bullet points, avoid excess blanks
    lines = cleaned.split('\n')
    formatted_lines: List[str] = []
    prev_blank = False

    for raw_line in lines:
        line = re.sub(r'[ \t]+', ' ', raw_line).strip()
        if line == '###':
            continue
        if not line:
            if not prev_blank:
                # Avoid blank lines directly between two bullet points
                if not (formatted_lines and formatted_lines[-1].startswith('• ')):
                    formatted_lines.append('')
                    prev_blank = True
        else:
            if line.startswith(('* ', '- ', '+ ', '• ')):
                line = '• ' + line[2:].strip()
                if prev_blank and len(formatted_lines) >= 2 and formatted_lines[-2].startswith('• '):
                    formatted_lines.pop()
            formatted_lines.append(line)
            prev_blank = False

    res = '\n'.join(formatted_lines).strip()
    return clean_teaser_artifacts(res)


def format_plain_text(text: str) -> str:
    """
    Cleans up plain text pasted job descriptions, normalizing bullet points
    and paragraph breaks.
    """
    if not text:
        return ""
    if re.search(r'<(?:p|div|br|li|ul|h[1-6])[^>]*>', text, re.IGNORECASE):
        return clean_html_to_markdown_or_text(text)

    cleaned = html.unescape(text)
    cleaned = cleaned.replace('\xa0', ' ').replace('\u200b', '').replace('\ufeff', '')
    cleaned = clean_teaser_artifacts(cleaned)

    # Strip social hashtag spam blocks
    cleaned = re.sub(r'^\s*#[A-Za-z0-9_#\s]+$', '', cleaned, flags=re.MULTILINE)

    lines = cleaned.splitlines()
    formatted_lines: List[str] = []
    prev_blank = False

    for raw_line in lines:
        line = re.sub(r'[ \t]+', ' ', raw_line).strip()
        if not line:
            if not prev_blank:
                if not (formatted_lines and formatted_lines[-1].startswith('• ')):
                    formatted_lines.append('')
                    prev_blank = True
        else:
            if line.startswith(('* ', '- ', '+ ', '• ')):
                line = '• ' + line[2:].strip()
                if prev_blank and len(formatted_lines) >= 2 and formatted_lines[-2].startswith('• '):
                    formatted_lines.pop()
            formatted_lines.append(line)
            prev_blank = False

    return '\n'.join(formatted_lines).strip()


def bulletize_list_items(lines_list: List[str]) -> str:
    """Ensures each item in responsibilities/requirements is formatted with a clean bullet point."""
    out = []
    for l in lines_list:
        stripped = l.strip()
        if not stripped:
            continue
        # Preserve subheadings like **Required Skills** or Preferred Qualifications:
        if (stripped.startswith('**') and stripped.endswith('**')) or stripped.endswith(':'):
            out.append('\n' + stripped)
        elif stripped.startswith(('• ', '- ', '* ', '+ ')):
            out.append('• ' + stripped[2:].strip())
        else:
            out.append('• ' + stripped)
    return '\n'.join(out).strip()


def split_job_sections(text: str) -> Tuple[str, str, str]:
    """
    Splits text into (overview, responsibilities, requirements).
    """
    if not text:
        return "", "", ""

    # Strip hashtag spam blocks
    cleaned_text = re.sub(r'^\s*(?:#[A-Za-z0-9][A-Za-z0-9_]*\s*)+$', '', text, flags=re.MULTILINE)

    resp_pat = re.compile(
        r'^\s*(?:###?\s*|\*\*\s*|[-•*]\s*)?(?:' + '|'.join(RESP_HEADERS) + r')(?:\s*[:\-–*]*)?\s*$',
        re.I
    )
    req_pat = re.compile(
        r'^\s*(?:###?\s*|\*\*\s*|[-•*]\s*)?(?:' + '|'.join(REQ_HEADERS) + r')(?:\s*[:\-–*]*)?\s*$',
        re.I
    )
    overview_pat = re.compile(
        r'^\s*(?:###?\s*|\*\*\s*|[-•*]\s*)?(?:' + '|'.join(OVERVIEW_HEADERS) + r')(?:\s*[:\-–*]*)?\s*$',
        re.I
    )
    eeo_pat = re.compile(
        r'(?:' + '|'.join(EEO_HEADERS) + r')',
        re.I
    )

    lines = cleaned_text.split('\n')
    current_sec = 'overview'

    ov_lines, resp_lines, req_lines, eeo_lines = [], [], [], []

    for line in lines:
        stripped = line.strip()
        if resp_pat.match(stripped):
            current_sec = 'resp'
            continue
        elif req_pat.match(stripped):
            if current_sec == 'req':
                # Subheading inside requirements (e.g. Preferred Qualifications)
                req_lines.append(f"**{stripped.rstrip(':')}**")
            else:
                current_sec = 'req'
            continue
        elif overview_pat.match(stripped) and current_sec != 'overview':
            current_sec = 'overview'
            continue

        # If line is an EEO statement, divert to overview
        if eeo_pat.search(stripped) and len(stripped) > 50:
            eeo_lines.append(line)
            continue

        if current_sec == 'resp':
            resp_lines.append(line)
        elif current_sec == 'req':
            req_lines.append(line)
        else:
            ov_lines.append(line)

    overview = '\n'.join(ov_lines).strip()
    resp = bulletize_list_items(resp_lines)
    req = bulletize_list_items(req_lines)

    # Attach EEO statement to overview if present
    if eeo_lines:
        eeo_block = '\n'.join(eeo_lines).strip()
        overview = f"{overview}\n\n{eeo_block}".strip() if overview else eeo_block

    if not overview and (resp or req):
        overview = text.split('\n\n')[0].strip() if text else ""

    return overview, resp, req


def detect_employment_type(title: str, text: str, schema_emp: str = '') -> str:
    """
    Accurately classifies employment type:
    FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, TRAINEE, TEMPORARY.
    Ensures strict word boundaries so 'internal' does not trigger 'intern'.
    """
    t_clean = (title or '').lower()
    text_clean = (text or '').lower()

    # 1. Schema check
    if schema_emp:
        s_upper = str(schema_emp).upper()
        if 'INTERN' in s_upper:
            return Job.EmploymentType.INTERNSHIP
        if 'TRAINEE' in s_upper or 'APPRENTICE' in s_upper:
            return Job.EmploymentType.TRAINEE
        if 'CONTRACT' in s_upper or 'FREELANCE' in s_upper:
            return Job.EmploymentType.CONTRACT
        if 'PART' in s_upper:
            return Job.EmploymentType.PART_TIME
        if 'FULL' in s_upper:
            return Job.EmploymentType.FULL_TIME

    # 2. Title check (Highest accuracy priority)
    if re.search(r'\b(?:intern|internship|interns)\b', t_clean):
        return Job.EmploymentType.INTERNSHIP
    if re.search(r'\b(?:trainee|apprentice)\b', t_clean):
        return Job.EmploymentType.TRAINEE
    if re.search(r'\b(?:contract|contractor|contractual|freelance|c2c|consultant)\b', t_clean):
        return Job.EmploymentType.CONTRACT
    if re.search(r'\b(?:part[\s\-]time)\b', t_clean):
        return Job.EmploymentType.PART_TIME
    if re.search(r'\b(?:full[\s\-]time|permanent)\b', t_clean):
        return Job.EmploymentType.FULL_TIME

    # 3. Explicit labels in JD text (e.g. "Employment Type: Contract")
    m_label = re.search(
        r'(?:employment\s*type|job\s*type|type\s*of\s*employment)\s*[:\-]\s*([^\n\r,]+)',
        text,
        re.I
    )
    if m_label:
        label_val = m_label.group(1).lower()
        if re.search(r'\b(?:intern|internship)\b', label_val):
            return Job.EmploymentType.INTERNSHIP
        if re.search(r'\b(?:trainee|apprentice)\b', label_val):
            return Job.EmploymentType.TRAINEE
        if re.search(r'\b(?:contract|freelance|c2c)\b', label_val):
            return Job.EmploymentType.CONTRACT
        if re.search(r'\bpart[\s\-]time\b', label_val):
            return Job.EmploymentType.PART_TIME
        if re.search(r'\b(?:full[\s\-]time|permanent)\b', label_val):
            return Job.EmploymentType.FULL_TIME

    # 4. Contextual search (with word boundaries to avoid 'internal')
    if re.search(r'\b(?:internship\s+duration|summer\s+intern|internship\s+opportunity|stipend\s*(?:of|:)?\s*(?:₹|rs|\$)?\s*\d+)\b', text_clean):
        return Job.EmploymentType.INTERNSHIP
    if re.search(r'\b(?:graduate\s+trainee|management\s+trainee|trainee\s+engineer)\b', text_clean):
        return Job.EmploymentType.TRAINEE
    if re.search(r'\b(?:c2c|corp[\s\-]to[\s\-]corp|freelance\s+contract|\bcontractor\b|fixed[\s\-]term\s+contract)\b', text_clean):
        return Job.EmploymentType.CONTRACT
    if re.search(r'\b(?:part[\s\-]time\s+role|part[\s\-]time\s+position)\b', text_clean):
        return Job.EmploymentType.PART_TIME

    return Job.EmploymentType.FULL_TIME


def detect_work_mode(title: str, text: str, location: str = '') -> str:
    """
    Accurately detects REMOTE, HYBRID, or ONSITE.
    """
    t_clean = (title or '').lower()
    text_clean = (text or '').lower()
    loc_clean = (location or '').lower()

    # 1. Title check
    if re.search(r'\b(?:remote|wfh|work\s+from\s+home)\b', t_clean):
        return Job.WorkMode.REMOTE
    if re.search(r'\b(?:hybrid)\b', t_clean):
        return Job.WorkMode.HYBRID
    if re.search(r'\b(?:onsite|on\-site|in\-office)\b', t_clean):
        return Job.WorkMode.ONSITE

    # 2. Location check
    if 'hybrid' in loc_clean:
        return Job.WorkMode.HYBRID
    if 'remote' in loc_clean or 'wfh' in loc_clean:
        return Job.WorkMode.REMOTE

    # 3. Explicit labels in JD text
    m_label = re.search(
        r'(?:work\s*mode|workplace\s*type|location\s*type|work\s*location)\s*[:\-]\s*([^\n\r,]+)',
        text,
        re.I
    )
    if m_label:
        label_val = m_label.group(1).lower()
        if 'hybrid' in label_val:
            return Job.WorkMode.HYBRID
        if 'remote' in label_val or 'wfh' in label_val or 'home' in label_val:
            return Job.WorkMode.REMOTE
        if 'onsite' in label_val or 'on-site' in label_val or 'office' in label_val:
            return Job.WorkMode.ONSITE

    # 4. Contextual body search (check HYBRID first since hybrid positions mention office/remote)
    if re.search(r'\b(?:hybrid|days\s+(?:in|from)\s+(?:the\s+)?office)\b', text_clean):
        return Job.WorkMode.HYBRID
    if re.search(r'\b(?:100%\s+remote|fully\s+remote|remote\s+first|work\s+from\s+anywhere|remote\s+position|remote\s+opportunity)\b', text_clean):
        return Job.WorkMode.REMOTE
    if re.search(r'\b(?:on[\s\-]site|in[\s\-]office|relocate\s+to|must\s+work\s+from\s+(?:our|the)\s+office)\b', text_clean):
        return Job.WorkMode.ONSITE

    # If location contains both Remote and local cities (e.g. Remote, India or local to Noida, Bangalore)
    if 'remote' in text_clean and any(city.lower() in text_clean for city in INDIAN_CITIES):
        return Job.WorkMode.HYBRID

    # If location is an Indian city, default to ONSITE
    if any(city.lower() in loc_clean for city in INDIAN_CITIES):
        return Job.WorkMode.ONSITE

    return Job.WorkMode.REMOTE if 'remote' in text_clean else Job.WorkMode.ONSITE


def check_job_duplicate(
    company_name: str,
    title: str,
    location: str = '',
    external_url: str = '',
    source_job_id: str = '',
    source: str = '',
    description: str = ''
) -> Dict[str, Any]:
    """
    Executes 4-tier deduplication check against the database and returns
    structured match details.
    """
    dup = JobDeduplicationService.find_duplicate(
        company_name=company_name,
        title=title,
        location=location,
        external_url=external_url,
        source_job_id=source_job_id,
        source=source,
        description=description
    )

    if dup:
        src_label = dup.get_source_display() if hasattr(dup, 'get_source_display') else str(dup.source)
        return {
            'is_duplicate': True,
            'job_id': dup.id,
            'title': dup.title,
            'company_name': dup.company_name,
            'location': dup.location,
            'work_mode': dup.work_mode,
            'employment_type': dup.employment_type,
            'detail_url': f"/jobs/{dup.id}/",
            'source': src_label,
            'match_reason': f"Matching job already exists: Job #{dup.id} at {dup.company_name} ({src_label})"
        }

    return {
        'is_duplicate': False,
        'job_id': None,
        'title': None,
        'company_name': None,
        'location': None,
        'work_mode': None,
        'employment_type': None,
        'detail_url': None,
        'source': None,
        'match_reason': None
    }


def extract_skills_from_text(text: str) -> List[str]:
    """Detects industry tech skills from text."""
    found = []
    text_lower = text.lower()
    for skill in COMMON_TECH_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return list(dict.fromkeys(found))[:12]


def detect_source_from_url(url: str) -> str:
    """Infers Source choice from external URL."""
    u = (url or '').lower()
    if 'linkedin.com' in u:
        return Job.Source.LINKEDIN
    if 'naukri.com' in u:
        return Job.Source.NAUKRI
    if 'indeed.com' in u:
        return Job.Source.INDEED
    if 'internshala.com' in u:
        return Job.Source.INTERNSHALA
    if 'wellfound.com' in u or 'angel.co' in u:
        return Job.Source.WELLFOUND
    if 'cutshort.io' in u:
        return Job.Source.CUTSHORT
    if 'instahyre.com' in u:
        return Job.Source.INSTAHYRE
    if 'remotive.com' in u:
        return Job.Source.REMOTIVE
    if 'arbeitnow.com' in u:
        return Job.Source.ARBEITNOW
    return Job.Source.OTHER


def extract_job_from_html(html_text: str, source_url: str = '') -> Dict[str, Any]:
    """Extracts job attributes from raw HTML via JSON-LD, DOM containers, and meta tags."""
    data: Dict[str, Any] = {}
    schema_emp_type = ''
    raw_desc = ''

    # 1. Inspect JSON-LD for Schema.org JobPosting
    json_ld_blocks = re.findall(
        r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>',
        html_text,
        re.DOTALL | re.IGNORECASE
    )

    for block in json_ld_blocks:
        try:
            parsed = json.loads(block.strip())
            items = []
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                if '@graph' in parsed and isinstance(parsed['@graph'], list):
                    items = parsed['@graph']
                else:
                    items = [parsed]

            for item in items:
                if not isinstance(item, dict):
                    continue
                itype = str(item.get('@type', ''))
                if 'JobPosting' in itype:
                    data['title'] = item.get('title')

                    # Company
                    hiring_org = item.get('hiringOrganization')
                    if isinstance(hiring_org, dict):
                        data['company_name'] = hiring_org.get('name')
                    elif isinstance(hiring_org, str):
                        data['company_name'] = hiring_org

                    # Location
                    loc_val = item.get('jobLocation')
                    if isinstance(loc_val, dict):
                        addr = loc_val.get('address')
                        if isinstance(addr, dict):
                            loc_parts = [
                                addr.get('addressLocality'),
                                addr.get('addressRegion'),
                                addr.get('addressCountry')
                            ]
                            data['location'] = ", ".join([p for p in loc_parts if p])
                    elif isinstance(loc_val, list) and loc_val:
                        data['location'] = str(loc_val[0])

                    # Description
                    d = item.get('description', '')
                    if d and not is_teaser_description(d):
                        raw_desc = d

                    # Salary
                    base_sal = item.get('baseSalary')
                    if isinstance(base_sal, dict):
                        val = base_sal.get('value')
                        if isinstance(val, dict):
                            min_s = val.get('minValue')
                            max_s = val.get('maxValue')
                            unit = val.get('unitText', 'YEAR')
                            curr = base_sal.get('currency', 'INR')
                            if min_s and max_s:
                                data['salary_text'] = f"{curr} {min_s:,.0f} - {max_s:,.0f} /{unit.lower()}"
                            elif min_s:
                                data['salary_text'] = f"{curr} {min_s:,.0f} /{unit.lower()}"

                    # Employment Type schema hint
                    schema_emp_type = item.get('employmentType', '')
                    break
            if data.get('title'):
                break
        except Exception:
            continue

    # 2. Inspect DOM container selectors for full rich description
    container_desc = ''
    for pat in CONTAINER_PATTERNS:
        m_c = re.search(pat, html_text, re.DOTALL | re.IGNORECASE)
        if m_c:
            cand = m_c.group(1).strip()
            if len(cand) > len(container_desc) and not is_teaser_description(cand):
                container_desc = cand

    if container_desc and len(container_desc) > len(raw_desc):
        raw_desc = container_desc

    # 3. OpenGraph / Title Fallback
    og_title = (
        re.search(r'<meta[^>]*property=[\'"]og:title[\'"][^>]*content=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE) or
        re.search(r'<meta[^>]*name=[\'"]twitter:title[\'"][^>]*content=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE)
    )
    if og_title:
        raw_t = html.unescape(og_title.group(1).strip())
        # Check standard LinkedIn format: "<Company> hiring <Title> in <Location> | LinkedIn"
        m_li = re.match(r'^(.*?)\s+(?:hiring|is\s+hiring)\s+(.*?)\s+in\s+(.*?)(?:\s+[|\-–•].*)?$', raw_t, re.IGNORECASE)
        if m_li:
            if not data.get('company_name'):
                data['company_name'] = m_li.group(1).strip()
            if not data.get('title'):
                data['title'] = m_li.group(2).strip()
            if not data.get('location'):
                data['location'] = m_li.group(3).strip()
        elif not data.get('title'):
            parts = re.split(r'\s+[-|–—•]\s+', raw_t)
            data['title'] = parts[0].strip()
            if len(parts) > 1 and not data.get('company_name'):
                data['company_name'] = parts[1].replace('at ', '').strip()

    if not data.get('title'):
        t_tag = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.DOTALL | re.IGNORECASE)
        if t_tag:
            clean_t = html.unescape(t_tag.group(1).strip())
            m_li = re.match(r'^(.*?)\s+(?:hiring|is\s+hiring)\s+(.*?)\s+in\s+(.*?)(?:\s+[|\-–•].*)?$', clean_t, re.IGNORECASE)
            if m_li:
                if not data.get('company_name'):
                    data['company_name'] = m_li.group(1).strip()
                data['title'] = m_li.group(2).strip()
                if not data.get('location'):
                    data['location'] = m_li.group(3).strip()
            else:
                parts = re.split(r'\s+[-|–—•]\s+', clean_t)
                data['title'] = parts[0].strip()

    if not data.get('company_name'):
        og_site = re.search(r'<meta[^>]*property=[\'"]og:site_name[\'"][^>]*content=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE)
        if og_site:
            cand = html.unescape(og_site.group(1).strip())
            if cand.lower() not in ['linkedin', 'indeed', 'naukri', 'glassdoor']:
                data['company_name'] = cand

    # 4. Fallback to OpenGraph description ONLY if no container description exists
    if not raw_desc:
        og_desc = (
            re.search(r'<meta[^>]*property=[\'"]og:description[\'"][^>]*content=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE) or
            re.search(r'<meta[^>]*name=[\'"]description[\'"][^>]*content=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE)
        )
        if og_desc:
            raw_desc = clean_teaser_artifacts(og_desc.group(1).strip())

    # Clean description into well-formatted markdown / text
    cleaned_desc = clean_html_to_markdown_or_text(raw_desc) if raw_desc else ""

    # Split into Overview, Responsibilities, and Requirements
    overview, resp, req = split_job_sections(cleaned_desc)
    data['description'] = overview or cleaned_desc
    data['responsibilities'] = resp
    data['requirements'] = req

    # Location detection from body if missing
    combined_body = f"{data.get('title', '')} {cleaned_desc}"
    if not data.get('location'):
        for city in INDIAN_CITIES:
            if re.search(r'\b' + city + r'\b', combined_body, re.IGNORECASE):
                data['location'] = f"{city}, India"
                break
        if not data.get('location'):
            if re.search(r'\bremote\b|\bwfh\b|\bwork from home\b', combined_body, re.IGNORECASE):
                data['location'] = "Remote"
            else:
                data['location'] = "India"

    # Work Mode
    data['work_mode'] = detect_work_mode(data.get('title', ''), combined_body, data.get('location', ''))

    # Employment Type
    data['employment_type'] = detect_employment_type(data.get('title', ''), combined_body, schema_emp_type)

    # Experience
    exp_min, exp_max = parse_experience_requirements(data.get('title', ''), cleaned_desc)
    data['experience_min'] = exp_min
    data['experience_max'] = exp_max

    # Skills
    detected_skills = extract_skills_from_text(combined_body)
    data['skills'] = ", ".join(detected_skills)

    data['external_url'] = source_url
    data['source'] = detect_source_from_url(source_url)

    # Run Deduplication Check
    dup_info = check_job_duplicate(
        company_name=data.get('company_name', ''),
        title=data.get('title', ''),
        location=data.get('location', ''),
        external_url=data.get('external_url', ''),
        source_job_id='',
        source=data.get('source', ''),
        description=cleaned_desc
    )
    data['duplicate'] = dup_info
    data['is_duplicate'] = dup_info['is_duplicate']

    return data


def extract_job_from_url(url: str) -> Dict[str, Any]:
    """
    Fetches a URL and parses its job posting details.
    Uses fast HTTP request first, with headless Playwright fallback to render dynamic DOM,
    expand 'Show more' sections, and overcome anti-scraping / teasers.
    """
    clean_url = (url or '').strip()
    if not clean_url:
        return {'success': False, 'error': 'No URL provided'}

    if not clean_url.startswith('http://') and not clean_url.startswith('https://'):
        clean_url = 'https://' + clean_url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-IN,en;q=0.9',
    }

    html_content = ""
    fetch_failed = False
    try:
        req = urllib.request.Request(clean_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html_content = resp.read().decode('utf-8', errors='ignore')
    except Exception:
        fetch_failed = True

    parsed = {}
    if html_content and not fetch_failed:
        parsed = extract_job_from_html(html_content, source_url=clean_url)

    # If HTTP request failed OR description is empty/teaser, launch Playwright
    needs_playwright = (
        fetch_failed or
        not parsed.get('title') or
        not parsed.get('description') or
        is_teaser_description(parsed.get('description', ''))
    )

    if needs_playwright:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 800}
                )
                page = context.new_page()
                page.goto(clean_url, timeout=20000, wait_until='domcontentloaded')

                # Click "Show more" button if job description is clamped
                try:
                    page.locator('.show-more-less-html__button-more, button[aria-label*="Show more"], .show-more').first.click(timeout=2500)
                except Exception:
                    pass

                pw_html = page.content()
                browser.close()

                pw_parsed = extract_job_from_html(pw_html, source_url=clean_url)
                if pw_parsed.get('description') and not is_teaser_description(pw_parsed.get('description', '')):
                    parsed = pw_parsed
                elif pw_parsed.get('title') and not parsed.get('title'):
                    parsed = pw_parsed
        except Exception as pw_exc:
            if not parsed.get('title'):
                return {'success': False, 'error': f"Failed to retrieve job details from URL: {str(pw_exc)}"}

    if not parsed.get('title'):
        # Infer title from URL path slug as last resort
        slug = urllib.parse.urlparse(clean_url).path.strip('/').split('/')[-1]
        clean_slug = re.sub(r'[^a-zA-Z0-9]+', ' ', slug).title()
        if len(clean_slug) > 3:
            parsed['title'] = clean_slug

    return {'success': True, 'data': parsed}


def extract_job_from_text(raw_text: str) -> Dict[str, Any]:
    """Parses raw text / pasted job description into structured job attributes."""
    raw_cleaned = (raw_text or '').strip()
    if not raw_cleaned:
        return {'success': False, 'error': 'No text provided'}

    # Convert to clean formatted markdown / text
    formatted_text = format_plain_text(raw_cleaned)
    lines = [line.strip() for line in formatted_text.splitlines() if line.strip()]
    if not lines:
        return {'success': False, 'error': 'Pasted text is empty'}

    data: Dict[str, Any] = {}

    # 1. Title detection
    title = ""
    for line in lines[:10]:
        m = re.match(r'^(?:Job\s*Title|Title|Role|Position|Opening)\s*[:\-]\s*(.*)$', line, re.IGNORECASE)
        if m:
            raw_t = m.group(1).strip()
            # Strip metadata packed onto the position line
            cleaned_t = re.split(r'\s+(?:no[.#\s]|number\s+of|positions?|remote|hybrid|location|req\b|job\s*id\b|at\b|[|\-])', raw_t, flags=re.I)[0].strip()
            cleaned_t = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', cleaned_t).strip()
            if len(cleaned_t) > 2:
                title = cleaned_t
                break

    if not title:
        # Check first line
        first_line = lines[0]
        if len(first_line) < 85 and not first_line.lower().startswith(('about', 'we are', 'join', 'company', 'http', 'www')):
            title = first_line
        else:
            for role_kw in [
                'AI Data Engineer', 'Data Platform Engineer', 'Cloud Data Engineer',
                'Data Architect', 'MLOps Engineer', 'Data Security Engineer',
                'Data Governance Engineer', 'Data Quality Engineer', 'AI/ML Engineer',
                'Data Scientist', 'Analytics Engineer', 'Decision Scientist',
                'AI Data & Knowledge Engineer', 'Data Annotation Specialist',
                'Data Analyst', 'Data Engineer', 'Software Engineer', 'Python Developer'
            ]:
                if re.search(r'\b' + re.escape(role_kw) + r'\b', formatted_text[:400], re.IGNORECASE):
                    title = role_kw
                    break
    data['title'] = title or "Software / Data Professional"

    # 2. Company Name
    company = ""
    # Explicit line Company: ...
    m_comp = re.search(r'^\s*(?:Company(?:\s*Name)?|Employer|Organization|Hiring Company)\s*[:\-]\s*(.*)$', formatted_text, re.MULTILINE | re.I)
    if m_comp:
        c = m_comp.group(1).strip()
        if c and len(c) < 50:
            company = c

    # About Company Droisys or About Company: Droisys or About CompanyDroisys
    if not company:
        m_comp = re.search(r'About\s+Company\s*[:\-]?\s*([A-Z][A-Za-z0-9&\s]{1,30}?)(?:\s+is|\s+was|\.|\n)', formatted_text, re.I)
        if m_comp:
            c = m_comp.group(1).strip()
            if c and c.lower() not in ['this', 'our', 'the']:
                company = c

    # At Droisys, we invest ...
    if not company:
        m_comp = re.search(r'\bAt\s+([A-Z][A-Za-z0-9&]{1,30}),?\s+we\s+(?:invest|are|believe|pride|deliver|build|work|offer)', formatted_text)
        if m_comp:
            company = m_comp.group(1).strip()

    # We at Droisys ...
    if not company:
        m_comp = re.search(r'\bWe\s+at\s+([A-Z][A-Za-z0-9&]{1,30})\b', formatted_text, re.I)
        if m_comp:
            company = m_comp.group(1).strip()

    # Droisys is an innovation ...
    if not company:
        m_comp = re.search(r'\b([A-Z][A-Za-z0-9&]{1,30})\s+is\s+an?\s+(?:equal\s+opportunity|innovation|leading|global|fast[\s\-]growing|technology)', formatted_text)
        if m_comp:
            c = m_comp.group(1).strip()
            if c.lower() not in ['this', 'it', 'there', 'that']:
                company = c

    # Fallback 'at <Company>'
    if not company:
        m_comp = re.search(r'\bat\s+([A-Z][A-Za-z0-9\s&]{2,30}?)(?:\s+in|\s+is|\s+looking|\.|\,|$|\n)', formatted_text[:400])
        if m_comp:
            cand = m_comp.group(1).strip()
            if not any(w in cand.lower() for w in ['least', 'home', 'work', 'present', 'the', 'our', 'a', 'an']):
                company = cand

    data['company_name'] = company or "Company"

    # 3. Location
    loc = ""
    for line in lines[:15]:
        m = re.match(r'^(?:Location|City|Place|Workplace|Job\s*Location)\s*[:\-]\s*(.*)$', line, re.IGNORECASE)
        if m:
            loc = m.group(1).strip()
            break
    if not loc:
        # Check if Position line or JD had location like "10Remote , India or local to Noida, Bangalore"
        found_cities = []
        for city in INDIAN_CITIES:
            if re.search(r'\b' + city + r'\b', formatted_text, re.IGNORECASE):
                found_cities.append(city)
        if found_cities:
            loc = ", ".join(found_cities) + ", India"
        elif 'remote' in formatted_text.lower():
            loc = "Remote"
        else:
            loc = "India"
    data['location'] = loc

    # 4. Work Mode
    data['work_mode'] = detect_work_mode(data['title'], formatted_text, data['location'])

    # 5. Employment Type
    data['employment_type'] = detect_employment_type(data['title'], formatted_text)

    # 6. Experience
    exp_min, exp_max = parse_experience_requirements(data['title'], formatted_text)
    data['experience_min'] = exp_min
    data['experience_max'] = exp_max

    # 7. Skills
    detected_skills = extract_skills_from_text(formatted_text)
    data['skills'] = ", ".join(detected_skills)

    # 8. Salary
    sal_m = (
        re.search(r'(?:₹|Rs\.?|INR|\$)\s*[\d\.\,]+\s*(?:-|to)?\s*[\d\.\,]*\s*(?:LPA|L|Lac|Lakhs?|Cr|k|year|yr|month|pm)?', formatted_text, re.IGNORECASE) or
        re.search(r'\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?\s*LPA', formatted_text, re.IGNORECASE)
    )
    data['salary_text'] = sal_m.group(0).strip() if sal_m else ""

    # 9. Split into Overview, Responsibilities, and Requirements
    overview, resp, req = split_job_sections(formatted_text)
    data['description'] = overview or formatted_text
    data['responsibilities'] = resp
    data['requirements'] = req

    data['source'] = Job.Source.MANUAL
    data['external_url'] = ""

    # 10. Deduplication Check
    dup_info = check_job_duplicate(
        company_name=data['company_name'],
        title=data['title'],
        location=data['location'],
        external_url='',
        source_job_id='',
        source=data['source'],
        description=formatted_text
    )
    data['duplicate'] = dup_info
    data['is_duplicate'] = dup_info['is_duplicate']

    return {'success': True, 'data': data}
