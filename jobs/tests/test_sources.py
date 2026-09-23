"""
Tests for Connector Registry and Sources Compliance (Milestone 3, Section 5 & 31).
"""

from django.test import TestCase
from jobs.sources import (
    get_all_connectors,
    get_source_connector,
    BaseJobSource,
    LinkedInJobSource,
    NaukriJobSource,
    IndeedJobSource,
    FounditJobSource,
    InternshalaJobSource,
    WellfoundJobSource,
    CutshortJobSource,
    InstahyreJobSource
)


class JobSourcesTests(TestCase):
    def test_registry_contains_all_sources(self):
        expected_sources = [
            'linkedin', 'naukri', 'indeed', 'foundit',
            'internshala', 'wellfound', 'cutshort', 'instahyre'
        ]
        connectors = get_all_connectors()
        connector_names = [c.name for c in connectors]

        for src in expected_sources:
            self.assertIn(src, connector_names, f"Connector {src} missing from registry")
            conn = get_source_connector(src)
            self.assertIsNotNone(conn)
            self.assertIsInstance(conn, BaseJobSource)

    def test_compliance_declarations(self):
        """
        Verify compliance flags and restriction reasons for sources with strict anti-bot/ToS terms.
        """
        naukri = get_source_connector('naukri')
        self.assertTrue(naukri.is_scraping_restricted)
        self.assertTrue(bool(naukri.restriction_reason))

        indeed = get_source_connector('indeed')
        self.assertTrue(indeed.is_scraping_restricted)
        self.assertTrue(bool(indeed.restriction_reason))

        cutshort = get_source_connector('cutshort')
        self.assertTrue(cutshort.is_scraping_restricted)

        instahyre = get_source_connector('instahyre')
        self.assertTrue(instahyre.is_scraping_restricted)

    def test_unified_schema_normalization(self):
        """
        Verify that all connectors normalize into the exact required schema (Section 6).
        """
        sample_raw = {
            'title': 'Cloud Data Engineer',
            'company': 'Tech Corp',
            'location': 'Bengaluru, India',
            'url': 'https://techcorp.example.com/jobs/99',
            'source_job_id': 'TC-99',
        }

        connectors = get_all_connectors()
        for conn in connectors:
            norm = conn.normalize_job(sample_raw)
            self.assertIn('title', norm)
            self.assertIn('company', norm)
            self.assertIn('location', norm)
            self.assertIn('work_mode', norm)
            self.assertIn('description', norm)
            self.assertIn('skills', norm)
            self.assertIn('salary', norm)
            self.assertIn('experience', norm)
            self.assertIn('source', norm)
            self.assertIn('source_job_id', norm)
            self.assertIn('url', norm)
            self.assertIn('posted_at', norm)
