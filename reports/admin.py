from django.contrib import admin
from .models import (
    MachineUsageReport,
    RiceMillSchedulingReport,
    RiceSale,
    RiceSaleSetting,
    UserActivityReport,
)


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


@admin.register(RiceSaleSetting)
class RiceSaleSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'current_price_per_sack', 'is_available_for_sale', 'updated_by', 'updated_at')
    list_filter = ('is_available_for_sale',)


@admin.register(RiceSale)
class RiceSaleAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'buyer', 'sacks', 'price_per_sack', 'total_amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reference_number', 'buyer__username', 'buyer__email', 'buyer__first_name', 'buyer__last_name')




