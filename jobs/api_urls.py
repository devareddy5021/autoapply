from django.urls import path
from . import api_views

app_name = 'jobs_api'

urlpatterns = [
    path('', api_views.JobListAPIView.as_view(), name='list'),
    path('saved/', api_views.SavedJobsListAPIView.as_view(), name='saved'),
    path('sources/', api_views.SourcesListAPIView.as_view(), name='sources'),
    path('sync/', api_views.TriggerSyncAPIView.as_view(), name='sync'),
    path('<int:pk>/', api_views.JobDetailAPIView.as_view(), name='detail'),
    path('<int:pk>/save/', api_views.ToggleSaveJobAPIView.as_view(), name='save'),
    path('<int:pk>/ignore/', api_views.ToggleIgnoreJobAPIView.as_view(), name='ignore'),
]
