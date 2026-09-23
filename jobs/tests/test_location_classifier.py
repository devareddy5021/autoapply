"""
Tests for India and Remote Location Classification (Milestone 3, Section 31).
"""

from django.test import TestCase
from jobs.models import LocationType
from jobs.services.location_classifier import classify_location


class LocationClassifierTests(TestCase):
    def test_indian_cities_accepted(self):
        # Bengaluru
        res_blr = classify_location("Bengaluru, India")
        self.assertTrue(res_blr['is_accepted'])
        self.assertTrue(res_blr['is_india'])
        self.assertEqual(res_blr['location_type'], LocationType.INDIA_CITY)

        # Hyderabad
        res_hyd = classify_location("Hyderabad, Telangana")
        self.assertTrue(res_hyd['is_accepted'])
        self.assertTrue(res_hyd['is_india'])
        self.assertEqual(res_hyd['location_type'], LocationType.INDIA_CITY)

        # Pune
        res_pune = classify_location("Pune, Maharashtra, India")
        self.assertTrue(res_pune['is_accepted'])
        self.assertTrue(res_pune['is_india'])

        # Multi-City India
        res_multi = classify_location("Bengaluru / Hyderabad / Mumbai")
        self.assertTrue(res_multi['is_accepted'])
        self.assertEqual(res_multi['location_type'], LocationType.INDIA_MULTI_CITY)

    def test_remote_india_accepted(self):
        test_cases = [
            "Remote India",
            "India remote",
            "Work from home in India",
            "Remote — India",
            "Remote, India",
        ]
        for loc in test_cases:
            res = classify_location(loc, work_mode='REMOTE')
            self.assertTrue(res['is_accepted'], f"Failed for {loc}")
            self.assertTrue(res['is_remote'], f"Failed for {loc}")
            self.assertTrue(res['is_india'], f"Failed for {loc}")
            self.assertEqual(res['location_type'], LocationType.REMOTE_INDIA, f"Failed for {loc}")

    def test_remote_worldwide_accepted(self):
        test_cases = [
            "Remote worldwide",
            "Remote - Worldwide",
            "Work from anywhere",
            "Global Remote",
            "Remote",
        ]
        for loc in test_cases:
            res = classify_location(loc, work_mode='REMOTE')
            self.assertTrue(res['is_accepted'], f"Failed for {loc}")
            self.assertTrue(res['is_remote'], f"Failed for {loc}")
            self.assertIn(res['location_type'], [LocationType.REMOTE_GLOBAL, LocationType.REMOTE_INDIA])

    def test_foreign_only_rejected(self):
        # USA only
        res_usa = classify_location("Remote — USA only", work_mode='REMOTE')
        self.assertFalse(res_usa['is_accepted'])
        self.assertEqual(res_usa['location_type'], LocationType.OUTSIDE_INDIA)

        # UK only
        res_uk = classify_location("Remote (UK Only)", work_mode='REMOTE')
        self.assertFalse(res_uk['is_accepted'])
        self.assertEqual(res_uk['location_type'], LocationType.OUTSIDE_INDIA)

        # Canada only
        res_ca = classify_location("Remote — Canada only", work_mode='REMOTE')
        self.assertFalse(res_ca['is_accepted'])
        self.assertEqual(res_ca['location_type'], LocationType.OUTSIDE_INDIA)

        # Europe only
        res_eu = classify_location("Remote - Europe only", work_mode='REMOTE')
        self.assertFalse(res_eu['is_accepted'])
        self.assertEqual(res_eu['location_type'], LocationType.OUTSIDE_INDIA)

        # US Citizens only in description
        res_us_cit = classify_location("Remote", work_mode='REMOTE', description="Requires US citizenship and US timezone")
        self.assertFalse(res_us_cit['is_accepted'])

    def test_foreign_onsite_rejected(self):
        res_london = classify_location("London, United Kingdom")
        self.assertFalse(res_london['is_accepted'])

        res_sf = classify_location("San Francisco, CA")
        self.assertFalse(res_sf['is_accepted'])
