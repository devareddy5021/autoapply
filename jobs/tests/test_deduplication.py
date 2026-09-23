"""
Tests for 4-Tier Deduplication and Multi-Source Merging (Milestone 3, Section 31).
"""

from django.test import TestCase
from jobs.models import Job
from jobs.services.deduplication import JobDeduplicationService, generate_content_hash, normalize_title


class DeduplicationTests(TestCase):
    def test_cross_platform_deduplication(self):
        """
        Verify that the exact same job appearing on LinkedIn, Naukri, and Indeed
        results in exactly ONE canonical Job record in the database.
        """
        # 1. First appearance on LinkedIn
        job = Job.objects.create(
            title="Senior Data Engineer",
            company_name="Acme Analytics",
            location="Bengaluru, India",
            source=Job.Source.LINKEDIN,
            source_job_id="ACME-LI-101",
            external_url="https://www.linkedin.com/jobs/view/101",
            source_urls=[{
                'source': Job.Source.LINKEDIN,
                'url': "https://www.linkedin.com/jobs/view/101",
                'source_job_id': "ACME-LI-101"
            }]
        )

        initial_count = Job.objects.filter(company_name="Acme Analytics").count()
        self.assertEqual(initial_count, 1)

        # 2. Second appearance on Naukri
        dup_naukri = JobDeduplicationService.find_duplicate(
            company_name="Acme Analytics",
            title="Senior Data Engineer (Immediate Joiner)",  # noisy title variation
            location="Bengaluru",
            external_url="https://www.naukri.com/job-listings-acme-101",
            source_job_id="ACME-NAUKRI-101",
            source=Job.Source.NAUKRI
        )
        self.assertIsNotNone(dup_naukri)
        self.assertEqual(dup_naukri.id, job.id)

        # Merge Naukri source
        JobDeduplicationService.register_or_merge_source(
            job=dup_naukri,
            source=Job.Source.NAUKRI,
            external_url="https://www.naukri.com/job-listings-acme-101",
            source_job_id="ACME-NAUKRI-101"
        )

        # 3. Third appearance on Indeed
        dup_indeed = JobDeduplicationService.find_duplicate(
            company_name="Acme Analytics",
            title="Senior Data Engineer",
            location="Bengaluru, Karnataka, India",
            external_url="https://in.indeed.com/viewjob?jk=acme101",
            source_job_id="ACME-IND-101",
            source=Job.Source.INDEED
        )
        self.assertIsNotNone(dup_indeed)
        self.assertEqual(dup_indeed.id, job.id)

        # Merge Indeed source
        JobDeduplicationService.register_or_merge_source(
            job=dup_indeed,
            source=Job.Source.INDEED,
            external_url="https://in.indeed.com/viewjob?jk=acme101",
            source_job_id="ACME-IND-101"
        )

        # Assert exactly ONE Job exists in DB
        total_acme_jobs = Job.objects.filter(company_name="Acme Analytics").count()
        self.assertEqual(total_acme_jobs, 1)

        # Assert all 3 sources are preserved in sources_list
        job.refresh_from_db()
        sources = job.sources_list
        self.assertIn("LinkedIn", sources)
        self.assertIn("Naukri", sources)
        self.assertIn("Indeed", sources)

    def test_hierarchy_levels(self):
        job = Job.objects.create(
            title="Data Platform Architect",
            company_name="BigData Corp",
            location="Hyderabad, India",
            source=Job.Source.NAUKRI,
            source_job_id="BD-999",
            external_url="https://naukri.com/jobs/bd-999",
            content_hash=generate_content_hash("BigData Corp", "Data Platform Architect", "Hyderabad, India")
        )

        # Level 1: exact source_job_id
        m1 = JobDeduplicationService.find_duplicate("Different", "Different", source_job_id="BD-999")
        self.assertEqual(m1, job)

        # Level 2: normalized URL
        m2 = JobDeduplicationService.find_duplicate("Different", "Different", external_url="https://naukri.com/jobs/bd-999?utm_source=email")
        self.assertEqual(m2, job)

        # Level 3: company + title + location
        m3 = JobDeduplicationService.find_duplicate("BigData Corp", "Data Platform Architect", location="Hyderabad")
        self.assertEqual(m3, job)

        # Level 4: Content hash
        m4 = JobDeduplicationService.find_duplicate("Different", "Different", content_hash=job.content_hash)
        self.assertEqual(m4, job)
