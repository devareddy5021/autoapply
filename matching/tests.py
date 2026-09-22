from django.test import TestCase
from django.contrib.auth.models import User
from jobs.models import Job
from accounts.models import Profile
from matching.services import calculate_match_score, MATCH_WEIGHTS

class MatchingEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='matchingtestuser', password='Password123!')
        self.profile = self.user.profile
        self.profile.preferred_job_titles = "Python Developer, Backend Engineer"
        self.profile.skills = "Python, Django, PostgreSQL, Docker, Redis"
        self.profile.preferred_locations = "Remote"
        self.profile.work_preference = Profile.WorkPreference.REMOTE
        self.profile.years_of_experience = 4.0
        self.profile.preferred_salary_min = 120000
        self.profile.save()

    def test_high_match_score(self):
        job = Job.objects.create(
            title="Senior Python Developer",
            company_name="Acme SaaS",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            skills="Python, Django, PostgreSQL, Docker",
            experience_min=3.0,
            salary_min=130000,
            salary_max=160000,
            description="Seeking an experienced Python developer with Django knowledge."
        )

        match = calculate_match_score(job, self.profile)
        self.assertGreaterEqual(match['score'], 80)
        self.assertEqual(match['breakdown']['title']['score'], 30)
        self.assertEqual(match['breakdown']['location']['score'], 10)
        self.assertEqual(match['breakdown']['work_mode']['score'], 10)
        self.assertEqual(match['breakdown']['experience']['score'], 10)
        self.assertIn("Python", match['matched_skills'])
        self.assertTrue(len(match['reasons']) > 0)

    def test_low_match_score(self):
        job = Job.objects.create(
            title="Graphic Designer & Animator",
            company_name="Studio Art",
            location="Tokyo, Japan",
            work_mode=Job.WorkMode.ONSITE,
            skills="Photoshop, Illustrator, After Effects, 3D Max",
            experience_min=8.0,
            salary_min=40000,
            salary_max=50000,
            description="Design brochures and 3D visual assets."
        )

        match = calculate_match_score(job, self.profile)
        self.assertLess(match['score'], 45)
        self.assertIn("Photoshop", match['missing_skills'])
