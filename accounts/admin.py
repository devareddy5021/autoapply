from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'current_location', 'years_of_experience', 'work_preference')
    search_fields = ('user__username', 'full_name', 'skills', 'preferred_job_titles')
    list_filter = ('work_preference', 'notice_period_days')
