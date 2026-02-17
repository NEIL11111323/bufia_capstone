from django.contrib import admin
from .models import UserNotification, MachineAlert, RiceMillSchedulingAlert


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'is_read', 'timestamp')
    list_filter = ('is_read', 'notification_type', 'timestamp')
    search_fields = ('user__username', 'user__email', 'message')
    date_hierarchy = 'timestamp'


@admin.register(MachineAlert)
class MachineAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'machine_name', 'alert_type', 'is_resolved', 'timestamp')
    list_filter = ('is_resolved', 'alert_type', 'timestamp')
    search_fields = ('machine_name', 'message')
    date_hierarchy = 'timestamp'


@admin.register(RiceMillSchedulingAlert)
class RiceMillSchedulingAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'schedule_id', 'user', 'alert_type', 'is_resolved', 'timestamp')
    list_filter = ('is_resolved', 'alert_type', 'timestamp')
    search_fields = ('schedule_id', 'user__username', 'user__email', 'message')
    date_hierarchy = 'timestamp'
