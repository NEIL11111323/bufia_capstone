from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('user-notifications/', views.user_notifications, name='user_notifications'),
    path('all/', views.all_notifications, name='all_notifications'),
    path('sent/', views.sent_notifications, name='sent_notifications'),
    path('machine-alerts/', views.machine_alerts, name='machine_alerts'),
    path('rice-mill-scheduling-alerts/', views.rice_mill_scheduling_alerts, name='rice_mill_scheduling_alerts'),
    path('send/', views.send_notification, name='send_notification'),
    path('api/user-autocomplete/', views.user_autocomplete, name='user_autocomplete'),
    path('redirect/<int:notification_id>/', views.notification_redirect, name='notification_redirect'),
    path('api/mark-admin-read/', views.mark_admin_notifications_read, name='mark_admin_notifications_read'),
    path('detail/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
] 