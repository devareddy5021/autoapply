from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list_view, name='list'),
    path('add/', views.job_create_view, name='create'),
    path('<int:pk>/', views.job_detail_view, name='detail'),
    path('<int:pk>/edit/', views.job_update_view, name='update'),
    path('<int:pk>/delete/', views.job_delete_view, name='delete'),
]
