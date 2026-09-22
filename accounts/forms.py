from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter strong password'}),
        label='Password'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}),
        label='Confirm Password'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'full_name',
            'phone',
            'current_location',
            'preferred_locations',
            'work_authorization',
            'years_of_experience',
            'notice_period_days',
            'preferred_job_titles',
            'skills',
            'education',
            'certifications',
            'preferred_salary_min',
            'preferred_salary_max',
            'salary_currency',
            'work_preference',
            'linkedin_url',
            'github_url',
            'portfolio_url',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'}),
            'current_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. San Francisco, CA or Bengaluru, India'}),
            'preferred_locations': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Remote, New York, Seattle'}),
            'work_authorization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. US Citizen / Green Card / Authorized to work'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'notice_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'preferred_job_titles': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Backend Engineer, Python Architect'}),
            'skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g. Python, Django, PostgreSQL, Docker, Kubernetes, AWS, Celery, Redis, REST APIs'}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g. B.S. in Computer Science, Stanford University (2020)'}),
            'certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g. AWS Solutions Architect Professional'}),
            'preferred_salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '120000'}),
            'preferred_salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '160000'}),
            'salary_currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD'}),
            'work_preference': forms.Select(attrs={'class': 'form-select'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/username'}),
            'github_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://yourportfolio.dev'}),
        }
