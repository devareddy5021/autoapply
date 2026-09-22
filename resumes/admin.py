from django.contrib import admin
from .models import Resume

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'version', 'is_default', 'file_size_kb', 'upload_date')
    list_filter = ('is_default', 'upload_date')
    search_fields = ('name', 'extracted_text', 'user__username')
