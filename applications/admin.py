from django.contrib import admin
from .models import Application, AutomationLog

class AutomationLogInline(admin.TabularInline):
    model = AutomationLog
    extra = 0
    readonly_fields = ('timestamp', 'level', 'action', 'message')
    can_delete = False

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'status', 'automation_status', 'applied_at', 'submitted_at', 'updated_at')
    list_filter = ('status', 'automation_status', 'created_at')
    search_fields = ('job__title', 'job__company', 'user__username', 'notes')
    inlines = [AutomationLogInline]

@admin.register(AutomationLog)
class AutomationLogAdmin(admin.ModelAdmin):
    list_display = ('application', 'timestamp', 'level', 'action', 'message')
    list_filter = ('level', 'timestamp')
    search_fields = ('application__job__title', 'action', 'message')

