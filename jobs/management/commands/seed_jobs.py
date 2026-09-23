"""
Management Command: python manage.py seed_jobs (Milestone 3).

Populates the database with realistic development data for India & Remote data roles,
including cross-source deduplication test cases.
Clearly marks all records as development/test data.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job, JobCategory, LocationType
from jobs.services.deduplication import JobDeduplicationService, generate_content_hash
from jobs.services.job_classifier import classify_job
from jobs.services.location_classifier import classify_location

SEED_JOBS_DATA = [
    # 1. Multi-Source Deduplication Scenario 1 (Flipkart Data Engineer)
    {
        'title': 'Data Engineer - Data Platform [Seed]',
        'company_name': 'Flipkart',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Design and scale Flipkart's real-time streaming infrastructure. "
            "Build Spark and Flink event pipelines handling billions of daily events. "
            "Maintain Iceberg data lakes on Azure cloud."
        ),
        'requirements': "3-5 years experience in Python, Apache Spark, Kafka, SQL, and distributed data pipelines.",
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, Apache Spark, Kafka, SQL, Azure, Apache Iceberg, ETL',
        'salary_text': '₹24,00,000 - ₹38,00,000 / year',
        'source': Job.Source.NAUKRI,
        'source_job_id': '150726018007',
        'external_url': 'https://www.naukri.com/job-listings-field-recruiter-flipkart-thiruvananthapuram-0-to-2-years-150726018007?src=cluster&sid=1790141884466822_1&xp=6&px=1',
    },
    {
        'title': 'Data Engineer - Data Platform [Seed]',
        'company_name': 'Flipkart',
        'location': 'Bengaluru, Karnataka, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Design and scale Flipkart's real-time streaming infrastructure. "
            "Build Spark and Flink event pipelines handling billions of daily events."
        ),
        'requirements': "3+ years Python, Spark, Kafka, SQL.",
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, Spark, Kafka, SQL, Azure',
        'salary_text': '₹24,00,000 - ₹38,00,000 / year',
        'source': Job.Source.LINKEDIN,
        'source_job_id': '4028374921',
        'external_url': 'https://www.linkedin.com/jobs/view/4028374921',
    },
    {
        'title': 'Data Engineer - Data Platform [Seed]',
        'company_name': 'Flipkart',
        'location': 'Bengaluru',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': "[Development Seed Record] Real-time data streaming engineering at Flipkart.",
        'requirements': "Python, Spark, SQL.",
        'experience_min': 3.0,
        'experience_max': 5.0,
        'skills': 'Python, Spark, SQL, Kafka',
        'salary_text': '₹24L - ₹38L',
        'source': Job.Source.INDEED,
        'source_job_id': '7a4b8c9d0e1f2a3b',
        'external_url': 'https://in.indeed.com/viewjob?jk=7a4b8c9d0e1f2a3b',
    },

    # 2. Junior Data Engineer (Swiggy)
    {
        'title': 'Junior Data Engineer [Seed]',
        'company_name': 'Swiggy',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Build ingestion pipelines and transformation workflows for food delivery logistics analytics. "
            "Collaborate with senior data engineers on DBT models and Snowflake data marts."
        ),
        'requirements': "0-2 years software or data engineering in Python and SQL. Familiarity with Airflow and Snowflake.",
        'experience_min': 0.0,
        'experience_max': 2.0,
        'skills': 'Python, SQL, Snowflake, Airflow, DBT, Data Engineering',
        'salary_text': '₹12,00,000 - ₹18,00,000 / year',
        'source': Job.Source.NAUKRI,
        'source_job_id': '180826019234',
        'external_url': 'https://www.naukri.com/job-listings-software-data-engineer-swiggy-bengaluru-0-to-3-years-180826019234',
    },

    # 3. Associate Data Analyst (PhonePe)
    {
        'title': 'Associate Data Analyst [Seed]',
        'company_name': 'PhonePe',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Analyze transaction failure patterns, merchant settlement cycles, and fraud indicators. "
            "Write complex SQL queries and build automated executive dashboards in Power BI."
        ),
        'requirements': "1-3 years in business or product data analytics. Advanced SQL, Python, Excel, and Power BI.",
        'experience_min': 1.0,
        'experience_max': 3.0,
        'skills': 'SQL, Python, Power BI, Excel, Data Analytics, Dashboards',
        'salary_text': '₹10,00,000 - ₹16,00,000 / year',
        'source': Job.Source.LINKEDIN,
        'source_job_id': '3987123456',
        'external_url': 'https://www.linkedin.com/jobs/view/3987123456',
    },

    # 4. Remote Worldwide / India Machine Learning Engineer (Postman)
    {
        'title': 'Machine Learning Engineer - AI Tools [Seed]',
        'company_name': 'Postman',
        'location': 'Remote India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Train and serve generative AI and embedding models powering Postman's automated API testing, "
            "smart documentation generators, and schema discovery assistants."
        ),
        'requirements': "2-5 years in applied machine learning. PyTorch, Hugging Face, LLM fine-tuning, Python, Docker.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'Python, PyTorch, LLM, Machine Learning, Docker, FastAPI, NLP',
        'salary_text': '₹28,00,000 - ₹45,00,000 / year',
        'source': Job.Source.WELLFOUND,
        'source_job_id': 'SEED-POSTMAN-ML-04',
        'external_url': 'https://wellfound.com/jobs?role=Machine+Learning+Engineer',
    },

    # 5. Remote Worldwide Data Scientist (GitLab / Canonical Style)
    {
        'title': 'Senior Data Scientist [Seed]',
        'company_name': 'OmniData Labs',
        'location': 'Remote Worldwide',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Open worldwide to engineers in India and internationally. "
            "Build causal inference models and recommendation systems for developer tools."
        ),
        'requirements': "4+ years in data science. Python, Scikit-learn, SQL, causal modeling, statistics.",
        'experience_min': 4.0,
        'experience_max': 7.0,
        'skills': 'Python, SQL, Scikit-learn, Statistics, Data Science, Machine Learning',
        'salary_text': '$90,000 - $130,000 / year',
        'source': Job.Source.LINKEDIN,
        'source_job_id': 'SEED-OMNI-DS-05',
        'external_url': 'https://www.linkedin.com/jobs/search/?keywords=Remote%20Data%20Scientist',
    },

    # 6. Azure Cloud Data Engineer (TCS / Hyderabad)
    {
        'title': 'Azure Data Engineer [Seed]',
        'company_name': 'Tata Consultancy Services',
        'location': 'Hyderabad, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Build enterprise data solutions using Azure Data Factory, Databricks, and Synapse Analytics. "
            "Implement automated CI/CD for ETL pipelines and data governance."
        ),
        'requirements': "3-6 years of Azure data stack experience. Azure Data Factory, Databricks, PySpark, SQL.",
        'experience_min': 3.0,
        'experience_max': 6.0,
        'skills': 'Azure, Databricks, PySpark, Azure Data Factory, SQL, ETL',
        'salary_text': '₹14,00,000 - ₹22,00,000 / year',
        'source': Job.Source.NAUKRI,
        'source_job_id': '220726015542',
        'external_url': 'https://www.naukri.com/job-listings-azure-data-engineer-tata-consultancy-services-hyderabad-3-to-6-years-220726015542',
    },

    # 7. Power BI Developer / BI Engineer (Infosys / Pune)
    {
        'title': 'Power BI Developer [Seed]',
        'company_name': 'Infosys',
        'location': 'Pune, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Develop intuitive, self-service enterprise reports and executive dashboards in Power BI. "
            "Write complex DAX measures, optimize tabular data models, and connect to SQL Server data marts."
        ),
        'requirements': "2-5 years BI development experience. Power BI, DAX, Power Query, SQL.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'Power BI, DAX, SQL, Power Query, Business Intelligence, Dashboards',
        'salary_text': '₹11,00,000 - ₹17,00,000 / year',
        'source': Job.Source.FOUNDIT,
        'source_job_id': 'SEED-INFY-BI-07',
        'external_url': 'https://www.foundit.in/srp/results?query=Infosys%20Power%20BI',
    },

    # 8. SQL Developer & Data Warehouse Engineer (Groww / Bengaluru)
    {
        'title': 'SQL Developer / Data Warehouse Engineer [Seed]',
        'company_name': 'Groww',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Architect dimensional models, star schemas, and stored procedures for financial transaction ledgers. "
            "Fine-tune SQL query performance on multi-terabyte PostgreSQL and ClickHouse clusters."
        ),
        'requirements': "2-5 years in database development and data warehousing. Advanced PostgreSQL, SQL, PL/pgSQL, Data Modeling.",
        'experience_min': 2.0,
        'experience_max': 5.0,
        'skills': 'SQL, PostgreSQL, Data Warehouse, PL/pgSQL, Query Optimization, ClickHouse',
        'salary_text': '₹18,00,000 - ₹28,00,000 / year',
        'source': Job.Source.CUTSHORT,
        'source_job_id': 'SEED-GROWW-SQL-08',
        'external_url': 'https://cutshort.io/jobs?search=Groww%20SQL',
    },

    # 9. Data Engineering Intern (Internshala / Gurgaon)
    {
        'title': 'Data Engineering Intern [Seed]',
        'company_name': 'Zomato',
        'location': 'Gurugram, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.INTERNSHIP,
        'description': (
            "[Development Seed Record] Assist in developing automated Python scraping pipelines, cleaning restaurant menu catalog datasets, "
            "and writing automated test suites for data pipeline validation."
        ),
        'requirements': "Recent graduate or final year student in CS/IT. Strong Python, SQL, and problem-solving skills.",
        'experience_min': 0.0,
        'experience_max': 1.0,
        'skills': 'Python, SQL, Pandas, Git, Data Engineering',
        'salary_text': '₹40,000 / month stipend',
        'source': Job.Source.INTERNSHALA,
        'source_job_id': 'SEED-ZOMATO-INTERN-09',
        'external_url': 'https://internshala.com/internships/keywords-data-engineer/',
    },

    # 10. Big Data Engineer - Spark & Databricks (Razorpay / Bengaluru)
    {
        'title': 'Big Data Engineer - Databricks [Seed]',
        'company_name': 'Razorpay',
        'location': 'Bengaluru, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Scale Razorpay's data platform infrastructure. "
            "Build Spark/Scala/Python pipelines on Databricks Delta Lake to process millions of transactions per second."
        ),
        'requirements': "4-7 years in big data engineering. PySpark, Databricks, Delta Lake, AWS, Kafka, SQL.",
        'experience_min': 4.0,
        'experience_max': 7.0,
        'skills': 'PySpark, Databricks, Delta Lake, AWS, Kafka, SQL, Data Engineering',
        'salary_text': '₹28,00,000 - ₹42,00,000 / year',
        'source': Job.Source.INSTAHYRE,
        'source_job_id': 'SEED-RAZORPAY-BDE-10',
        'external_url': 'https://www.instahyre.com/jobs/?search=Razorpay%20Big%20Data',
    },

    # 11. Associate Data Scientist (Noida / Delhi NCR)
    {
        'title': 'Associate Data Scientist [Seed]',
        'company_name': 'Paytm',
        'location': 'Noida, Delhi NCR, India',
        'work_mode': Job.WorkMode.HYBRID,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Build credit risk underwriting algorithms and merchant churn prediction models using Scikit-learn and XGBoost."
        ),
        'requirements': "1-3 years in data science. Python, SQL, Scikit-learn, XGBoost, Pandas.",
        'experience_min': 1.0,
        'experience_max': 3.0,
        'skills': 'Python, SQL, Scikit-learn, XGBoost, Pandas, Data Science',
        'salary_text': '₹12,00,000 - ₹18,00,000 / year',
        'source': Job.Source.NAUKRI,
        'source_job_id': '190626014321',
        'external_url': 'https://www.naukri.com/job-listings-associate-data-scientist-paytm-noida-1-to-3-years-190626014321',
    },

    # 12. Remote India Analytics Engineer (BrowserStack)
    {
        'title': 'Analytics Engineer [Seed]',
        'company_name': 'BrowserStack',
        'location': 'Remote India',
        'work_mode': Job.WorkMode.REMOTE,
        'employment_type': Job.EmploymentType.FULL_TIME,
        'description': (
            "[Development Seed Record] Bridge the gap between data engineering and business analytics. "
            "Own data transformations in DBT, orchestrate DAGs in Airflow, and model warehouse tables in Snowflake."
        ),
        'requirements': "2-4 years in analytics or data engineering. SQL, DBT, Snowflake, Airflow, Python.",
        'experience_min': 2.0,
        'experience_max': 4.0,
        'skills': 'SQL, DBT, Snowflake, Airflow, Python, Analytics Engineering',
        'salary_text': '₹20,00,000 - ₹32,00,000 / year',
        'source': Job.Source.LINKEDIN,
        'source_job_id': 'SEED-BROWSERSTACK-AE-12',
        'external_url': 'https://www.linkedin.com/jobs/search/?keywords=BrowserStack%20Analytics%20Engineer',
    },
]


class Command(BaseCommand):
    help = "Seeds database with realistic development data for India & Remote data roles and multi-source deduplication."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding realistic development data for India & Remote data jobs..."))

        created_count = 0
        merged_count = 0

        for item in SEED_JOBS_DATA:
            company = item['company_name']
            title = item['title']
            location = item['location']
            external_url = item['external_url']
            source = item['source']
            source_job_id = item['source_job_id']
            description = item['description']
            skills = item['skills']

            # 1. Geographic classification
            loc_res = classify_location(location=location, work_mode=item['work_mode'], description=description, title=title)
            # 2. Role classification
            role_res = classify_job(title=title, description=description, skills=[s.strip() for s in skills.split(',')])

            # 3. Content hash
            content_hash = generate_content_hash(company, title, location, description)

            # 4. Deduplication
            existing = JobDeduplicationService.find_duplicate(
                company_name=company,
                title=title,
                location=location,
                external_url=external_url,
                source_job_id=source_job_id,
                source=source,
                content_hash=content_hash,
                description=description
            )

            if existing:
                JobDeduplicationService.register_or_merge_source(
                    job=existing,
                    source=source,
                    external_url=external_url,
                    source_job_id=source_job_id
                )
                merged_count += 1
                self.stdout.write(f"  [Deduplicated & Merged Source] '{title}' at {company} -> Found on: {existing.sources_list}")
            else:
                Job.objects.create(
                    title=title,
                    company_name=company,
                    location=location,
                    work_mode=item['work_mode'],
                    employment_type=item['employment_type'],
                    job_category=role_res['category'],
                    category_confidence=role_res['confidence'],
                    country=loc_res['country'],
                    is_india=loc_res['is_india'],
                    is_remote=loc_res['is_remote'],
                    location_type=loc_res['location_type'],
                    matched_keywords=role_res['matched_keywords'],
                    description=description,
                    requirements=item.get('requirements', ''),
                    experience_min=item['experience_min'],
                    experience_max=item['experience_max'],
                    skills=skills,
                    salary_text=item['salary_text'],
                    source=source,
                    source_job_id=source_job_id,
                    external_url=external_url,
                    content_hash=content_hash,
                    source_urls=[{
                        'source': source,
                        'url': external_url,
                        'source_job_id': source_job_id,
                        'discovered_at': timezone.now().isoformat(),
                    }],
                    first_seen_at=timezone.now(),
                    last_seen_at=timezone.now(),
                    is_active=True
                )
                created_count += 1
                self.stdout.write(f"  [Created Canonical Job] '{title}' at {company} ({location}) - Category: {role_res['category']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nFinished seeding jobs! Created {created_count} canonical jobs; merged {merged_count} cross-platform duplicates."
        ))
