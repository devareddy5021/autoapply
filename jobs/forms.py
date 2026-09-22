from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title',
            'company',
            'location',
            'work_mode',
            'description',
            'salary_min',
            'salary_max',
            'salary_currency',
            'salary_text',
            'experience_required_years',
            'skills',
            'source',
            'external_url',
            'external_job_id',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, Country or Remote'}),
            'work_mode': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Paste complete job description'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min salary'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max salary'}),
            'salary_currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD'}),
            'salary_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '$120,000 - $150,000 / yr'}),
            'experience_required_years': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, PostgreSQL, Docker'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://job-site.com/view/12345'}),
            'external_job_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Internal or source job ID'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
