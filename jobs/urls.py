from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list_view, name='list'),
    path('create/', views.job_create_view, name='create'),
    path('saved/', views.saved_jobs_view, name='saved'),
    path('sync-real-jobs/', views.fetch_real_jobs_view, name='fetch_real_jobs'),
    path('<int:pk>/', views.job_detail_view, name='detail'),
    path('<int:pk>/save/', views.job_save_toggle_view, name='save'),
    path('<int:pk>/ignore/', views.job_ignore_toggle_view, name='ignore'),
    path('<int:pk>/delete/', views.job_delete_view, name='delete'),
]

