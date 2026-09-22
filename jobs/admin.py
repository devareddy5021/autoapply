from django.contrib import admin
from .models import Job, UserJob

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'company_name',
        'location',
        'work_mode',
        'employment_type',
        'source',
        'is_active',
        'posted_at',
        'discovered_at'
    )
    list_filter = (
        'source',
        'work_mode',
        'employment_type',
        'is_active',
        'posted_at',
        'discovered_at'
    )
    search_fields = (
        'title',
        'company_name',
        'location',
        'skills',
        'source_job_id',
        'description'
    )
    date_hierarchy = 'discovered_at'
    ordering = ('-discovered_at',)


@admin.register(UserJob)
class UserJobAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'job',
        'is_saved',
        'is_ignored',
        'match_score',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'is_saved',
        'is_ignored',
        'match_score',
        'created_at'
    )
    search_fields = (
        'user__username',
        'user__email',
        'job__title',
        'job__company_name'
    )
    raw_id_fields = ('user', 'job')
