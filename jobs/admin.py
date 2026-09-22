from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'work_mode', 'source', 'status', 'discovered_at')
    list_filter = ('work_mode', 'source', 'status', 'discovered_at')
    search_fields = ('title', 'company', 'location', 'skills', 'description')
