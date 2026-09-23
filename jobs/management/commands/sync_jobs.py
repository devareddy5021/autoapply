"""
Management Command: python manage.py sync_jobs (Milestone 3).

CLI command to trigger job aggregation across all or specific connectors.
"""

from django.core.management.base import BaseCommand
from jobs.services.collector import JobCollector
from jobs.sources import get_source_connector, get_all_connectors


class Command(BaseCommand):
    help = "Aggregates fresh data jobs from configured sources for India & Remote."

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, help='Specific source to synchronize (e.g. linkedin, naukri)')

    def handle(self, *args, **options):
        source_name = options.get('source')
        collector = JobCollector()

        if source_name:
            connector = get_source_connector(source_name)
            if not connector:
                self.stderr.write(self.style.ERROR(f"Unknown connector '{source_name}'. Registered: linkedin, naukri, indeed, foundit, internshala, wellfound, cutshort, instahyre"))
                return
            self.stdout.write(f"Collecting jobs from {connector.display_name}...")
            log = collector.collect_from_source(connector)
            self.stdout.write(self.style.SUCCESS(f"Finished {connector.display_name}: Found {log.jobs_found}, New {log.jobs_new}, Merged {log.jobs_duplicate}"))
        else:
            self.stdout.write("Collecting jobs from all registered sources...")
            logs = collector.collect_all_sources()
            for log in logs:
                self.stdout.write(f"  {log.source}: Found {log.jobs_found}, New {log.jobs_new}, Merged {log.jobs_duplicate} ({log.status})")
            self.stdout.write(self.style.SUCCESS("All sources aggregated successfully."))
