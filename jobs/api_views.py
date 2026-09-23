"""
Django REST Framework API Views for JobAutoApply (Milestone 3).

Provides endpoints applying India/Remote and Data domain filtering:
- GET  /api/jobs/
- GET  /api/jobs/<id>/
- GET  /api/jobs/saved/
- GET  /api/jobs/sources/
- POST /api/jobs/sync/
- POST /api/jobs/<id>/save/
- POST /api/jobs/<id>/ignore/
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from jobs.models import Job, UserJob, JobSyncLog
from jobs.serializers import JobSerializer, JobSyncLogSerializer
from jobs.sources import get_all_connectors
from jobs.tasks import trigger_sync_in_background
from jobs import services


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobListAPIView(APIView):
    """
    GET /api/jobs/
    Lists active data jobs strictly in India or Remote.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Job.objects.filter(is_active=True).exclude(job_category='OTHER').filter(
            Q(is_india=True) | Q(is_remote=True)
        )

        query = request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(
                Q(title__icontains=query) |
                Q(company_name__icontains=query) |
                Q(skills__icontains=query) |
                Q(location__icontains=query)
            )

        category = request.GET.get('category', '').strip()
        if category:
            qs = qs.filter(job_category=category)

        work_mode = request.GET.get('work_mode', '').strip()
        if work_mode:
            qs = qs.filter(work_mode=work_mode)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = JobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class JobDetailAPIView(APIView):
    """
    GET /api/jobs/<id>/
    Returns single job details and candidate match breakdown.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(
            Job.objects.filter(is_active=True).exclude(job_category='OTHER').filter(
                Q(is_india=True) | Q(is_remote=True)
            ),
            pk=pk
        )
        user_job = services.calculate_and_sync_user_job_match(request.user, job)
        serializer = JobSerializer(job)
        data = serializer.data
        data['match'] = {
            'score': user_job.match_score,
            'reasons': user_job.match_reasons,
            'missing_skills': user_job.missing_skills,
        }
        data['is_saved'] = user_job.is_saved
        data['is_ignored'] = user_job.is_ignored
        return Response(data)


class SavedJobsListAPIView(APIView):
    """
    GET /api/jobs/saved/
    Returns user's saved data jobs.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_saved_ids = UserJob.objects.filter(
            user=request.user,
            is_saved=True,
            job__is_active=True
        ).values_list('job_id', flat=True)

        qs = Job.objects.filter(id__in=user_saved_ids).exclude(job_category='OTHER').filter(
            Q(is_india=True) | Q(is_remote=True)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = JobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class SourcesListAPIView(APIView):
    """
    GET /api/jobs/sources/
    Returns statuses and metrics for all configured connectors.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        connectors = get_all_connectors()
        data = []
        for conn in connectors:
            last_log = JobSyncLog.objects.filter(source=conn.display_name).first()
            data.append({
                'name': conn.name,
                'display_name': conn.display_name,
                'is_available': conn.is_available,
                'is_restricted': conn.is_scraping_restricted,
                'restriction_reason': conn.restriction_reason,
                'last_sync': last_log.started_at if last_log else None,
                'last_status': last_log.status if last_log else 'Never',
                'jobs_found': last_log.jobs_found if last_log else 0,
            })
        return Response({'sources': data})


class TriggerSyncAPIView(APIView):
    """
    POST /api/jobs/sync/
    Triggers source synchronization in background worker/thread.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        source = request.data.get('source', '').strip()
        trigger_sync_in_background(source_name=source or None, user_id=request.user.pk)
        return Response({
            'success': True,
            'message': f"Collection dispatched for {source or 'all sources'} in background."
        }, status=status.HTTP_202_ACCEPTED)


class ToggleSaveJobAPIView(APIView):
    """
    POST /api/jobs/<id>/save/
    Toggles saved state for job.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_job, is_saved = services.toggle_save_job(request.user, pk)
        if not user_job:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True,
            'job_id': pk,
            'is_saved': is_saved
        })


class ToggleIgnoreJobAPIView(APIView):
    """
    POST /api/jobs/<id>/ignore/
    Toggles ignored state for job.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_job, is_ignored = services.toggle_ignore_job(request.user, pk)
        if not user_job:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True,
            'job_id': pk,
            'is_ignored': is_ignored
        })
