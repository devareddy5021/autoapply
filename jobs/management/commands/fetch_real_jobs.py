from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jobs.services import fetch_and_sync_real_jobs


class Command(BaseCommand):
    help = "Fetches and synchronizes real, live job postings from public APIs (Remotive and Arbeitnow) with experience parsing and deduplication."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help="Maximum number of jobs to fetch per external source (default: 50)"
        )
        parser.add_argument(
            '--user',
            type=str,
            default='',
            help="Optional username to calculate match scores for"
        )

    def handle(self, *args, **options):
        limit = options['limit']
        username = options['user']
        user = None
        if username:
            user = User.objects.filter(username=username).first()

        self.stdout.write(self.style.NOTICE(f"Fetching real live jobs from Remotive & Arbeitnow (limit: {limit})..."))
        result = fetch_and_sync_real_jobs(user=user, limit=limit)

        self.stdout.write(self.style.SUCCESS(
            f"Done! Scanned {result['total_scanned']} postings. "
            f"Created: {result['created']} new real jobs. "
            f"Updated: {result['updated']} existing jobs."
        ))
        if result['errors']:
            self.stdout.write(self.style.WARNING(f"Warnings/Errors encountered: {', '.join(result['errors'])}"))
