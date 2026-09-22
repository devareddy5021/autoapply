from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from jobs.models import Job

class DashboardViewsTests(TestCase):
    def test_unauthenticated_dashboard_landing(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JobAutoApply")
        self.assertContains(response, "Land your dream role")

    def test_authenticated_dashboard_view(self):
        user = User.objects.create_user(username='dashuser', password='Password123!')
        self.client.login(username='dashuser', password='Password123!')

        Job.objects.create(
            title="Python Developer",
            company="Acme Corp",
            location="Remote",
            description="Django backend engineering role."
        )

        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, "Total Discovered")
        self.assertContains(response, "Recommended For You")
