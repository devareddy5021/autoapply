"""
Tests for Data-Role Classification (Milestone 3, Section 31).
"""

from django.test import TestCase
from jobs.models import JobCategory
from jobs.services.job_classifier import classify_job


class JobClassifierTests(TestCase):
    def test_data_roles_accepted(self):
        # Data Engineer
        res_de = classify_job("Data Engineer", "Build Spark and ETL pipelines with Python.")
        self.assertTrue(res_de['is_accepted'])
        self.assertEqual(res_de['category'], JobCategory.DATA_ENGINEERING)

        # Junior Data Engineer
        res_jde = classify_job("Junior Data Engineer", "Python, SQL, Airflow.")
        self.assertTrue(res_jde['is_accepted'])
        self.assertEqual(res_jde['category'], JobCategory.DATA_ENGINEERING)

        # Data Analyst
        res_da = classify_job("Data Analyst", "Build Tableau dashboards and query SQL.")
        self.assertTrue(res_da['is_accepted'])
        self.assertEqual(res_da['category'], JobCategory.DATA_ANALYTICS)

        # Data Scientist
        res_ds = classify_job("Data Scientist", "Predictive modeling and statistical analysis.")
        self.assertTrue(res_ds['is_accepted'])
        self.assertEqual(res_ds['category'], JobCategory.DATA_SCIENCE)

        # Machine Learning Engineer
        res_ml = classify_job("Machine Learning Engineer", "Deploy PyTorch and LLM models.")
        self.assertTrue(res_ml['is_accepted'])
        self.assertEqual(res_ml['category'], JobCategory.MACHINE_LEARNING)

        # Power BI Developer
        res_bi = classify_job("Power BI Developer", "DAX, reporting, Power Query.")
        self.assertTrue(res_bi['is_accepted'])
        self.assertEqual(res_bi['category'], JobCategory.BI)

        # SQL Developer
        res_sql = classify_job("SQL Developer", "Stored procedures and PostgreSQL.")
        self.assertTrue(res_sql['is_accepted'])
        self.assertEqual(res_sql['category'], JobCategory.DATABASE)

        # Azure Data Engineer
        res_az = classify_job("Azure Data Engineer", "Azure Data Factory, Databricks.")
        self.assertTrue(res_az['is_accepted'])
        self.assertEqual(res_az['category'], JobCategory.DATA_ENGINEERING)

    def test_tech_and_software_roles_accepted(self):
        # Frontend Developer
        res_fe = classify_job("Frontend Developer", "Build React UI components. Work with API data.")
        self.assertTrue(res_fe['is_accepted'])
        self.assertEqual(res_fe['category'], JobCategory.SOFTWARE_ENGINEERING)

        # React Developer
        res_react = classify_job("Senior React Developer", "State management, Redux, fetching data from APIs.")
        self.assertTrue(res_react['is_accepted'])
        self.assertEqual(res_react['category'], JobCategory.SOFTWARE_ENGINEERING)

        # DevOps Engineer
        res_devops = classify_job("DevOps Engineer", "Manage Kubernetes, Docker, and CI/CD.")
        self.assertTrue(res_devops['is_accepted'])
        self.assertEqual(res_devops['category'], JobCategory.CLOUD_DEVOPS)

        # Software Engineer
        res_swe = classify_job(
            "Software Engineer",
            "Requirements: Python, SQL, REST APIs, PostgreSQL databases."
        )
        self.assertTrue(res_swe['is_accepted'])
        self.assertEqual(res_swe['category'], JobCategory.SOFTWARE_ENGINEERING)

    def test_unrelated_non_tech_jobs_rejected(self):
        # HR Recruiter
        res_hr = classify_job("HR Recruiter", "Talent acquisition, candidate sourcing, payroll.")
        self.assertFalse(res_hr['is_accepted'])
        self.assertEqual(res_hr['category'], JobCategory.OTHER)

        # Sales Representative
        res_sales = classify_job("Sales Executive", "B2B client acquisition, cold calling, quarterly sales quotas.")
        self.assertFalse(res_sales['is_accepted'])
        self.assertEqual(res_sales['category'], JobCategory.OTHER)

        # Accountant
        res_acc = classify_job("Senior Accountant", "Tax audits, ledger reconciliation, balance sheets.")
        self.assertFalse(res_acc['is_accepted'])
        self.assertEqual(res_acc['category'], JobCategory.OTHER)
