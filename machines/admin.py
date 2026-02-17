from django.contrib import admin
from .models import Machine, MachineImage, Rental, Maintenance, PriceHistory, RiceMillAppointment
from .forms import AdminRentalForm

class MachineImageInline(admin.TabularInline):
    model = MachineImage
    extra = 1

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('name', 'machine_type', 'status', 'current_price', 'created_at')
    list_filter = ('machine_type', 'status')
    search_fields = ('name', 'description')
    inlines = [MachineImageInline]

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('machine', 'get_renter_name', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('status', 'start_date')
    search_fields = ('machine__name', 'user__username', 'user__email', 'purpose')
    date_hierarchy = 'created_at'
    form = AdminRentalForm
    actions = ['approve_rentals', 'reject_rentals', 'complete_rentals']
    
    def get_renter_name(self, obj):
        if obj.user.username == 'system' and obj.purpose and 'Renter:' in obj.purpose:
            renter_line = obj.purpose.split('\n')[0]
            if renter_line.startswith('Renter:'):
                return renter_line[8:].strip()
        return obj.user.get_full_name() or obj.user.username
    
    get_renter_name.short_description = 'Renter'
    get_renter_name.admin_order_field = 'user__last_name'
    
    def approve_rentals(self, request, queryset):
        """Bulk approve selected rentals"""
        count = 0
        for rental in queryset.filter(status='pending'):
            rental.status = 'approved'
            rental.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} rental(s) approved successfully. Notifications sent to users.')
    approve_rentals.short_description = 'Approve selected rentals'
    
    def reject_rentals(self, request, queryset):
        """Bulk reject selected rentals"""
        count = 0
        for rental in queryset.filter(status='pending'):
            rental.status = 'rejected'
            rental.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} rental(s) rejected. Notifications sent to users.')
    reject_rentals.short_description = 'Reject selected rentals'
    
    def complete_rentals(self, request, queryset):
        """Bulk complete selected rentals"""
        count = 0
        for rental in queryset.filter(status='approved'):
            rental.status = 'completed'
            rental.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} rental(s) marked as completed. Notifications sent to users.')
    complete_rentals.short_description = 'Mark selected rentals as completed'

@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ('machine', 'start_date', 'end_date', 'status', 'created_by')
    list_filter = ('status', 'start_date')
    search_fields = ('machine__name', 'description')
    date_hierarchy = 'start_date'

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('machine', 'price', 'start_date', 'end_date', 'created_by')
    list_filter = ('start_date',)
    search_fields = ('machine__name',)
    date_hierarchy = 'start_date'

@admin.register(RiceMillAppointment)
class RiceMillAppointmentAdmin(admin.ModelAdmin):
    list_display = ('machine', 'user', 'appointment_date', 'time_slot', 'rice_quantity', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'time_slot')
    search_fields = ('machine__name', 'user__username', 'user__email', 'reference_number')
    date_hierarchy = 'appointment_date'
    readonly_fields = ('created_at', 'updated_at', 'reference_number')
    actions = ['approve_appointments', 'reject_appointments', 'complete_appointments']
    
    def approve_appointments(self, request, queryset):
        """Bulk approve selected appointments"""
        count = 0
        for appointment in queryset.filter(status='pending'):
            appointment.status = 'approved'
            appointment.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} appointment(s) approved successfully. Notifications sent to users.')
    approve_appointments.short_description = 'Approve selected appointments'
    
    def reject_appointments(self, request, queryset):
        """Bulk reject selected appointments"""
        count = 0
        for appointment in queryset.filter(status='pending'):
            appointment.status = 'rejected'
            appointment.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} appointment(s) rejected. Notifications sent to users.')
    reject_appointments.short_description = 'Reject selected appointments'
    
    def complete_appointments(self, request, queryset):
        """Bulk complete selected appointments"""
        count = 0
        for appointment in queryset.filter(status='approved'):
            appointment.status = 'completed'
            appointment.save()  # This triggers the signal
            count += 1
        self.message_user(request, f'{count} appointment(s) marked as completed. Notifications sent to users.')
    complete_appointments.short_description = 'Mark selected appointments as completed'
