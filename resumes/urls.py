from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('', views.resume_list_view, name='list'),
    path('upload/', views.resume_list_view, name='upload'),
    path('<int:pk>/', views.resume_detail_view, name='detail'),
    path('<int:pk>/set-default/', views.set_default_resume_view, name='set_default'),
    path('<int:pk>/delete/', views.delete_resume_view, name='delete'),
]
