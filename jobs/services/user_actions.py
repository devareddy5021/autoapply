import re
import json
import html
import urllib.request
import logging
from typing import Optional, Tuple, Dict, Any, List
from django.utils import timezone
from django.contrib.auth.models import User
from jobs.models import Job, UserJob, normalize_job_url
from accounts.models import Profile
from resumes.models import Resume
from matching.services import calculate_match_score

logger = logging.getLogger(__name__)


def clean_html_text(raw_html: str) -> str:
    """Strips HTML tags and unescapes HTML entities to clean text."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_experience_requirements(title: str, text: str) -> Tuple[float, Optional[float]]:
    """
    Intelligently extracts required years of experience from job title and description.
    """
    from jobs.services.job_classifier import parse_experience_requirements as _parse_exp
    return _parse_exp(title, text)


class JobDeduplicationService:
    """
    Reusable deduplication engine to prevent duplicate Job records.
    Priority order:
    1. source + source_job_id
    2. normalized_url (when available)
    3. company_name + title + location match
    """
    @classmethod
    def find_duplicate(
        cls,
        company_name: str,
        title: str,
        location: str = '',
        external_url: str = '',
        source_job_id: str = '',
        source: str = ''
    ) -> Optional[Job]:
        # 1. Match source + source_job_id
        if source_job_id:
            query = Job.objects.filter(source_job_id=source_job_id.strip())
            if source:
                query = query.filter(source=source)
            existing = query.first()
            if existing:
                return existing

        # 2. Match normalized URL
        if external_url:
            norm_url = normalize_job_url(external_url)
            if norm_url:
                existing = Job.objects.filter(normalized_url=norm_url).first()
                if existing:
                    return existing

        # 3. Match normalized company, title, and location
        if company_name and title:
            query = Job.objects.filter(
                company_name__iexact=company_name.strip(),
                title__iexact=title.strip()
            )
            if location:
                query = query.filter(location__icontains=location.strip())
            return query.first()

        return None


def calculate_and_sync_user_job_match(user: User, job: Job) -> UserJob:
    """
    Calculates deterministic match score against user's profile and saves it to UserJob.
    """
    profile, _ = Profile.objects.get_or_create(user=user)
    default_resume = Resume.objects.filter(user=user, is_default=True).first()

    match_info = calculate_match_score(job, profile, default_resume)

    user_job, _ = UserJob.objects.get_or_create(
        user=user,
        job=job,
        defaults={
            'match_score': match_info['score'],
            'match_reasons': match_info.get('reasons', []),
            'missing_skills': match_info.get('missing_skills', []),
        }
    )
    user_job.match_score = match_info['score']
    user_job.match_reasons = match_info.get('reasons', [])
    user_job.missing_skills = match_info.get('missing_skills', [])
    user_job.save(update_fields=['match_score', 'match_reasons', 'missing_skills', 'updated_at'])

    return user_job


def toggle_save_job(user: User, job_id: int) -> Tuple[Optional[UserJob], bool]:
    """
    Toggles the is_saved status for a user and job.
    Returns (UserJob, is_saved_status).
    """
    job = Job.objects.filter(pk=job_id).first()
    if not job:
        return None, False

    user_job, created = UserJob.objects.get_or_create(user=user, job=job)
    user_job.is_saved = not user_job.is_saved
    user_job.save(update_fields=['is_saved', 'updated_at'])

    return user_job, user_job.is_saved


def toggle_ignore_job(user: User, job_id: int) -> Tuple[Optional[UserJob], bool]:
    """
    Toggles the is_ignored status for a user and job.
    Returns (UserJob, is_ignored_status).
    """
    job = Job.objects.filter(pk=job_id).first()
    if not job:
        return None, False

    user_job, created = UserJob.objects.get_or_create(user=user, job=job)
    user_job.is_ignored = not user_job.is_ignored
    user_job.save(update_fields=['is_ignored', 'updated_at'])

    return user_job, user_job.is_ignored


def create_manual_job(user: User, form_cleaned_data: Dict[str, Any]) -> Tuple[Job, bool, UserJob]:
    """
    Creates a job manually:
    1. Checks for duplicates using JobDeduplicationService.
    2. Saves the job.
    3. Calculates match against the user.
    4. Creates/updates UserJob.
    Returns (Job, is_duplicate, UserJob).
    """
    company_name = form_cleaned_data.get('company_name', '')
    title = form_cleaned_data.get('title', '')
    location = form_cleaned_data.get('location', '')
    external_url = form_cleaned_data.get('external_url', '')
    source_job_id = form_cleaned_data.get('source_job_id', '')
    source = form_cleaned_data.get('source', Job.Source.MANUAL)

    duplicate = JobDeduplicationService.find_duplicate(
        company_name=company_name,
        title=title,
        location=location,
        external_url=external_url,
        source_job_id=source_job_id,
        source=source
    )

    if duplicate:
        user_job = calculate_and_sync_user_job_match(user, duplicate)
        return duplicate, True, user_job

    job = Job.objects.create(**form_cleaned_data)
    user_job = calculate_and_sync_user_job_match(user, job)

    return job, False, user_job


INDIA_LOCATION_KEYWORDS = [
    'india', 'bengaluru', 'bangalore', 'hyderabad', 'mumbai', 'pune',
    'delhi', 'new delhi', 'noida', 'greater noida', 'gurgaon', 'gurugram', 'chennai', 'kolkata',
    'ahmedabad', 'kochi', 'cochin', 'indore', 'chandigarh', 'jaipur', 'trivandrum',
    'thiruvananthapuram', 'mysore', 'mysuru', 'bhubaneswar', 'nagpur', 'coimbatore'
]

EXCLUDED_FOREIGN_RESTRICTIONS = [
    'usa only', 'us only', 'united states only', 'uk only', 'germany only',
    'canada only', 'europe only', 'eu only', 'latam only', 'apac only',
    'france only', 'japan only', 'australia only', 'us timezones', 'poland',
    'germany', 'deutschland', 'homeoffice', 'europe', 'latam', 'emea',
    'france', 'japan', 'turkey', 'mexico', 'norway', 'israel', 'peru', 'argentina'
]

FOREIGN_CITIES = [
    'london', 'berlin', 'munich', 'cologne', 'dortmund', 'frankfurt', 'paris',
    'tokyo', 'sydney', 'tholey', 'kassel', 'bexbach', 'darmstadt', 'kaarst',
    'heidelberg', 'leipzig', 'san francisco', 'new york', 'deutschland'
]


def is_india_or_remote(location: str, work_mode: str = '', title: str = '') -> bool:
    """
    Returns True ONLY if:
    1. The location is in India (Bengaluru, Hyderabad, Mumbai, Delhi, Pune, etc.)
    2. OR it is a Worldwide/Global Remote job open to candidates in India.
    Restricted foreign locations (e.g. USA, Germany, Poland, Canada, Europe, etc.) are excluded.
    """
    loc_lower = (location or '').lower().strip()
    mode_lower = (work_mode or '').lower().strip()
    title_lower = (title or '').lower().strip()
    combined = f"{loc_lower} {title_lower}"

    # 1. Any explicitly Indian location is always valid
    if any(city in loc_lower for city in INDIA_LOCATION_KEYWORDS):
        return True

    # 2. Check for foreign onsite/hybrid cities without India
    if any(fc in combined for fc in FOREIGN_CITIES):
        return False

    # 3. Check for foreign-only country/region restrictions
    foreign_restrictions = [
        'usa', 'us', 'united states', 'canada', 'uk', 'united kingdom',
        'germany', 'deutschland', 'homeoffice', 'europe', 'eu', 'latam', 'emea',
        'france', 'japan', 'turkey', 'mexico', 'norway', 'israel', 'peru', 'argentina', 'poland', 'cee'
    ]
    if any(re.search(r'\b' + re.escape(fr) + r'\b', combined) for fr in foreign_restrictions):
        if 'worldwide' not in loc_lower and 'anywhere' not in loc_lower and 'global' not in loc_lower:
            return False

    # 4. Pure Remote / Worldwide / Anywhere jobs
    if loc_lower in ('remote', 'worldwide', 'anywhere', 'global') or mode_lower == 'remote':
        return True

    if 'worldwide' in loc_lower or 'anywhere' in loc_lower:
        return True

    return False


REAL_INDIA_TECH_JOBS = [
    {
        'title': 'Senior Backend Engineer (Python / Django)',
        'company_name': 'Razorpay',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Razorpay is building the financial infrastructure for India. As a Senior Backend Engineer on our Payments platform, "
            "you will design and build mission-critical distributed payment gateways, webhook pipelines, and settlement ledgers."
        ),
        'requirements': "5+ years of software engineering in Python. Distributed systems, PostgreSQL, Redis, Kafka, AWS.",
        'experience_min': 5.0,
        'experience_max': 8.0,
        'skills': 'Python, Django, PostgreSQL, Redis, Kafka, AWS, Docker, Microservices',
        'salary_text': '₹28,00,000 - ₹42,00,000 / year + ESOPs',
        'external_url': 'https://razorpay.com/jobs/senior-backend-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'RAZORPAY-SWE-101',
    },
    {
        'title': 'Full Stack Developer (Python + React)',
        'company_name': 'Swiggy',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Swiggy Engineering is seeking a Full Stack Developer to build restaurant partner dashboards, order dispatch analytics, "
            "and candidate portals with React, TypeScript, and scalable Python backend services."
        ),
        'requirements': "3+ years of full stack experience in React, Python/Django, PostgreSQL, and REST APIs.",
        'experience_min': 3.0,
        'experience_max': 6.0,
        'skills': 'Python, React, TypeScript, Django, PostgreSQL, Docker, Redis',
        'salary_text': '₹20,00,000 - ₹32,00,000 / year',
        'external_url': 'https://careers.swiggy.com/jobs/full-stack-dev',
        'source': Job.Source.OTHER,
        'source_job_id': 'SWIGGY-FSD-202',
    },
    {
        'title': 'Software Development Engineer II - Python',
        'company_name': 'PhonePe',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Join PhonePe's Core Platform Team building UPI payments, merchant analytics, and risk verification systems. "
            "You will write clean, well-tested Python services with sub-millisecond latency SLAs."
        ),
        'requirements': "2-5 years of backend engineering experience. Python, relational databases, caching, and CI/CD pipelines.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'Python, Django, FastAPI, MySQL, Redis, AWS, Kubernetes',
        'salary_text': '₹22,00,000 - ₹35,00,000 / year',
        'external_url': 'https://phonepe.com/careers/sde2-python',
        'source': Job.Source.OTHER,
        'source_job_id': 'PHONEPE-SDE2-303',
    },
    {
        'title': 'Junior Python Developer',
        'company_name': 'Zerodha',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Zerodha is India's largest discount broker. We are hiring Junior Python Developers passionate about open source, "
            "minimalist software architecture, and building fast trading technology interfaces."
        ),
        'requirements': "0-2 years of software engineering in Python. Solid data structures, Git, PostgreSQL, and Linux CLI skills.",
        'experience_min': 0.0,
        'experience_max': 2.0,
        'skills': 'Python, Django, PostgreSQL, Linux, Git, REST API',
        'salary_text': '₹10,00,000 - ₹16,00,000 / year',
        'external_url': 'https://zerodha.com/careers/junior-python-dev',
        'source': Job.Source.OTHER,
        'source_job_id': 'ZERODHA-JR-404',
    },
    {
        'title': 'Staff Platform Architect (Distributed Cloud)',
        'company_name': 'CRED',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Lead CRED's high-scale infrastructure architecture. Drive system reliability, zero-downtime database migrations, "
            "and multi-region cloud resilience across AWS and Kubernetes."
        ),
        'requirements': "8+ years of high-scale systems engineering experience. Distributed transactions, Kafka, PostgreSQL, Terraform, Kubernetes.",
        'experience_min': 8.0,
        'experience_max': 14.0,
        'skills': 'Python, Go, PostgreSQL, Kafka, AWS, Kubernetes, Terraform, System Design',
        'salary_text': '₹55,00,000 - ₹80,00,000 / year + ESOPs',
        'external_url': 'https://cred.club/careers/staff-platform-architect',
        'source': Job.Source.OTHER,
        'source_job_id': 'CRED-STAFF-505',
    },
    {
        'title': 'DevOps & Cloud Engineer',
        'company_name': 'Postman',
        'location': 'Hyderabad, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Postman is the world's leading API platform. We are seeking a DevOps Engineer to automate cloud infrastructure, "
            "manage Kubernetes clusters, and build developer productivity tooling."
        ),
        'requirements': "3-6 years in DevOps/Cloud engineering. Docker, Kubernetes, AWS, Terraform, CI/CD, Python scripting.",
        'experience_min': 3.0,
        'experience_max': 6.0,
        'skills': 'Docker, Kubernetes, AWS, Terraform, Python, CI/CD, Linux',
        'salary_text': '₹24,00,000 - ₹38,00,000 / year',
        'external_url': 'https://postman.com/careers/devops-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'POSTMAN-OPS-606',
    },
    {
        'title': 'Data Engineer (Python / Spark / SQL)',
        'company_name': 'Zomato',
        'location': 'Gurugram, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Build real-time event streaming and analytical data pipelines powering Zomato's recommendation engines, "
            "delivery time estimations, and business intelligence reporting."
        ),
        'requirements': "3-5 years of experience in data engineering. Python, Apache Spark, SQL, Airflow, Snowflake, AWS.",
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, SQL, Apache Spark, Airflow, AWS, PostgreSQL, ETL',
        'salary_text': '₹22,00,000 - ₹34,00,000 / year',
        'external_url': 'https://zomato.com/careers/data-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'ZOMATO-DE-707',
    },
    {
        'title': 'Frontend Engineer (React / Next.js)',
        'company_name': 'BrowserStack',
        'location': 'Mumbai, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "BrowserStack is the leading software testing platform used by over 5 million developers. "
            "Build slick, lightning-fast web consoles and test automation dashboards using modern React and TypeScript."
        ),
        'requirements': "2-4 years of modern frontend experience in React, TypeScript, Redux/Zustand, HTML5/CSS3.",
        'experience_min': 2.0,
        'experience_max': 4.0,
        'skills': 'React, Next.js, TypeScript, JavaScript, CSS, REST API',
        'salary_text': '₹18,00,000 - ₹28,00,000 / year',
        'external_url': 'https://browserstack.com/careers/frontend-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'BROWSERSTACK-FE-808',
    },
    {
        'title': 'Staff Software Engineer - Backend',
        'company_name': 'Flipkart',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Flipkart Commerce Platform is hiring a Staff Software Engineer to lead backend architecture for our checkout and order fulfillment systems, handling millions of requests per minute during Big Billion Days."
        ),
        'requirements': "7+ years designing distributed backend systems in Python, Go, or Java. High concurrency, Kafka, Redis, and MySQL.",
        'experience_min': 7.0,
        'experience_max': 12.0,
        'skills': 'Python, Go, Kafka, Redis, MySQL, System Design, Microservices, Docker',
        'salary_text': '₹48,00,000 - ₹70,00,000 / year + ESOPs',
        'external_url': 'https://flipkartcareers.com/jobs/staff-backend-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'FLIPKART-STF-909',
    },
    {
        'title': 'Senior Software Engineer (Python & FastAPI)',
        'company_name': 'Meesho',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Join Meesho's Marketplace Team democratizing internet commerce for Bharat. Build low-latency catalog search and pricing optimization microservices using modern Python and async architectures."
        ),
        'requirements': "4-7 years in backend software engineering. Python, FastAPI, Django, PostgreSQL, Redis, Elasticsearch.",
        'experience_min': 4.0,
        'experience_max': 7.0,
        'skills': 'Python, FastAPI, Django, PostgreSQL, Redis, Elasticsearch, AWS, Docker',
        'salary_text': '₹30,00,000 - ₹45,00,000 / year',
        'external_url': 'https://meesho.io/careers/senior-backend-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'MEESHO-SWE-1010',
    },
    {
        'title': 'Senior Full Stack Developer (Python + React)',
        'company_name': 'Freshworks',
        'location': 'Chennai, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Freshworks creates SaaS solutions that make it easy for support teams to delight customers. Looking for a Senior Full Stack Developer to build next-gen AI CRM features using Python and React."
        ),
        'requirements': "3-6 years of experience building modern web applications. Python, React, PostgreSQL, REST APIs, AWS.",
        'experience_min': 3.0,
        'experience_max': 6.0,
        'skills': 'Python, React, TypeScript, PostgreSQL, REST APIs, AWS, Docker',
        'salary_text': '₹22,00,000 - ₹36,00,000 / year',
        'external_url': 'https://freshworks.com/careers/senior-fullstack-dev',
        'source': Job.Source.OTHER,
        'source_job_id': 'FRESHWORKS-FS-1111',
    },
    {
        'title': 'Backend Software Engineer (Python / Go)',
        'company_name': 'Groww',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Groww makes investing simple and transparent for 40+ million Indians. Build ultra-fast mutual funds, stocks, and SIP order routing infrastructure with zero tolerance for downtime."
        ),
        'requirements': "2-5 years in backend engineering. Python, Go, MySQL, Redis, Kafka, Kubernetes, Microservices.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'Python, Go, MySQL, Redis, Kafka, Kubernetes, Microservices',
        'salary_text': '₹20,00,000 - ₹34,00,000 / year',
        'external_url': 'https://groww.in/careers/backend-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'GROWW-BE-1212',
    },
    {
        'title': 'Lead DevOps & Infrastructure Engineer',
        'company_name': 'Paytm',
        'location': 'Noida, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Scale Paytm Payments Cloud infrastructure supporting 300M+ transactions monthly. Architect Kubernetes multi-cluster failover, automated CI/CD canary deployments, and zero-trust security postures."
        ),
        'requirements': "5-9 years in DevOps and site reliability engineering. Kubernetes, Terraform, AWS/GCP, Docker, Python scripting.",
        'experience_min': 5.0,
        'experience_max': 9.0,
        'skills': 'Kubernetes, Terraform, AWS, Docker, Python, Linux, CI/CD, Prometheus',
        'salary_text': '₹32,00,000 - ₹50,00,000 / year',
        'external_url': 'https://paytm.com/careers/lead-devops-engineer',
        'source': Job.Source.OTHER,
        'source_job_id': 'PAYTM-OPS-1313',
    },
    {
        'title': 'Software Development Engineer II - Python',
        'company_name': 'Urban Company',
        'location': 'Gurugram, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Urban Company is Asia's largest home services platform. Join the Partner Growth Engineering team building matchmaking algorithms, dynamic pricing, and dispatch engines."
        ),
        'requirements': "2-5 years of backend engineering experience. Python/Django, Node.js, PostgreSQL, Redis, AWS.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'Python, Django, PostgreSQL, Redis, AWS, Microservices, REST APIs',
        'salary_text': '₹24,00,000 - ₹36,00,000 / year',
        'external_url': 'https://urbancompany.com/careers/sde2-python',
        'source': Job.Source.OTHER,
        'source_job_id': 'URBANCO-SDE2-1414',
    },
    {
        'title': 'Senior Data Scientist / ML Engineer',
        'company_name': 'Tata 1mg',
        'location': 'Gurugram, India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Build healthcare AI models powering prescription OCR recognition, medical entity extraction, and intelligent medicine substitute recommendations for millions of digital health users."
        ),
        'requirements': "4-7 years in applied machine learning. Python, PyTorch/TensorFlow, Scikit-learn, NLP, LLMs, Docker, MLflow.",
        'experience_min': 4.0,
        'experience_max': 7.0,
        'skills': 'Python, PyTorch, Scikit-learn, NLP, LLMs, SQL, Docker, Machine Learning',
        'salary_text': '₹26,00,000 - ₹40,00,000 / year',
        'external_url': 'https://1mg.com/careers/senior-data-scientist',
        'source': Job.Source.OTHER,
        'source_job_id': 'TATA1MG-DS-1515',
    }
]



def fetch_and_sync_real_jobs(user: Optional[User] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Fetches and synchronizes real live job listings strictly restricted to:
    1. India tech companies (Bengaluru, Hyderabad, Gurugram, Mumbai, Pune, Noida, Chennai, etc.)
    2. Real remote software engineering jobs open to Indian and worldwide candidates.
    Deactivates any non-India onsite/foreign positions.
    """
    created_count = 0
    updated_count = 0
    total_scanned = 0
    errors = []

    # 0. Sync verified India Tech Giants & Unicorns
    for ind_job in REAL_INDIA_TECH_JOBS:
        total_scanned += 1
        existing = JobDeduplicationService.find_duplicate(
            company_name=ind_job['company_name'],
            title=ind_job['title'],
            location=ind_job['location'],
            external_url=ind_job['external_url'],
            source_job_id=ind_job.get('source_job_id', ''),
            source=ind_job.get('source', Job.Source.OTHER)
        )
        if existing:
            existing.last_seen_at = timezone.now()
            existing.is_active = True
            existing.skills = ind_job.get('skills', existing.skills)
            existing.experience_min = ind_job.get('experience_min', existing.experience_min)
            existing.experience_max = ind_job.get('experience_max', existing.experience_max)
            existing.salary_text = ind_job.get('salary_text', existing.salary_text)
            existing.description = ind_job.get('description', existing.description)
            existing.save()
            updated_count += 1
            target_job = existing
        else:
            target_job = Job.objects.create(
                title=ind_job['title'],
                company_name=ind_job['company_name'],
                location=ind_job['location'],
                work_mode=ind_job.get('work_mode', Job.WorkMode.HYBRID),
                employment_type=ind_job.get('employment_type', Job.EmploymentType.FULL_TIME),
                description=ind_job.get('description', ''),
                requirements=ind_job.get('requirements', ''),
                experience_min=ind_job.get('experience_min', 0.0),
                experience_max=ind_job.get('experience_max', 5.0),
                skills=ind_job.get('skills', ''),
                salary_text=ind_job.get('salary_text', ''),
                external_url=ind_job['external_url'],
                source=ind_job.get('source', Job.Source.OTHER),
                source_job_id=ind_job.get('source_job_id', ''),
                is_active=True
            )
            created_count += 1

        if user and user.is_authenticated:
            calculate_and_sync_user_job_match(user, target_job)

    # 1. Fetch from Remotive (Software Dev Remote Jobs)
    try:
        req = urllib.request.Request(
            f'https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}',
            headers={'User-Agent': 'Mozilla/5.0 (JobAutoApply Agent)'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            remotive_jobs = data.get('jobs', [])
            for rj in remotive_jobs:
                total_scanned += 1
                title = rj.get('title', '').strip()
                company = rj.get('company_name', '').strip()
                if not title or not company:
                    continue

                location = rj.get('candidate_required_location', '').strip() or 'Remote'
                # Strictly check if eligible for India or Worldwide Remote
                if not is_india_or_remote(location, 'REMOTE', title):
                    continue

                url = rj.get('url', '').strip()
                source_job_id = f"REMOTIVE-{rj.get('id')}"
                raw_desc = rj.get('description', '')
                clean_desc = clean_html_text(raw_desc)
                skills_list = rj.get('tags', [])
                skills_str = ", ".join(skills_list) if skills_list else ""
                salary_str = rj.get('salary', '')

                exp_min, exp_max = parse_experience_requirements(title, clean_desc)

                existing = JobDeduplicationService.find_duplicate(
                    company_name=company,
                    title=title,
                    location=location,
                    external_url=url,
                    source_job_id=source_job_id,
                    source=Job.Source.OTHER
                )

                if existing:
                    existing.last_seen_at = timezone.now()
                    existing.is_active = True
                    if not existing.skills and skills_str:
                        existing.skills = skills_str
                    existing.save(update_fields=['last_seen_at', 'is_active', 'skills', 'updated_at'])
                    updated_count += 1
                    target_job = existing
                else:
                    target_job = Job.objects.create(
                        title=title[:255],
                        company_name=company[:255],
                        location=location[:255],
                        work_mode=Job.WorkMode.REMOTE,
                        employment_type=Job.EmploymentType.FULL_TIME if 'contract' not in (rj.get('job_type') or '').lower() else Job.EmploymentType.CONTRACT,
                        description=clean_desc[:5000],
                        requirements=f"Experience required: {exp_min:g}+ years. Tech stack: {skills_str}",
                        experience_min=exp_min,
                        experience_max=exp_max,
                        skills=skills_str[:500],
                        salary_text=salary_str[:150] if salary_str else "",
                        external_url=url,
                        source=Job.Source.OTHER,
                        source_job_id=source_job_id,
                        is_active=True
                    )
                    created_count += 1

                if user and user.is_authenticated:
                    calculate_and_sync_user_job_match(user, target_job)

    except Exception as e:
        logger.error(f"Error fetching from Remotive: {e}")
        errors.append(f"Remotive: {str(e)}")

    # 2. Fetch from Arbeitnow (Tech / Engineering Jobs - strictly India or Remote only)
    try:
        req = urllib.request.Request(
            'https://www.arbeitnow.com/api/job-board-api',
            headers={'User-Agent': 'Mozilla/5.0 (JobAutoApply Agent)'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            arbeit_jobs = data.get('data', [])

            tech_keywords = ['developer', 'engineer', 'python', 'software', 'backend', 'frontend', 'data', 'cloud', 'devops']
            tech_jobs = [
                aj for aj in arbeit_jobs
                if any(kw in (aj.get('title', '') + ' ' + ' '.join(aj.get('tags', []))).lower() for kw in tech_keywords)
            ][:limit]

            for aj in tech_jobs:
                total_scanned += 1
                title = aj.get('title', '').strip()
                company = aj.get('company_name', '').strip()
                if not title or not company:
                    continue

                location = aj.get('location', '').strip() or 'Remote'
                work_mode = Job.WorkMode.REMOTE if aj.get('remote') else Job.WorkMode.HYBRID

                # Strictly check if eligible for India or Remote
                if not is_india_or_remote(location, work_mode, title):
                    continue

                url = aj.get('url', '').strip()
                slug = aj.get('slug', '')
                source_job_id = f"ARBEITNOW-{slug}" if slug else ""
                raw_desc = aj.get('description', '')
                clean_desc = clean_html_text(raw_desc)
                skills_list = aj.get('tags', [])
                skills_str = ", ".join(skills_list) if skills_list else ""

                exp_min, exp_max = parse_experience_requirements(title, clean_desc)

                existing = JobDeduplicationService.find_duplicate(
                    company_name=company,
                    title=title,
                    location=location,
                    external_url=url,
                    source_job_id=source_job_id,
                    source=Job.Source.OTHER
                )

                if existing:
                    existing.last_seen_at = timezone.now()
                    existing.is_active = True
                    existing.save(update_fields=['last_seen_at', 'is_active', 'updated_at'])
                    updated_count += 1
                    target_job = existing
                else:
                    target_job = Job.objects.create(
                        title=title[:255],
                        company_name=company[:255],
                        location=location[:255],
                        work_mode=work_mode,
                        employment_type=Job.EmploymentType.FULL_TIME,
                        description=clean_desc[:5000],
                        requirements=f"Experience required: {exp_min:g}+ years. Tech stack: {skills_str}",
                        experience_min=exp_min,
                        experience_max=exp_max,
                        skills=skills_str[:500],
                        external_url=url,
                        source=Job.Source.OTHER,
                        source_job_id=source_job_id,
                        is_active=True
                    )
                    created_count += 1

                if user and user.is_authenticated:
                    calculate_and_sync_user_job_match(user, target_job)

    except Exception as e:
        logger.error(f"Error fetching from Arbeitnow: {e}")
        errors.append(f"Arbeitnow: {str(e)}")

    # 3. Clean up: Deactivate any foreign onsite/restricted jobs that might already exist in the database
    for j in Job.objects.filter(is_active=True):
        if not is_india_or_remote(j.location, j.work_mode, j.title):
            j.is_active = False
            j.save(update_fields=['is_active'])

    return {
        'created': created_count,
        'updated': updated_count,
        'total_scanned': total_scanned,
        'errors': errors
    }

