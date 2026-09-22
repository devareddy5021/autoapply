from django.core.management.base import BaseCommand
from jobs.models import Job

SAMPLE_JOBS = [
    {
        'title': 'Senior Python & Django Engineer',
        'company': 'CloudScale Systems',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'description': (
            "We are seeking an experienced Senior Python/Django Engineer to build high-throughput web applications "
            "and real-time services. Responsibilities include designing RESTful APIs, optimizing PostgreSQL queries, "
            "implementing Celery task queues, and architecting scalable backend microservices. "
            "Requires solid knowledge of Docker, AWS, CI/CD pipelines, and writing robust automated tests."
        ),
        'salary_min': 140000,
        'salary_max': 175000,
        'salary_currency': 'USD',
        'salary_text': '$140,000 - $175,000 / year + Equity',
        'experience_required_years': 4.0,
        'skills': 'Python, Django, PostgreSQL, Docker, Redis, Celery, AWS, REST API, Git',
        'source': Job.Source.LINKEDIN,
        'external_url': 'https://www.linkedin.com/jobs/view/100101',
        'external_job_id': 'LI-100101',
    },
    {
        'title': 'Full Stack Developer (Python / React)',
        'company': 'FinVantage Labs',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'description': (
            "FinVantage is expanding its core engineering team. You will build user-facing financial dashboards "
            "with React and TypeScript, integrated with Django and PostgreSQL backend services. "
            "Must be proficient in modern JavaScript, HTML/CSS, RESTful API design, and asynchronous worker systems."
        ),
        'salary_min': 90000,
        'salary_max': 120000,
        'salary_currency': 'USD',
        'salary_text': '$90,000 - $120,000 (INR 25 - 35 LPA equivalent)',
        'experience_required_years': 3.0,
        'skills': 'Python, Django, React, TypeScript, PostgreSQL, REST API, Docker, Git',
        'source': Job.Source.NAUKRI,
        'external_url': 'https://www.naukri.com/job-listings/finvantage-2002',
        'external_job_id': 'NK-2002',
    },
    {
        'title': 'Backend Software Engineer - Automation Platform',
        'company': 'PulseFlow Tech',
        'location': 'New York, NY',
        'work_mode': Job.WorkMode.HYBRID,
        'description': (
            "Join PulseFlow to build enterprise workflow automation infrastructure. "
            "You will leverage Python, Playwright/Selenium for web data extraction, Celery for queue processing, "
            "and Redis for caching. Strong Linux, Git, and database performance optimization skills are essential."
        ),
        'salary_min': 130000,
        'salary_max': 160000,
        'salary_currency': 'USD',
        'salary_text': '$130,000 - $160,000 / yr',
        'experience_required_years': 3.5,
        'skills': 'Python, Celery, Redis, Selenium, Playwright, PostgreSQL, Linux, Docker',
        'source': Job.Source.WELLFOUND,
        'external_url': 'https://wellfound.com/jobs/pulseflow-3003',
        'external_job_id': 'WF-3003',
    },
    {
        'title': 'Lead Cloud & Backend Architect',
        'company': 'Nexis Global',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'description': (
            "Nexis Global is looking for a Lead Architect to oversee our distributed cloud platform. "
            "You will lead architectural decisions for scalable Django APIs, microservices in Kubernetes, "
            "and event-driven data streaming with Kafka. Must have strong leadership and mentoring experience."
        ),
        'salary_min': 170000,
        'salary_max': 210000,
        'salary_currency': 'USD',
        'salary_text': '$170,000 - $210,000 / yr',
        'experience_required_years': 7.0,
        'skills': 'Python, Django, Kubernetes, AWS, Kafka, PostgreSQL, CI/CD, Architecture',
        'source': Job.Source.INDEED,
        'external_url': 'https://www.indeed.com/viewjob?jk=nexis-4004',
        'external_job_id': 'IND-4004',
    },
    {
        'title': 'Data Platform Engineer',
        'company': 'DataStream Analytics',
        'location': 'Hyderabad, India',
        'work_mode': Job.WorkMode.HYBRID,
        'description': (
            "Build reliable data ingestion pipelines, automated ETL workflows, and reporting APIs. "
            "Experience with Python, SQL, PostgreSQL, Pandas, and Airflow or Celery is highly valued."
        ),
        'salary_min': 85000,
        'salary_max': 115000,
        'salary_currency': 'USD',
        'salary_text': '$85,000 - $115,000',
        'experience_required_years': 2.5,
        'skills': 'Python, SQL, PostgreSQL, Pandas, Docker, Airflow, Git',
        'source': Job.Source.NAUKRI,
        'external_url': 'https://www.naukri.com/job-listings/datastream-5005',
        'external_job_id': 'NK-5005',
    },
    {
        'title': 'Junior Python Developer',
        'company': 'OpenSource Innovations',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'description': (
            "Great opportunity for an ambitious junior engineer to contribute to open-source developer tooling. "
            "You will develop REST APIs using Django and FastAPI, write comprehensive unit tests, and collaborate on GitHub."
        ),
        'salary_min': 75000,
        'salary_max': 95000,
        'salary_currency': 'USD',
        'salary_text': '$75,000 - $95,000',
        'experience_required_years': 1.0,
        'skills': 'Python, Django, Git, REST API, SQLite, PostgreSQL',
        'source': Job.Source.WELLFOUND,
        'external_url': 'https://wellfound.com/jobs/opensource-6006',
        'external_job_id': 'WF-6006',
    },
    {
        'title': 'Staff Software Engineer - Infrastructure',
        'company': 'Apex Enterprise Cloud',
        'location': 'San Francisco, CA',
        'work_mode': Job.WorkMode.ON_SITE,
        'description': (
            "Apex Enterprise Cloud needs a Staff Infrastructure Engineer to optimize core distributed systems. "
            "Requires deep knowledge of Linux internals, container orchestrators, automated deployment pipelines, "
            "and site reliability engineering."
        ),
        'salary_min': 190000,
        'salary_max': 240000,
        'salary_currency': 'USD',
        'salary_text': '$190,000 - $240,000 + Bonus',
        'experience_required_years': 8.0,
        'skills': 'Python, Go, Linux, Kubernetes, Terraform, AWS, Docker',
        'source': Job.Source.LINKEDIN,
        'external_url': 'https://www.linkedin.com/jobs/view/700701',
        'external_job_id': 'LI-700701',
    },
    {
        'title': 'Python Backend Developer (Contract/Freelance)',
        'company': 'Vanguard Digital',
        'location': 'London, UK (Remote ok)',
        'work_mode': Job.WorkMode.REMOTE,
        'description': (
            "Looking for a skilled Python developer to help integrate third-party payment and CRM webhooks. "
            "Fast-paced environment using Django REST Framework and Celery background workers."
        ),
        'salary_min': 100000,
        'salary_max': 130000,
        'salary_currency': 'USD',
        'salary_text': '£80,000 - £100,000 equiv.',
        'experience_required_years': 3.0,
        'skills': 'Python, Django, REST API, Celery, Redis, Git',
        'source': Job.Source.INDEED,
        'external_url': 'https://www.indeed.com/viewjob?jk=vanguard-8008',
        'external_job_id': 'IND-8008',
    },
]

class Command(BaseCommand):
    help = "Seed realistic sample jobs for testing JobAutoApply matching and dashboard"

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for item in SAMPLE_JOBS:
            duplicate = Job.find_duplicate(
                company=item['company'],
                title=item['title'],
                location=item['location'],
                external_url=item['external_url'],
                external_job_id=item['external_job_id']
            )
            if duplicate:
                existing_count += 1
            else:
                Job.objects.create(**item)
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed demo data: {created_count} jobs created, {existing_count} existing."
            )
        )
