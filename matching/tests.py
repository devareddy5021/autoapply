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

    def test_full_resume_matching(self):
        from resumes.models import Resume
        resume_text = """
        John Doe - Data Engineer
        Summary: Experienced Data Engineer specializing in PySpark, Apache Airflow, Snowflake, and AWS.
        Built real-time streaming pipelines with Kafka and distributed ETL with Spark.
        Education: B.Tech in Computer Science.
        Projects:
        - Enterprise Data Lakehouse on AWS and Snowflake.
        - Orchestrated DAG workflows using Airflow.
        """
        resume = Resume.objects.create(
            user=self.user,
            name="John_Doe_Data_Engineer_Resume.pdf",
            extracted_text=resume_text,
            is_default=True
        )

        job = Job.objects.create(
            title="Data Engineer",
            company_name="Flipkart",
            location="Bengaluru",
            work_mode=Job.WorkMode.ONSITE,
            skills="PySpark, Airflow, Snowflake, AWS, Python, Kafka",
            experience_min=2.0,
            description="Looking for a Data Engineer with hands-on PySpark, Apache Airflow, and Snowflake experience to design data lakehouse pipelines on AWS."
        )

        match = calculate_match_score(job, self.profile, default_resume=resume)
        self.assertIn('resume_analysis', match)
        resume_analysis = match['resume_analysis']
        self.assertTrue(resume_analysis['has_resume'])
        self.assertGreaterEqual(resume_analysis['score'], 60)
        self.assertIn("Pyspark", resume_analysis['matched_keywords'])
        self.assertIn("Airflow", resume_analysis['matched_keywords'])
        self.assertIn("Snowflake", resume_analysis['matched_keywords'])
        self.assertIn("breakdown", match)
        self.assertIn("resume", match['breakdown'])

