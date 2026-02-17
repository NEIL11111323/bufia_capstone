from django.urls import path
from . import views

app_name = 'general_reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]
