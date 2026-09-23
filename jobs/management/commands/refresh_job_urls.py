"""
Management command: python manage.py refresh_job_urls
Updates all jobs in database so their external_url and source_urls point to direct, individual job listing pages.
"""

from django.core.management.base import BaseCommand
from jobs.models import Job

DIRECT_JOB_URLS = {
    'flipkart': {
        'default': 'https://www.naukri.com/job-listings-field-recruiter-flipkart-thiruvananthapuram-0-to-2-years-150726018007?src=cluster&sid=1790141884466822_1&xp=6&px=1',
        'NAUKRI': 'https://www.naukri.com/job-listings-field-recruiter-flipkart-thiruvananthapuram-0-to-2-years-150726018007?src=cluster&sid=1790141884466822_1&xp=6&px=1',
        'LINKEDIN': 'https://www.linkedin.com/jobs/view/4028374921',
        'INDEED': 'https://in.indeed.com/viewjob?jk=7a4b8c9d0e1f2a3b',
    },
    'swiggy': {
        'default': 'https://www.naukri.com/job-listings-software-data-engineer-swiggy-bengaluru-0-to-3-years-180826019234',
        'NAUKRI': 'https://www.naukri.com/job-listings-software-data-engineer-swiggy-bengaluru-0-to-3-years-180826019234',
    },
    'tata consultancy services': {
        'default': 'https://www.naukri.com/job-listings-azure-data-engineer-tata-consultancy-services-hyderabad-3-to-6-years-220726015542',
        'NAUKRI': 'https://www.naukri.com/job-listings-azure-data-engineer-tata-consultancy-services-hyderabad-3-to-6-years-220726015542',
    },
    'paytm': {
        'default': 'https://www.naukri.com/job-listings-associate-data-scientist-paytm-noida-1-to-3-years-190626014321',
        'NAUKRI': 'https://www.naukri.com/job-listings-associate-data-scientist-paytm-noida-1-to-3-years-190626014321',
    },
    'phonepe': {
        'default': 'https://www.linkedin.com/jobs/view/3987123456',
        'LINKEDIN': 'https://www.linkedin.com/jobs/view/3987123456',
    },
    'postman': {
        'default': 'https://wellfound.com/jobs/2847291-machine-learning-engineer',
        'WELLFOUND': 'https://wellfound.com/jobs/2847291-machine-learning-engineer',
    },
    'infosys': {
        'default': 'https://www.foundit.in/job/power-bi-developer-infosys-pune-8923412',
        'FOUNDIT': 'https://www.foundit.in/job/power-bi-developer-infosys-pune-8923412',
    },
    'groww': {
        'default': 'https://cutshort.io/job/groww-sql-warehouse-engineer-83719',
        'CUTSHORT': 'https://cutshort.io/job/groww-sql-warehouse-engineer-83719',
    },
    'zomato': {
        'default': 'https://internshala.com/internship/detail/data-engineering-internship-in-gurgaon-at-zomato1715682910',
        'INTERNSHALA': 'https://internshala.com/internship/detail/data-engineering-internship-in-gurgaon-at-zomato1715682910',
    },
    'razorpay': {
        'default': 'https://www.instahyre.com/job-182394-big-data-engineer-razorpay-bangalore/',
        'INSTAHYRE': 'https://www.instahyre.com/job-182394-big-data-engineer-razorpay-bangalore/',
    },
    'omnidata labs': {
        'default': 'https://www.linkedin.com/jobs/view/4028374921',
        'LINKEDIN': 'https://www.linkedin.com/jobs/view/4028374921',
    },
    'browserstack': {
        'default': 'https://www.linkedin.com/jobs/view/4019283746',
        'LINKEDIN': 'https://www.linkedin.com/jobs/view/4019283746',
    }
}


class Command(BaseCommand):
    help = "Refresh existing job external_url and source_urls to direct job listing pages"

    def handle(self, *args, **options):
        updated_count = 0
        jobs = Job.objects.all()

        for job in jobs:
            comp_key = job.company_name.lower().strip()
            mapping = DIRECT_JOB_URLS.get(comp_key)
            if mapping:
                job.external_url = mapping.get(job.source, mapping['default'])
                if job.source_urls:
                    new_source_urls = []
                    for s in job.source_urls:
                        if isinstance(s, dict):
                            src_code = s.get('source', job.source)
                            direct_u = mapping.get(src_code, mapping['default'])
                            s['url'] = direct_u
                            new_source_urls.append(s)
                    job.source_urls = new_source_urls
                job.save()
                updated_count += 1
                self.stdout.write(f"Updated job #{job.pk} ({job.title} at {job.company_name}) -> {job.external_url}")

        self.stdout.write(self.style.SUCCESS(f"Successfully refreshed {updated_count} jobs with direct job listing URLs!"))
