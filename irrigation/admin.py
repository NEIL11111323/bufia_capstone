from django.contrib import admin
from .models import WaterIrrigationRequest, IrrigationRequestHistory


@admin.register(WaterIrrigationRequest)
class WaterIrrigationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'farmer', 'sector', 'requested_date', 'duration_hours', 'status', 'request_date'
    )
    list_filter = (
        'status', 'requested_date', 'sector'
    )
    search_fields = (
        'farmer__username', 'farmer__first_name', 'farmer__last_name', 'purpose', 'crop_type', 'canal_number', 'block_number'
    )
    date_hierarchy = 'request_date'
    autocomplete_fields = ('farmer', 'membership', 'sector', 'reviewed_by')
    readonly_fields = ('request_date', 'status_date')
    actions = ['approve_requests', 'reject_requests', 'complete_requests']
    
    def approve_requests(self, request, queryset):
        """Bulk approve selected irrigation requests"""
        count = 0
        for irrigation_request in queryset.filter(status='pending'):
            irrigation_request.status = 'approved'
            irrigation_request.reviewed_by = request.user
            irrigation_request.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} irrigation request(s) approved successfully. Notifications sent to farmers.')
    approve_requests.short_description = 'Approve selected irrigation requests'
    
    def reject_requests(self, request, queryset):
        """Bulk reject selected irrigation requests"""
        count = 0
        for irrigation_request in queryset.filter(status='pending'):
            irrigation_request.status = 'rejected'
            irrigation_request.reviewed_by = request.user
            irrigation_request.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} irrigation request(s) rejected. Notifications sent to farmers.')
    reject_requests.short_description = 'Reject selected irrigation requests'
    
    def complete_requests(self, request, queryset):
        """Bulk complete selected irrigation requests"""
        count = 0
        for irrigation_request in queryset.filter(status='approved'):
            irrigation_request.status = 'completed'
            irrigation_request.reviewed_by = request.user
            irrigation_request.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} irrigation request(s) marked as completed. Notifications sent to farmers.')
    complete_requests.short_description = 'Mark selected irrigation requests as completed'


@admin.register(IrrigationRequestHistory)
class IrrigationRequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'status', 'changed_by', 'changed_date')
    list_filter = ('status', 'changed_date')
    search_fields = (
        'request__farmer__username', 'request__farmer__first_name', 'request__farmer__last_name', 'notes'
    )
    date_hierarchy = 'changed_date'
