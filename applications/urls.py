from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.application_list_view, name='list'),
    path('track/<int:job_id>/', views.quick_track_job, name='quick_track'),
    path('prepare/<int:job_id>/', views.application_prepare_view, name='prepare'),
    path('<int:pk>/', views.application_detail_view, name='detail'),
    path('<int:pk>/review/', views.application_review_view, name='review'),
    path('<int:pk>/confirm-submit/', views.application_confirm_submit_view, name='confirm_submit'),
    path('<int:pk>/status/', views.application_status_api, name='status_api'),
    path('<int:pk>/delete/', views.application_delete_view, name='delete'),
]

