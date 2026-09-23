from django.urls import path
from . import views, api_views

app_name = 'jobs'

urlpatterns = [
    # Web UI Dashboard & Pages
    path('', views.job_list_view, name='list'),
    path('sources/', views.sources_dashboard_view, name='sources_status'),
    path('sync/', views.sync_source_view, name='sync_source'),
    path('create/', views.job_create_view, name='create'),
    path('saved/', views.saved_jobs_view, name='saved'),
    path('<int:pk>/', views.job_detail_view, name='detail'),
    path('<int:pk>/save/', views.job_save_toggle_view, name='save'),
    path('<int:pk>/ignore/', views.job_ignore_toggle_view, name='ignore'),
    path('<int:pk>/delete/', views.job_delete_view, name='delete'),

    # REST API Endpoints (Section 29)
    path('api/jobs/', api_views.JobListAPIView.as_view(), name='api_jobs_list'),
    path('api/jobs/<int:pk>/', api_views.JobDetailAPIView.as_view(), name='api_jobs_detail'),
    path('api/jobs/saved/', api_views.SavedJobsListAPIView.as_view(), name='api_jobs_saved'),
    path('api/jobs/sources/', api_views.SourcesListAPIView.as_view(), name='api_jobs_sources'),
    path('api/jobs/sync/', api_views.TriggerSyncAPIView.as_view(), name='api_jobs_sync'),
    path('api/jobs/<int:pk>/save/', api_views.ToggleSaveJobAPIView.as_view(), name='api_jobs_save'),
    path('api/jobs/<int:pk>/ignore/', api_views.ToggleIgnoreJobAPIView.as_view(), name='api_jobs_ignore'),
]
