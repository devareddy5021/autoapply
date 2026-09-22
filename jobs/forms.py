from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title',
            'company_name',
            'location',
            'work_mode',
            'employment_type',
            'description',
            'requirements',
            'responsibilities',
            'salary_min',
            'salary_max',
            'salary_currency',
            'salary_text',
            'experience_min',
            'experience_max',
            'skills',
            'source',
            'source_job_id',
            'external_url',
            'is_active',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Data Engineer'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ABC Technologies'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bengaluru, India or Remote'}),
            'work_mode': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Paste complete job overview/description...'}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Key requirements, qualifications, education...'}),
            'responsibilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Key responsibilities and day-to-day duties...'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min salary'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max salary'}),
            'salary_currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD or INR'}),
            'salary_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ₹6–10 LPA or $120k-$150k'}),
            'experience_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': 'Min years'}),
            'experience_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': 'Max years'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, SQL, PySpark, Databricks, Azure'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'source_job_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional source job ID'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
