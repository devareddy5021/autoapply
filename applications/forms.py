from django import forms
from .models import Application
from resumes.models import Resume

class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status', 'resume', 'application_url', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'resume': forms.Select(attrs={'class': 'form-select'}),
            'application_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add notes, recruiter contacts, follow-up dates...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['resume'].queryset = Resume.objects.filter(user=user)
