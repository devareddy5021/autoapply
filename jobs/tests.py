from django.test import TestCase
from jobs.models import Job, normalize_job_url

class JobModelTests(TestCase):
    def test_normalize_job_url(self):
        raw_url = "https://www.linkedin.com/jobs/view/123456/?refId=abc&trackingId=xyz"
        expected = "https://www.linkedin.com/jobs/view/123456"
        self.assertEqual(normalize_job_url(raw_url), expected)

    def test_find_duplicate_by_company_title(self):
        job = Job.objects.create(
            title="Senior Python Engineer",
            company="Tech Corp",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            description="Build great software",
            external_job_id="TC-101",
            external_url="https://techcorp.com/jobs/101?ref=feed"
        )

        # Duplicate by external_job_id
        dup1 = Job.find_duplicate(
            company="Other",
            title="Other",
            external_job_id="TC-101"
        )
        self.assertEqual(dup1, job)

        # Duplicate by URL (with different query parameters)
        dup2 = Job.find_duplicate(
            company="Other",
            title="Other",
            external_url="https://techcorp.com/jobs/101?ref=email"
        )
        self.assertEqual(dup2, job)

        # Duplicate by company + title
        dup3 = Job.find_duplicate(
            company="Tech Corp",
            title="Senior Python Engineer",
            location="Remote"
        )
        self.assertEqual(dup3, job)

        # Non duplicate
        non_dup = Job.find_duplicate(
            company="Different Corp",
            title="Frontend Engineer"
        )
        self.assertIsNone(non_dup)


class JobViewsTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='jobuser', password='Password123!')
        self.client.login(username='jobuser', password='Password123!')
        self.job = Job.objects.create(
            title="Senior Django Developer",
            company="Global Tech",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            skills="Python, Django, PostgreSQL",
            description="Developing scalable web applications."
        )

    def test_job_list_view(self):
        from django.urls import reverse
        response = self.client.get(reverse('jobs:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Django Developer")
        self.assertContains(response, "Global Tech")

    def test_job_detail_view(self):
        from django.urls import reverse
        response = self.client.get(reverse('jobs:detail', args=[self.job.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Django Developer")
        self.assertContains(response, "Transparent Match")
        self.assertContains(response, "Full Job Description")

    def test_job_create_view(self):
        from django.urls import reverse
        response = self.client.post(reverse('jobs:create'), {
            'title': 'React Engineer',
            'company': 'Frontend Labs',
            'location': 'Remote',
            'work_mode': 'REMOTE',
            'description': 'React UI engineering',
            'experience_required_years': '2.0',
            'skills': 'React, TypeScript, CSS',
            'source': 'MANUAL',
            'status': 'ACTIVE',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Job.objects.filter(title='React Engineer').exists())

