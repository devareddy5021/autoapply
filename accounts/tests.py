from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import Profile

class AccountsModelTests(TestCase):
    def test_profile_auto_created_on_user_creation(self):
        user = User.objects.create_user(
            username='johndoe',
            email='john@example.com',
            password='Password123!'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.user, user)

    def test_profile_helpers(self):
        user = User.objects.create_user(
            username='janedoe',
            first_name='Jane',
            last_name='Doe',
            email='jane@example.com',
            password='Password123!'
        )
        profile = user.profile
        profile.skills = 'Python, Django, PostgreSQL, Docker'
        profile.preferred_job_titles = 'Backend Engineer, Python Architect'
        profile.preferred_locations = 'Remote, New York'
        profile.save()

        self.assertEqual(profile.display_name, 'Jane Doe')
        self.assertEqual(len(profile.skills_list), 4)
        self.assertIn('Python', profile.skills_list)
        self.assertEqual(len(profile.preferred_job_titles_list), 2)
        self.assertIn('Backend Engineer', profile.preferred_job_titles_list)
        self.assertEqual(len(profile.preferred_locations_list), 2)


class AccountViewsTests(TestCase):
    def test_user_registration_view(self):
        from django.urls import reverse
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newapplicant',
            'email': 'newapplicant@example.com',
            'first_name': 'New',
            'last_name': 'Applicant',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newapplicant').exists())

    def test_user_login_view(self):
        from django.urls import reverse
        User.objects.create_user(username='loginuser', password='Password123!')
        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'Password123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:index'))

