"""
Django REST Framework Serializers for JobAutoApply (Milestone 3).
"""

from rest_framework import serializers
from jobs.models import Job, UserJob, JobSyncLog


class JobSerializer(serializers.ModelSerializer):
    sources = serializers.ReadOnlyField(source='sources_list')
    primary_url = serializers.ReadOnlyField()

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'company_name',
            'location',
            'work_mode',
            'employment_type',
            'job_category',
            'category_confidence',
            'country',
            'is_india',
            'is_remote',
            'location_type',
            'matched_keywords',
            'description',
            'requirements',
            'skills',
            'salary_text',
            'experience_min',
            'experience_max',
            'source',
            'source_job_id',
            'external_url',
            'primary_url',
            'sources',
            'posted_at',
            'first_seen_at',
            'last_seen_at',
            'is_active',
        ]


class JobSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSyncLog
        fields = '__all__'
