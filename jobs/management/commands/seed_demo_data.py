from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from jobs.services import JobDeduplicationService

now = timezone.now()

SAMPLE_JOBS = [
    {
        'title': 'Senior Python & Django Engineer',
        'company_name': 'CloudScale Systems',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "CloudScale Systems is looking for an experienced Senior Python/Django Engineer to architect "
            "high-throughput web applications, RESTful microservices, and asynchronous event streams. "
            "You will lead architectural decisions, optimize database performance, and build resilient infrastructure."
        ),
        'responsibilities': (
            "- Architect and maintain distributed Django REST APIs serving 2M+ active requests.\n"
            "- Implement asynchronous task pipelines with Celery and Redis.\n"
            "- Optimize PostgreSQL indexes, partition queries, and manage connection pools.\n"
            "- Collaborate with frontend teams to deliver seamless user experiences."
        ),
        'requirements': (
            "- 4+ years of professional backend engineering in Python & Django.\n"
            "- Strong proficiency in PostgreSQL schema design, optimization, and transaction handling.\n"
            "- Hands-on Docker, Kubernetes, and AWS (EC2, S3, RDS) cloud experience.\n"
            "- Solid foundation in writing automated unit and integration test suites."
        ),
        'salary_min': 140000,
        'salary_max': 175000,
        'salary_currency': 'USD',
        'salary_text': '$140,000 - $175,000 / year + Equity',
        'experience_min': 4.0,
        'experience_max': 7.0,
        'skills': 'Python, Django, PostgreSQL, Docker, Redis, Celery, AWS, REST API, Git',
        'source': Job.Source.LINKEDIN,
        'source_job_id': 'LI-100101',
        'external_url': 'https://www.linkedin.com/jobs/view/100101',
        'posted_at': now - timedelta(days=2),
    },
    {
        'title': 'Full Stack Developer (Python / React)',
        'company_name': 'FinVantage Labs',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "FinVantage is expanding its core engineering team. You will build user-facing financial analytics dashboards "
            "with React and TypeScript, integrated with scalable Django and PostgreSQL backend services."
        ),
        'responsibilities': (
            "- Build reusable React/TypeScript interface components and data visualization widgets.\n"
            "- Develop secure REST APIs and WebSocket endpoints in Django.\n"
            "- Ensure fast render times, responsive layouts, and cross-browser consistency.\n"
            "- Participate in sprint planning, code reviews, and architectural syncs."
        ),
        'requirements': (
            "- 3+ years experience across modern JavaScript/TypeScript and Python.\n"
            "- Practical expertise with React, hooks, state management, and HTML/CSS.\n"
            "- Strong knowledge of Django REST Framework and relational databases.\n"
            "- Experience with Git version control and containerized workflows."
        ),
        'salary_min': 90000,
        'salary_max': 120000,
        'salary_currency': 'USD',
        'salary_text': '$90,000 - $120,000 (INR 25 - 35 LPA equivalent)',
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, Django, React, TypeScript, PostgreSQL, REST API, Docker, Git',
        'source': Job.Source.NAUKRI,
        'source_job_id': 'NK-2002',
        'external_url': 'https://www.naukri.com/job-listings/finvantage-2002',
        'posted_at': now - timedelta(days=1),
    },
    {
        'title': 'Backend Software Engineer - Automation Platform',
        'company_name': 'PulseFlow Tech',
        'location': 'New York, NY',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Join PulseFlow to build enterprise workflow automation infrastructure. "
            "You will leverage Python, Playwright/Selenium for web data extraction, Celery for queue processing, "
            "and Redis for caching."
        ),
        'responsibilities': (
            "- Develop web scrapers, crawler connectors, and data parsing pipelines.\n"
            "- Manage worker queues and asynchronous job retries with Celery.\n"
            "- Monitor automated process execution and handle CAPTCHAs and bot detection.\n"
            "- Write clean, maintainable Python code with comprehensive test coverage."
        ),
        'requirements': (
            "- 3+ years of Python engineering experience.\n"
            "- Deep familiarity with browser automation (Playwright, Puppeteer, or Selenium).\n"
            "- Strong Linux shell scripting and debugging skills.\n"
            "- Understanding of HTTP protocols, DOM parsing, and proxies."
        ),
        'salary_min': 130000,
        'salary_max': 160000,
        'salary_currency': 'USD',
        'salary_text': '$130,000 - $160,000 / yr',
        'experience_min': 3.5,
        'experience_max': 6.0,
        'skills': 'Python, Celery, Redis, Selenium, Playwright, PostgreSQL, Linux, Docker',
        'source': Job.Source.WELLFOUND,
        'source_job_id': 'WF-3003',
        'external_url': 'https://wellfound.com/jobs/pulseflow-3003',
        'posted_at': now - timedelta(days=3),
    },
    {
        'title': 'Lead Cloud & Backend Architect',
        'company_name': 'Nexis Global',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Nexis Global is looking for a Lead Architect to oversee our distributed cloud platform. "
            "You will lead architectural decisions for scalable Django APIs, microservices in Kubernetes, "
            "and event-driven data streaming with Kafka."
        ),
        'responsibilities': (
            "- Define cloud system topology, disaster recovery plans, and scalability blueprints.\n"
            "- Mentor 12+ software engineers across backend and DevOps disciplines.\n"
            "- Drive microservices decoupled architecture with Kafka and event sourcing.\n"
            "- Champion security, compliance, and automated CI/CD pipelines."
        ),
        'requirements': (
            "- 7+ years of experience architecting large-scale backend systems.\n"
            "- Proven leadership in Kubernetes container orchestration and AWS infrastructure.\n"
            "- Mastery of Python, Django, distributed caching, and streaming queues.\n"
            "- Excellent stakeholder communication and strategic vision."
        ),
        'salary_min': 170000,
        'salary_max': 210000,
        'salary_currency': 'USD',
        'salary_text': '$170,000 - $210,000 / yr',
        'experience_min': 7.0,
        'experience_max': 10.0,
        'skills': 'Python, Django, Kubernetes, AWS, Kafka, PostgreSQL, CI/CD, Architecture',
        'source': Job.Source.INDEED,
        'source_job_id': 'IND-4004',
        'external_url': 'https://www.indeed.com/viewjob?jk=nexis-4004',
        'posted_at': now - timedelta(days=5),
    },
    {
        'title': 'Data Platform Engineer',
        'company_name': 'DataStream Analytics',
        'location': 'Hyderabad, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Build reliable data ingestion pipelines, automated ETL workflows, and reporting APIs. "
            "Experience with Python, SQL, PostgreSQL, Pandas, and Airflow or Celery is highly valued."
        ),
        'responsibilities': (
            "- Design batch and streaming ETL pipelines aggregating data from multiple third-party sources.\n"
            "- Create automated data validation checks and schema migrations.\n"
            "- Optimize complex analytical SQL queries for business intelligence reporting.\n"
            "- Maintain data warehouse models and automated Airflow DAGs."
        ),
        'requirements': (
            "- 2.5+ years of data engineering or Python development.\n"
            "- Advanced SQL knowledge including window functions and query execution plans.\n"
            "- Experience with Python (Pandas, PySpark, SQLAlchemy).\n"
            "- Familiarity with Apache Airflow or Celery orchestrators."
        ),
        'salary_min': 85000,
        'salary_max': 115000,
        'salary_currency': 'USD',
        'salary_text': '$85,000 - $115,000 (INR 22 - 30 LPA)',
        'experience_min': 2.5,
        'experience_max': 4.5,
        'skills': 'Python, SQL, PostgreSQL, Pandas, Docker, Airflow, Git',
        'source': Job.Source.NAUKRI,
        'source_job_id': 'NK-5005',
        'external_url': 'https://www.naukri.com/job-listings/datastream-5005',
        'posted_at': now - timedelta(days=4),
    },
    {
        'title': 'Junior Python Developer',
        'company_name': 'OpenSource Innovations',
        'location': 'Remote',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.INTERNSHIP,
        'description': (
            "Great opportunity for an ambitious junior engineer to contribute to open-source developer tooling. "
            "You will develop REST APIs using Django and FastAPI, write comprehensive unit tests, and collaborate on GitHub."
        ),
        'responsibilities': (
            "- Write clean, well-tested Python endpoints for open-source CLI and web tools.\n"
            "- Fix reported bugs, write reproduction test cases, and document API behavior.\n"
            "- Review pull requests and participate in developer community discussions."
        ),
        'requirements': (
            "- Solid Python fundamentals (OOP, data structures, exceptions).\n"
            "- Experience with Django, Flask, or FastAPI through projects or internships.\n"
            "- Familiarity with Git, GitHub pull request workflows, and basic SQL."
        ),
        'salary_min': 60000,
        'salary_max': 80000,
        'salary_currency': 'USD',
        'salary_text': '$60,000 - $80,000 / yr',
        'experience_min': 1.0,
        'experience_max': 2.0,
        'skills': 'Python, Django, Git, REST API, SQLite, PostgreSQL',
        'source': Job.Source.WELLFOUND,
        'source_job_id': 'WF-6006',
        'external_url': 'https://wellfound.com/jobs/opensource-6006',
        'posted_at': now - timedelta(days=2),
    },
    {
        'title': 'Staff Software Engineer - Infrastructure',
        'company_name': 'Apex Enterprise Cloud',
        'location': 'San Francisco, CA',
        'work_mode': Job.WorkMode.ONSITE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "Apex Enterprise Cloud needs a Staff Infrastructure Engineer to optimize core distributed systems. "
            "Requires deep knowledge of Linux internals, container orchestrators, automated deployment pipelines, "
            "and site reliability engineering."
        ),
        'responsibilities': (
            "- Scale multi-region Kubernetes clusters supporting 99.99% availability.\n"
            "- Write infrastructure as code using Terraform and Ansible.\n"
            "- Lead incident response, post-mortems, and root cause analyses.\n"
            "- Establish company-wide observability standards (Prometheus, Grafana, OpenTelemetry)."
        ),
        'requirements': (
            "- 8+ years in cloud infrastructure, SRE, or backend platforms.\n"
            "- Mastery of Linux system internals, networking, and kernel tuning.\n"
            "- Extensive production experience with Go, Python, and Kubernetes.\n"
            "- Demonstrated expertise managing multi-cloud enterprise footprints."
        ),
        'salary_min': 190000,
        'salary_max': 240000,
        'salary_currency': 'USD',
        'salary_text': '$190,000 - $240,000 + Bonus + Equity',
        'experience_min': 8.0,
        'experience_max': 12.0,
        'skills': 'Python, Go, Linux, Kubernetes, Terraform, AWS, Docker',
        'source': Job.Source.LINKEDIN,
        'source_job_id': 'LI-700701',
        'external_url': 'https://www.linkedin.com/jobs/view/700701',
        'posted_at': now - timedelta(days=6),
    },
    {
        'title': 'Python Backend Developer (Contract)',
        'company_name': 'Vanguard Digital',
        'location': 'London, UK',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.CONTRACT,
        'description': (
            "Looking for a skilled Python contractor to help integrate third-party payment and CRM webhooks. "
            "Fast-paced environment using Django REST Framework and Celery background workers."
        ),
        'responsibilities': (
            "- Implement Stripe and PayPal webhook handlers with idempotent transaction checks.\n"
            "- Build CRM data sync workers updating Salesforce and HubSpot leads.\n"
            "- Write integration tests with mock services to guarantee reliability."
        ),
        'requirements': (
            "- 3+ years experience with Django REST Framework.\n"
            "- Prior experience handling payment gateways and webhooks.\n"
            "- Good knowledge of Redis task queues and background concurrency."
        ),
        'salary_min': 100000,
        'salary_max': 130000,
        'salary_currency': 'USD',
        'salary_text': '£80,000 - £100,000 equiv. / Contract',
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, Django, REST API, Celery, Redis, Git',
        'source': Job.Source.INDEED,
        'source_job_id': 'IND-8008',
        'external_url': 'https://www.indeed.com/viewjob?jk=vanguard-8008',
        'posted_at': now - timedelta(days=1),
    },
]

class Command(BaseCommand):
    help = "Seed realistic sample jobs for testing Milestone 2 Job Search & Dashboard"

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for item in SAMPLE_JOBS:
            duplicate = JobDeduplicationService.find_duplicate(
                company_name=item['company_name'],
                title=item['title'],
                location=item['location'],
                external_url=item['external_url'],
                source_job_id=item['source_job_id'],
                source=item['source']
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
