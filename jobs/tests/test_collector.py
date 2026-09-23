"""
Tests for JobCollector and Source Failure Isolation (Milestone 3, Section 31).
"""

from django.test import TestCase
from django.contrib.auth.models import User
from jobs.models import Job, JobSyncLog
from jobs.sources.base import BaseJobSource
from jobs.services.collector import JobCollector
from matching.services import calculate_match_score


class DummyFailingSource(BaseJobSource):
    name = "failing_mock"
    display_name = "Failing Mock Source"

    def search(self, query, location=None, remote=False):
        raise ConnectionResetError("Remote server closed connection unexpectedly (Mock Failure)")

    def normalize_job(self, raw_job):
        return {}


class DummyWorkingSource(BaseJobSource):
    name = "working_mock"
    display_name = "Working Mock Source"

    def search(self, query, location=None, remote=False):
        return [
            {
                'title': 'Junior Data Engineer',
                'company': 'Mock Analytics Ltd',
                'location': 'Bengaluru, India',
                'work_mode': 'REMOTE',
                'url': 'https://mockanalytics.example.com/jobs/101',
                'id': 'MOCK-101',
            }
        ]

    def normalize_job(self, raw_job):
        return {
            'title': raw_job['title'],
            'company': raw_job['company'],
            'location': raw_job['location'],
            'work_mode': 'REMOTE',
            'description': 'Python, SQL, and Apache Spark engineering.',
            'skills': ['Python', 'SQL', 'Spark'],
            'salary': '₹12,00,000 / year',
            'experience': '0 - 2 yrs',
            'source': Job.Source.OTHER,
            'source_job_id': raw_job['id'],
            'url': raw_job['url'],
        }


class CollectorAndSourceFailureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dataengineer', password='Password123!')
        self.profile = self.user.profile
        self.profile.preferred_job_titles = "Data Engineer, Junior Data Engineer"
        self.profile.skills = "Python, SQL, Spark, Databricks"
        self.profile.preferred_locations = "Bengaluru, Remote"
        self.profile.work_preference = "REMOTE"
        self.profile.save()

    def test_source_failure_isolation(self):
        """
        Section 27 & 31: Verify that one failing source does NOT stop the entire sync,
        and other sources are collected and saved successfully.
        """
        failing_source = DummyFailingSource()
        working_source = DummyWorkingSource()

        collector = JobCollector(user=self.user)

        # 1. Collect from failing source
        fail_log = collector.collect_from_source(failing_source)
        self.assertEqual(fail_log.status, JobSyncLog.Status.FAILED)
        self.assertIn("Mock Failure", fail_log.error_message)

        # 2. Collect from working source (should succeed despite prior failure)
        work_log = collector.collect_from_source(working_source)
        self.assertEqual(work_log.status, JobSyncLog.Status.SUCCESS)
        self.assertGreaterEqual(work_log.jobs_new, 1)

        # 3. Verify job created in DB
        created_job = Job.objects.filter(company_name='Mock Analytics Ltd').first()
        self.assertIsNotNone(created_job)
        self.assertEqual(created_job.title, 'Junior Data Engineer')
        self.assertTrue(created_job.is_india)
        self.assertTrue(created_job.is_remote)

    def test_profile_to_job_matching(self):
        """
        Section 16 & 31: Test profile-to-job match scoring.
        """
        job = Job.objects.create(
            title="Junior Data Engineer",
            company_name="Apex Data",
            location="Bengaluru, India",
            work_mode=Job.WorkMode.REMOTE,
            skills="Python, SQL, Spark, Databricks, Airflow",
            description="Build Spark pipelines.",
            experience_min=1.0,
            experience_max=3.0,
        )

        match_info = calculate_match_score(job, self.profile)
        # Should be a high score because of title, skills, location, work mode match
        self.assertGreaterEqual(match_info['score'], 70)
        self.assertIn("Python matches target skills", match_info['reasons'])
        self.assertIn("SQL matches target skills", match_info['reasons'])
        self.assertIn("Airflow", match_info['missing_skills'])
