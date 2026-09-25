"""
Tests for Smart Job Extractor and Duplicate Detection Service.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from jobs.models import Job
from jobs.services.job_extractor import (
    clean_html_to_markdown_or_text,
    format_plain_text,
    split_job_sections,
    detect_employment_type,
    detect_work_mode,
    check_job_duplicate,
    extract_job_from_text,
)


class JobExtractorUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')

        # Create a sample existing job for duplicate testing
        self.existing_job = Job.objects.create(
            title="Senior AI Data Engineer",
            company_name="Flipkart",
            location="Bengaluru, India",
            work_mode=Job.WorkMode.HYBRID,
            employment_type=Job.EmploymentType.FULL_TIME,
            description="Existing job in Bengaluru",
            external_url="https://www.flipkart.com/careers/data-engineer-101",
            source=Job.Source.LINKEDIN
        )

    def test_clean_html_to_markdown_preserves_bullets_and_paragraphs(self):
        html_input = """
        <p><strong>About Us:</strong></p>
        <p>We are a leading fintech enterprise.</p>
        <h3>Responsibilities:</h3>
        <ul>
            <li>Design and deploy PySpark pipelines.</li>
            <li>Optimize Databricks workloads.</li>
        </ul>
        <h3>Requirements:</h3>
        <ul>
            <li>3+ years with Python and SQL.</li>
            <li>Experience with AWS and Kafka.</li>
        </ul>
        """
        cleaned = clean_html_to_markdown_or_text(html_input)
        self.assertIn("About Us:", cleaned)
        self.assertIn("• Design and deploy PySpark pipelines.", cleaned)
        self.assertIn("• Optimize Databricks workloads.", cleaned)
        self.assertNotIn("<ul>", cleaned)
        self.assertNotIn("<li>", cleaned)
        self.assertNotIn("<p>", cleaned)

    def test_split_job_sections(self):
        text = """About Us:
Zepto is a fast-growing tech platform.

Key Responsibilities:
• Build distributed data pipelines using Kafka and Spark.
• Ensure data quality across platforms.

Requirements & Qualifications:
• 4+ years of data engineering experience.
• Strong knowledge of Python, SQL, and AWS.
"""
        overview, resp, req = split_job_sections(text)
        self.assertIn("Zepto is a fast-growing tech platform.", overview)
        self.assertIn("• Build distributed data pipelines using Kafka and Spark.", resp)
        self.assertIn("• 4+ years of data engineering experience.", req)

    def test_detect_employment_type_no_false_positive_internal(self):
        # Must NOT classify as INTERNSHIP when 'internal' is present
        emp_type = detect_employment_type(
            "Senior Data Engineer",
            "You will work closely with internal stakeholders and maintain internal databases."
        )
        self.assertEqual(emp_type, Job.EmploymentType.FULL_TIME)

        # Title specifies intern
        emp_intern = detect_employment_type("Data Engineering Intern", "6-month opportunity.")
        self.assertEqual(emp_intern, Job.EmploymentType.INTERNSHIP)

        # Title specifies contract
        emp_contract = detect_employment_type("Snowflake Architect (Contract)", "C2C / 6 months.")
        self.assertEqual(emp_contract, Job.EmploymentType.CONTRACT)

        # Title specifies trainee
        emp_trainee = detect_employment_type("Graduate Trainee Engineer", "Freshers welcome.")
        self.assertEqual(emp_trainee, Job.EmploymentType.TRAINEE)

    def test_detect_work_mode(self):
        wm_remote = detect_work_mode("Data Engineer (Remote)", "Work from anywhere in India", "Remote")
        self.assertEqual(wm_remote, Job.WorkMode.REMOTE)

        wm_hybrid = detect_work_mode("Data Architect", "Hybrid model: 2 days office, 3 days home", "Bengaluru")
        self.assertEqual(wm_hybrid, Job.WorkMode.HYBRID)

        wm_onsite = detect_work_mode("Data Platform Engineer", "Office based role in Bengaluru campus", "Bengaluru, India")
        self.assertEqual(wm_onsite, Job.WorkMode.ONSITE)

    def test_check_job_duplicate_positive_and_negative(self):
        # Should detect existing job
        dup = check_job_duplicate(
            company_name="Flipkart",
            title="Senior AI Data Engineer",
            location="Bengaluru, India"
        )
        self.assertTrue(dup['is_duplicate'])
        self.assertEqual(dup['job_id'], self.existing_job.id)

        # Should not detect non-existing job
        no_dup = check_job_duplicate(
            company_name="Totally Unique Company 12345",
            title="Unique Role 9876",
            location="Remote"
        )
        self.assertFalse(no_dup['is_duplicate'])
        self.assertIsNone(no_dup['job_id'])

    def test_extract_job_from_text(self):
        raw_jd = """Job Title: AI Data Engineer
Company: Acme AI Labs
Location: Hyderabad (Hybrid)
Salary: 18 - 25 LPA
Employment Type: Full Time

About Us:
Acme AI Labs pioneers foundation models.

Responsibilities:
• Architect real-time vector pipelines.
• Scale feature store on Databricks.

Requirements:
• 3+ years experience with Python and SQL.
• Deep understanding of MLOps and Spark.
"""
        res = extract_job_from_text(raw_jd)
        self.assertTrue(res['success'])
        data = res['data']
        self.assertEqual(data['title'], "AI Data Engineer")
        self.assertEqual(data['company_name'], "Acme AI Labs")
        self.assertEqual(data['work_mode'], Job.WorkMode.HYBRID)
        self.assertEqual(data['employment_type'], Job.EmploymentType.FULL_TIME)
        self.assertIn("Acme AI Labs", data['description'])
        self.assertIn("• Architect real-time vector pipelines.", data['responsibilities'])
        self.assertIn("• 3+ years experience with Python and SQL.", data['requirements'])
        self.assertIn("Python", data['skills'])
        self.assertIn("SQL", data['skills'])
        self.assertIn("Spark", data['skills'])
        self.assertFalse(data['is_duplicate'])

    def test_job_check_duplicate_view_endpoint(self):
        # Check duplicate via AJAX view
        url = reverse('jobs:check_duplicate')
        response = self.client.post(
            url,
            data=json.dumps({
                'company_name': 'Flipkart',
                'title': 'Senior AI Data Engineer',
                'location': 'Bengaluru'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertTrue(json_data['is_duplicate'])
        self.assertEqual(json_data['duplicate']['job_id'], self.existing_job.id)

    def test_job_extract_view_endpoint_with_duplicate(self):
        # Extract view should include duplicate info in response
        url = reverse('jobs:extract')
        raw_jd = """Job Title: Senior AI Data Engineer
Company: Flipkart
Location: Bengaluru
"""
        response = self.client.post(
            url,
            data=json.dumps({
                'mode': 'text',
                'text': raw_jd
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        data = json_data['data']
        self.assertTrue(data['is_duplicate'])
        self.assertEqual(data['duplicate']['job_id'], self.existing_job.id)

    def test_user_provided_droisys_jd_text(self):
        # Test exact real-world JD provided by the user
        jd_text = """About the job
About CompanyDroisys is an innovation technology company focused on helping companies accelerate their digital initiatives from strategy and planning through execution. We leverage deep technical expertise, Agile methodologies, and data-driven intelligence to modernize systems of engagement and simplify human/tech interaction.
Amazing things happen when we work in environments where everyone feels a true sense of belonging and when candidates have the requisite skills and opportunities to succeed. At Droisys, we invest in our talent and support career growth, and we are always on the lookout for amazing talent who can contribute to our growth by delivering top results for our clients. Join us to challenge yourself and accomplish work that matters.
Position: Data Analyst No# Of positions : 10Remote , India or local to Noida, Bangalore
Job Responsibilities:
Collect, clean, and organize data from various sources to ensure accuracy and reliability.
Analyze datasets to identify trends, patterns, and actionable insights that support business decisions.
Create and maintain reports, dashboards, and visualizations using tools such as Excel, Power BI, or Tableau.
Assist in preparing data summaries and presentations for stakeholders and management.
Perform data validation and quality checks to ensure data integrity.
Support business teams by providing timely and accurate analytical reports.
Work with databases and write basic SQL queries to retrieve, update, and manage data.
Collaborate with cross-functional teams to understand business requirements and reporting needs.
Monitor key performance indicators (KPIs) and generate periodic performance reports.
Help automate recurring reports and data collection processes where applicable.
Document data definitions, methodologies, and analysis procedures.
Stay updated on industry trends, data analytics tools, and best practices.

Required Skills
Bachelor's degree in Computer Science, Statistics, Mathematics, Business Analytics, or a related field.
Basic knowledge of SQL and database concepts.
Proficiency in Microsoft Excel, including formulas, pivot tables, and data analysis techniques.
Familiarity with Power BI, Tableau, or other data visualization tools.
Understanding of statistics and data analysis concepts.
Strong analytical and problem-solving skills.
Good communication and presentation abilities.
Ability to work independently and collaboratively in a team environment.
Preferred Qualifications
Internship or academic project experience in data analysis.
Basic knowledge of Python or R for data analysis.
Familiarity with data warehousing and ETL concepts.
Exposure to cloud platforms such as Azure, AWS, or Google Cloud is a plus.

#Hiring #DataAnalyst #FresherJobs #EntryLevelJobs #Analytics #PowerBI #SQL #Excel #DataVisualization #CareerOpportunity

Droisys is an equal opportunity employer. We do not discriminate based on race, religion, color, national origin, gender, gender expression, sexual orientation, age, marital status, veteran status, disability status or any other characteristic protected by law. Droisys believes in diversity, inclusion, and belonging, and we are committed to fostering a diverse work environment."""

        res = extract_job_from_text(jd_text)
        self.assertTrue(res['success'])
        data = res['data']

        self.assertEqual(data['title'], "Data Analyst")
        self.assertEqual(data['company_name'], "Droisys")
        self.assertEqual(data['work_mode'], Job.WorkMode.HYBRID)
        self.assertEqual(data['employment_type'], Job.EmploymentType.FULL_TIME)

        # Verify clean section extraction and auto-bulletization
        self.assertIn("About CompanyDroisys is an innovation technology company", data['description'])
        self.assertIn("• Collect, clean, and organize data from various sources", data['responsibilities'])
        self.assertIn("• Analyze datasets to identify trends, patterns", data['responsibilities'])
        self.assertIn("• Bachelor's degree in Computer Science", data['requirements'])
        self.assertIn("• Basic knowledge of SQL and database concepts.", data['requirements'])
        self.assertIn("SQL", data['skills'])
        self.assertIn("Power BI", data['skills'])
        self.assertIn("Tableau", data['skills'])

    def test_linkedin_html_prefers_container_over_teaser_description(self):
        # Tests that LinkedIn teaser snippet in og:description is rejected in favor of full markup
        from jobs.services.job_extractor import extract_job_from_html
        linkedin_html = """
        <html>
        <head>
          <title>Droisys hiring Data Analyst in Noida, Uttar Pradesh, India | LinkedIn</title>
          <meta property="og:title" content="Droisys hiring Data Analyst in Noida, Uttar Pradesh, India | LinkedIn">
          <meta property="og:description" content="Posted 5:52:21 AM. About CompanyDroisys is an innovation technology company focused on helping companies accelerate…See this and similar jobs on LinkedIn.">
        </head>
        <body>
          <div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5">
            <p>About Company Droisys is an innovation technology company focused on helping companies accelerate their digital initiatives.</p>
            <h3>Job Responsibilities:</h3>
            <ul>
              <li>Collect, clean, and organize data from various sources.</li>
              <li>Build dashboards in Power BI and Excel.</li>
            </ul>
            <h3>Required Skills</h3>
            <ul>
              <li>Strong SQL and analytical skills.</li>
              <li>Experience with Tableau.</li>
            </ul>
          </div>
        </body>
        </html>
        """
        parsed = extract_job_from_html(linkedin_html, source_url='https://www.linkedin.com/jobs/view/12345')

        self.assertEqual(parsed['company_name'], "Droisys")
        self.assertEqual(parsed['title'], "Data Analyst")
        self.assertIn("Noida", parsed['location'])
        # Must NOT be the teaser
        self.assertNotIn("See this and similar jobs on LinkedIn", parsed['description'])
        self.assertNotIn("Posted 5:52:21 AM", parsed['description'])
        self.assertIn("Droisys is an innovation technology company", parsed['description'])
        self.assertIn("• Collect, clean, and organize data", parsed['responsibilities'])
        self.assertIn("• Strong SQL and analytical skills.", parsed['requirements'])
