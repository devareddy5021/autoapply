import io
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone
from pypdf import PdfWriter
from accounts.models import Profile
from resumes.models import Resume
from jobs.models import Job
from applications.models import Application

class Command(BaseCommand):
    help = "Seed demo user account with full profile, sample PDF resume, and application tracking records"

    def handle(self, *args, **options):
        # 1. Create or retrieve demo user
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@jobautoapply.dev',
                'first_name': 'Alex',
                'last_name': 'Rivera',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        user.set_password('Password123!')
        user.save()

        # 2. Complete Profile
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = "Alex Rivera"
        profile.phone = "+1 (555) 345-6789"
        profile.current_location = "Bengaluru, India"
        profile.preferred_locations = "Bengaluru, Remote, New York"
        profile.work_authorization = "Authorized to work in India & US Remote (B1/B2)"
        profile.years_of_experience = 4.5
        profile.notice_period_days = 15
        profile.preferred_job_titles = "Senior Python & Django Engineer, Backend Lead, Full Stack Developer"
        profile.skills = "Python, Django, PostgreSQL, Docker, Redis, Celery, AWS, React, REST API, Git, Linux, Kubernetes"
        profile.education = "B.Tech in Computer Science and Engineering, National Institute of Technology (2020)"
        profile.certifications = "AWS Certified Solutions Architect - Associate (2024)"
        profile.linkedin_url = "https://linkedin.com/in/alex-rivera-tech"
        profile.github_url = "https://github.com/alexrivera-tech"
        profile.portfolio_url = "https://alexrivera.dev"
        profile.preferred_salary_min = 120000
        profile.preferred_salary_max = 160000
        profile.salary_currency = "USD"
        profile.work_preference = Profile.WorkPreference.REMOTE
        profile.save()

        # 3. Create Sample PDF Resume
        writer = PdfWriter()
        page = writer.add_blank_page(width=595, height=842)  # A4 size
        pdf_stream = io.BytesIO()
        writer.write(pdf_stream)
        pdf_content = pdf_stream.getvalue()

        resume_text = (
            "ALEX RIVERA\n"
            "Senior Python & Django Engineer\n"
            "Email: demo@jobautoapply.dev | Phone: +1 555-345-6789 | Location: Bengaluru / Remote\n\n"
            "SUMMARY\n"
            "Results-driven backend software engineer with 4.5+ years of experience designing scalable RESTful APIs, "
            "asynchronous task pipelines, and cloud microservices in Python, Django, PostgreSQL, and AWS.\n\n"
            "CORE TECHNICAL SKILLS\n"
            "Languages: Python, JavaScript, TypeScript, SQL, Bash\n"
            "Frameworks: Django, Django REST Framework, React, FastAPI, Flask\n"
            "Databases & Queues: PostgreSQL, Redis, Celery, Kafka\n"
            "Infrastructure & Tools: Docker, Kubernetes, AWS (EC2, S3, RDS), Git, Linux, CI/CD\n\n"
            "PROFESSIONAL EXPERIENCE\n"
            "Senior Backend Engineer - FinVantage Labs (2022 - Present)\n"
            "- Architected high-throughput Django REST APIs serving 1M+ daily transactions.\n"
            "- Reduced database query latency by 45% through PostgreSQL indexing and Redis caching.\n"
            "- Spearheaded Docker containerization and automated CI/CD deployment pipelines on AWS.\n\n"
            "Software Engineer - CloudScale Systems (2020 - 2022)\n"
            "- Built background job processing infrastructure with Celery and RabbitMQ.\n"
            "- Integrated third-party payment gateways and webhooks with 99.9% uptime.\n\n"
            "EDUCATION\n"
            "Bachelor of Technology in Computer Science, NIT (2020)\n"
            "CERTIFICATIONS\n"
            "AWS Certified Solutions Architect Associate"
        )

        existing_resume = Resume.objects.filter(user=user, name="Alex Rivera - Senior Python Engineer").first()
        if not existing_resume:
            resume = Resume(
                user=user,
                name="Alex Rivera - Senior Python Engineer",
                version="2026.1",
                is_default=True,
                extracted_text=resume_text,
                file_size_kb=48
            )
            resume.file.save('Alex_Rivera_Resume_2026.pdf', ContentFile(pdf_content), save=True)
            self.stdout.write(self.style.SUCCESS("Sample PDF resume created and attached to demo user."))
        else:
            resume = existing_resume

        # 4. Create Tracked Applications
        jobs = list(Job.objects.all()[:5])
        if jobs:
            statuses = [
                Application.Status.SAVED,
                Application.Status.READY,
                Application.Status.REVIEW_REQUIRED,
                Application.Status.SUBMITTED,
                Application.Status.INTERVIEW,
            ]
            for idx, job in enumerate(jobs):
                app_status = statuses[idx % len(statuses)]
                app, _ = Application.objects.get_or_create(
                    user=user,
                    job=job,
                    defaults={
                        'status': app_status,
                        'resume': resume,
                        'application_url': job.external_url,
                        'applied_at': timezone.now() if app_status in (Application.Status.SUBMITTED, Application.Status.INTERVIEW) else None,
                        'notes': "Applied through portal. Follow-up scheduled with engineering manager." if app_status == Application.Status.INTERVIEW else "Auto-tracked application.",
                        'answers': {
                            'Years of Python experience?': '4.5 years',
                            'Are you authorized to work in India?': 'Yes',
                            'Notice period': '15 days',
                        }
                    }
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo user successfully configured!\n"
                "Credentials: Username: 'demo' | Password: 'Password123!'"
            )
        )
