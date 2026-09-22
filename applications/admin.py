from django.contrib import admin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'status', 'automation_status', 'applied_at', 'updated_at')
    list_filter = ('status', 'automation_status', 'created_at')
    search_fields = ('job__title', 'job__company', 'user__username', 'notes')
