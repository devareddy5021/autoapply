from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError
from jobs.models import Job, UserJob, normalize_job_url
from jobs.services import JobDeduplicationService, toggle_save_job, toggle_ignore_job, create_manual_job
from jobs import selectors, services
from matching.services import calculate_match_score, MATCH_WEIGHTS

class JobModelTests(TestCase):
    def test_normalize_job_url(self):
        raw_url = "https://www.linkedin.com/jobs/view/123456/?refId=abc&trackingId=xyz"
        expected = "https://www.linkedin.com/jobs/view/123456"
        self.assertEqual(normalize_job_url(raw_url), expected)

    def test_job_model_fields_and_backward_compatibility(self):
        job = Job.objects.create(
            title="Senior Python Engineer",
            company_name="Tech Corp",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            employment_type=Job.EmploymentType.FULL_TIME,
            description="Build great software",
            requirements="Python 4+ yrs",
            responsibilities="Architect APIs",
            source_job_id="TC-101",
            salary_min=120000,
            salary_max=150000,
            experience_min=4.0,
            experience_max=7.0,
            skills="Python, Django, PostgreSQL",
        )
        self.assertEqual(job.company, "Tech Corp")
        self.assertEqual(job.external_job_id, "TC-101")
        self.assertEqual(job.experience_required_years, 4.0)
        self.assertTrue(job.is_active)
        self.assertEqual(job.status, "ACTIVE")
        self.assertEqual(len(job.skills_list), 3)
        self.assertEqual(job.formatted_experience, "4 - 7 yrs")

    def test_user_job_unique_constraint(self):
        user = User.objects.create_user(username='testuser', password='Password123!')
        job = Job.objects.create(
            title="Django Developer",
            company_name="Acme Inc",
            description="Backend work"
        )
        UserJob.objects.create(user=user, job=job, is_saved=True)

        with self.assertRaises(IntegrityError):
            UserJob.objects.create(user=user, job=job, is_saved=False)


class JobServicesAndSelectorsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='coder', password='Password123!')
        self.profile = self.user.profile
        self.profile.preferred_job_titles = "Python Developer, Backend Engineer"
        self.profile.skills = "Python, Django, PostgreSQL, Docker"
        self.profile.preferred_locations = "Bengaluru, Remote"
        self.profile.work_preference = "REMOTE"
        self.profile.years_of_experience = 4.0
        self.profile.save()

        self.job1 = Job.objects.create(
            title="Python Developer",
            company_name="Alpha Tech",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            employment_type=Job.EmploymentType.FULL_TIME,
            skills="Python, Django, Docker",
            experience_min=3.0,
            description="Build cloud backends",
            source=Job.Source.LINKEDIN,
            source_job_id="ALPHA-1",
            external_url="https://alphatech.com/jobs/1",
        )
        self.job2 = Job.objects.create(
            title="Data Analyst",
            company_name="Beta Insights",
            location="Bengaluru",
            work_mode=Job.WorkMode.HYBRID,
            employment_type=Job.EmploymentType.CONTRACT,
            skills="SQL, Tableau, Excel",
            experience_min=2.0,
            description="Analyze financial datasets",
            source=Job.Source.NAUKRI,
            source_job_id="BETA-2",
            external_url="https://betainsights.com/jobs/2",
        )

    def test_deduplication_service(self):
        # Match by source_job_id
        dup1 = JobDeduplicationService.find_duplicate(
            company_name="Other",
            title="Other",
            source_job_id="ALPHA-1"
        )
        self.assertEqual(dup1, self.job1)

        # Match by URL
        dup2 = JobDeduplicationService.find_duplicate(
            company_name="Other",
            title="Other",
            external_url="https://alphatech.com/jobs/1?ref=email"
        )
        self.assertEqual(dup2, self.job1)

        # Match by company + title
        dup3 = JobDeduplicationService.find_duplicate(
            company_name="Beta Insights",
            title="Data Analyst",
            location="Bengaluru"
        )
        self.assertEqual(dup3, self.job2)

        # Non-duplicate
        dup4 = JobDeduplicationService.find_duplicate(
            company_name="Gamma",
            title="Designer"
        )
        self.assertIsNone(dup4)

    def test_toggle_save_and_ignore_job(self):
        # Toggle Save
        uj, is_saved = toggle_save_job(self.user, self.job1.id)
        self.assertTrue(is_saved)
        self.assertTrue(uj.is_saved)

        uj, is_saved = toggle_save_job(self.user, self.job1.id)
        self.assertFalse(is_saved)
        self.assertFalse(uj.is_saved)

        # Toggle Ignore
        uj, is_ignored = toggle_ignore_job(self.user, self.job1.id)
        self.assertTrue(is_ignored)
        self.assertTrue(uj.is_ignored)

    def test_filter_and_search_jobs(self):
        # Search keyword
        results = selectors.filter_and_search_jobs(self.user, query="cloud")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['job'], self.job1)

        # Filter work mode
        remote_results = selectors.filter_and_search_jobs(self.user, work_mode=Job.WorkMode.REMOTE)
        self.assertEqual(len(remote_results), 1)
        self.assertEqual(remote_results[0]['job'], self.job1)

        # Ignored filter test
        toggle_ignore_job(self.user, self.job1.id)
        visible_results = selectors.filter_and_search_jobs(self.user, show_ignored=False)
        self.assertEqual(len(visible_results), 1)
        self.assertEqual(visible_results[0]['job'], self.job2)

        with_ignored_results = selectors.filter_and_search_jobs(self.user, show_ignored=True)
        self.assertEqual(len(with_ignored_results), 2)

    def test_dashboard_statistics(self):
        toggle_save_job(self.user, self.job1.id)
        stats = selectors.get_dashboard_statistics(self.user)
        self.assertEqual(stats['total_jobs'], 2)
        self.assertEqual(stats['saved_jobs'], 1)

    def test_saved_jobs_selector(self):
        toggle_save_job(self.user, self.job1.id)
        saved = selectors.get_saved_jobs_for_user(self.user)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['job'], self.job1)


class MatchingEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='matchuser', password='Password123!')
        self.profile = self.user.profile
        self.profile.preferred_job_titles = "Python Engineer"
        self.profile.skills = "Python, Django, PostgreSQL, Docker"
        self.profile.preferred_locations = "Bengaluru"
        self.profile.work_preference = "REMOTE"
        self.profile.years_of_experience = 4.0
        self.profile.save()

        self.job = Job.objects.create(
            title="Senior Python Engineer",
            company_name="Apex Tech",
            location="Bengaluru",
            work_mode=Job.WorkMode.REMOTE,
            skills="Python, Django, PostgreSQL, Docker, Kubernetes",
            experience_min=3.0,
            description="High scalability Django microservices"
        )

    def test_explainable_match_score(self):
        match = calculate_match_score(self.job, self.profile)
        self.assertGreaterEqual(match['score'], 80)
        self.assertIn("Kubernetes", match['missing_skills'])
        self.assertTrue(len(match['reasons']) >= 3)
        self.assertIn("title", match['breakdown'])
        self.assertEqual(match['breakdown']['title']['max'], MATCH_WEIGHTS['title'])


class JobViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='Password123!')
        self.client.login(username='viewuser', password='Password123!')
        self.job = Job.objects.create(
            title="Senior Django Developer",
            company_name="Global Tech",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            employment_type=Job.EmploymentType.FULL_TIME,
            skills="Python, Django, PostgreSQL",
            description="Developing scalable web applications."
        )

    def test_job_list_view(self):
        response = self.client.get(reverse('jobs:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Django Developer")
        self.assertContains(response, "Global Tech")
        self.assertContains(response, "Total Jobs")

    def test_job_detail_view(self):
        response = self.client.get(reverse('jobs:detail', args=[self.job.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Django Developer")
        self.assertContains(response, "Explainable Match")
        self.assertContains(response, "Prepare Application")

    def test_job_save_toggle_view(self):
        # Save job
        response = self.client.post(reverse('jobs:save', args=[self.job.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserJob.objects.filter(user=self.user, job=self.job, is_saved=True).exists())

        # Unsave job
        response = self.client.post(reverse('jobs:save', args=[self.job.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserJob.objects.filter(user=self.user, job=self.job, is_saved=True).exists())

    def test_job_ignore_toggle_view(self):
        response = self.client.post(reverse('jobs:ignore', args=[self.job.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserJob.objects.filter(user=self.user, job=self.job, is_ignored=True).exists())

    def test_saved_jobs_view(self):
        toggle_save_job(self.user, self.job.pk)
        response = self.client.get(reverse('jobs:saved'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saved Jobs")
        self.assertContains(response, "Senior Django Developer")

    def test_job_create_view(self):
        response = self.client.post(reverse('jobs:create'), {
            'title': 'React Engineer',
            'company_name': 'Frontend Labs',
            'location': 'Remote',
            'work_mode': 'REMOTE',
            'employment_type': 'FULL_TIME',
            'description': 'React UI engineering',
            'experience_min': '2.0',
            'skills': 'React, TypeScript, CSS',
            'source': 'MANUAL',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Job.objects.filter(title='React Engineer').exists())

    def test_experience_filtering(self):
        # Create jobs with specific experience requirements
        Job.objects.create(
            title="Junior Python Dev",
            company_name="JuniorCo",
            experience_min=1.0,
            experience_max=2.0,
            is_active=True
        )
        Job.objects.create(
            title="Principal Architect",
            company_name="BigCo",
            experience_min=10.0,
            is_active=True
        )

        # Filter by 0-2 years
        entry_jobs = selectors.filter_and_search_jobs(user=self.user, experience='0-2')
        titles_entry = [j['job'].title for j in entry_jobs]
        self.assertIn("Junior Python Dev", titles_entry)
        self.assertNotIn("Principal Architect", titles_entry)

        # Filter by 8+ years
        lead_jobs = selectors.filter_and_search_jobs(user=self.user, experience='8+')
        titles_lead = [j['job'].title for j in lead_jobs]
        self.assertIn("Principal Architect", titles_lead)
        self.assertNotIn("Junior Python Dev", titles_lead)

    def test_parse_experience_requirements_service(self):
        min_y, max_y = services.parse_experience_requirements(
            "Senior Backend Engineer",
            "Must have 4 to 6 years of experience in distributed systems."
        )
        self.assertEqual(min_y, 4.0)
        self.assertEqual(max_y, 6.0)

        min_y2, _ = services.parse_experience_requirements("Junior Associate", "Fresh graduates welcome.")
        self.assertEqual(min_y2, 1.0)

