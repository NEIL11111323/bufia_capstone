from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('user-activity/', views.user_activity_report, name='user_activity_report'),
    path('machine-usage/', views.machine_usage_report, name='machine_usage_report'),
    path('rice-mill-scheduling/', views.rice_mill_scheduling_report, name='rice_mill_scheduling_report'),
] 