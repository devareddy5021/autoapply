"""
Tests for Django REST Framework API Endpoints (Milestone 3, Section 29).
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from jobs.models import Job, UserJob, JobCategory


class JobAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='api_dev', password='Password123!')
        self.client.force_authenticate(user=self.user)

        # 1. India Data Job (should be returned)
        self.data_job = Job.objects.create(
            title="Data Platform Engineer",
            company_name="Alpha Analytics",
            location="Bengaluru, India",
            work_mode=Job.WorkMode.HYBRID,
            job_category=JobCategory.DATA_ENGINEERING,
            is_india=True,
            is_remote=False,
            is_active=True
        )

        # 2. Remote Data Job (should be returned)
        self.remote_job = Job.objects.create(
            title="Senior Data Analyst",
            company_name="Remote Insights",
            location="Remote India",
            work_mode=Job.WorkMode.REMOTE,
            job_category=JobCategory.DATA_ANALYTICS,
            is_india=True,
            is_remote=True,
            is_active=True
        )

        # 3. Unrelated Software Job (should be excluded)
        self.frontend_job = Job.objects.create(
            title="Senior React Developer",
            company_name="Web Tech",
            location="Bengaluru, India",
            work_mode=Job.WorkMode.ONSITE,
            job_category=JobCategory.OTHER,
            is_india=True,
            is_remote=False,
            is_active=True
        )

    def test_api_jobs_list_filters_data_and_geography(self):
        url = reverse('jobs_api:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        results = response.data.get('results', [])
        job_ids = [j['id'] for j in results]

        # Verify India and Remote Data jobs are present
        self.assertIn(self.data_job.id, job_ids)
        self.assertIn(self.remote_job.id, job_ids)

        # Verify OTHER / Frontend role is strictly excluded
        self.assertNotIn(self.frontend_job.id, job_ids)

    def test_api_job_detail(self):
        url = reverse('jobs_api:detail', args=[self.data_job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.data_job.id)
        self.assertIn('match', response.data)
        self.assertIn('sources', response.data)

    def test_api_sources_list(self):
        url = reverse('jobs_api:sources')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sources', response.data)
        sources_list = [s['name'] for s in response.data['sources']]
        self.assertIn('linkedin', sources_list)
        self.assertIn('naukri', sources_list)
        self.assertIn('indeed', sources_list)

    def test_api_toggle_save_and_saved_list(self):
        save_url = reverse('jobs_api:save', args=[self.data_job.id])
        resp_save = self.client.post(save_url)
        self.assertEqual(resp_save.status_code, 200)
        self.assertTrue(resp_save.data['is_saved'])

        # Check saved list
        saved_url = reverse('jobs_api:saved')
        resp_saved_list = self.client.get(saved_url)
        self.assertEqual(resp_saved_list.status_code, 200)
        saved_ids = [j['id'] for j in resp_saved_list.data.get('results', [])]
        self.assertIn(self.data_job.id, saved_ids)

    def test_api_trigger_sync(self):
        sync_url = reverse('jobs_api:sync')
        resp = self.client.post(sync_url, {'source': 'linkedin'})
        self.assertEqual(resp.status_code, 202)
        self.assertTrue(resp.data['success'])
