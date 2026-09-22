from django import forms
from .models import Resume

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['name', 'file', 'version', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Backend Lead Resume 2026'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf'
            }),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1.0'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file:
            if not uploaded_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF resumes are supported.")
            if uploaded_file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("File size must be under 10MB.")
        return uploaded_file
