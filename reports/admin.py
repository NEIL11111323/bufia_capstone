from django.contrib import admin
from .models import UserActivityReport, MachineUsageReport, RiceMillSchedulingReport


@admin.register(UserActivityReport)
class UserActivityReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'activity_type', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'user__email', 'description')
    date_hierarchy = 'timestamp'


@admin.register(MachineUsageReport)
class MachineUsageReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'machine_name', 'usage_type', 'timestamp')
    list_filter = ('usage_type', 'timestamp')
    search_fields = ('machine_name', 'description')
    date_hierarchy = 'timestamp'


@admin.register(RiceMillSchedulingReport)
class RiceMillSchedulingReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'schedule_id', 'user', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'start_time')
    search_fields = ('schedule_id', 'user__username', 'user__email', 'description')
    date_hierarchy = 'start_time'




