from django.test import TestCase
from django.contrib.auth.models import User
from jobs.models import Job
from resumes.models import Resume
from accounts.models import Profile
from matching.services import calculate_match_score

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
            company="Acme SaaS",
            location="Remote",
            work_mode=Job.WorkMode.REMOTE,
            skills="Python, Django, PostgreSQL, Docker",
            experience_required_years=3.0,
            salary_min=130000,
            salary_max=160000,
            description="Seeking an experienced Python developer with Django knowledge."
        )

        match = calculate_match_score(job, self.profile)
        self.assertGreaterEqual(match['total_score'], 80)
        self.assertEqual(match['role']['score'], 25)
        self.assertEqual(match['location']['score'], 15)
        self.assertEqual(match['work_mode']['score'], 10)
        self.assertEqual(match['experience']['score'], 10)
        self.assertEqual(match['salary']['score'], 10)
        self.assertIn("Python", match['skills']['matched'])

    def test_low_match_score(self):
        job = Job.objects.create(
            title="Graphic Designer & Animator",
            company="Studio Art",
            location="Tokyo, Japan",
            work_mode=Job.WorkMode.ON_SITE,
            skills="Photoshop, Illustrator, After Effects, 3D Max",
            experience_required_years=8.0,
            salary_min=40000,
            salary_max=50000,
            description="Design brochures and 3D visual assets."
        )

        match = calculate_match_score(job, self.profile)
        self.assertLess(match['total_score'], 45)
