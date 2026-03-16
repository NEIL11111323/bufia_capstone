from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, MembershipApplication, Sector
import datetime

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_verified', 'membership_form_submitted', 'role', 'is_operator_display')
    list_filter = ('is_verified', 'membership_form_submitted', 'role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    actions = ['make_operator', 'remove_operator']
    
    def is_operator_display(self, obj):
        return obj.is_staff and not obj.is_superuser
    is_operator_display.short_description = 'Is Operator'
    is_operator_display.boolean = True
    
    def make_operator(self, request, queryset):
        """Convert selected users to operators"""
        count = 0
        for user in queryset:
            if not user.is_superuser:
                user.is_staff = True
                user.role = 'operator'
                user.save()
                count += 1
        self.message_user(request, f"{count} user(s) converted to operators.")
    make_operator.short_description = "Convert to Operator"
    
    def remove_operator(self, request, queryset):
        """Remove operator status from selected users"""
        count = 0
        for user in queryset:
            if not user.is_superuser:
                user.is_staff = False
                if user.role == 'operator':
                    user.role = 'member'
                user.save()
                count += 1
        self.message_user(request, f"{count} user(s) removed from operator role.")
    remove_operator.short_description = "Remove Operator Status"
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'address')}),
        ('Membership', {'fields': ('is_verified', 'membership_form_submitted', 'membership_form_date', 
                                   'membership_approved_date', 'membership_rejected_reason')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_verified', 'membership_form_submitted'),
        }),
    )


class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'submission_date', 'is_current', 'is_approved', 'is_rejected', 'assigned_sector')
    list_filter = ('submission_date', 'is_current', 'is_approved', 'is_rejected', 'gender', 'civil_status', 'ownership_type', 'assigned_sector')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'barangay', 'city', 'province', 'bufia_farm_location')
    date_hierarchy = 'submission_date'
    
    fieldsets = (
        ('Application Status', {
            'fields': ('user', 'submission_date', 'is_current', 'is_approved', 'is_rejected', 'reviewed_by', 'review_date', 'rejection_reason')
        }),
        ('Personal Information', {
            'fields': ('middle_name', 'gender', 'birth_date', 'civil_status', 'education')
        }),
        ('Address Information', {
            'fields': ('sitio', 'barangay', 'city', 'province')
        }),
        ('Farm Information', {
            'fields': ('ownership_type', 'land_owner', 'farm_manager', 'farm_location', 'bufia_farm_location', 'farm_size')
        }),
        ('Sector Information', {
            'fields': ('sector', 'assigned_sector')
        }),
    )
    
    readonly_fields = ('submission_date',)
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        # Mark selected applications as approved
        for application in queryset:
            application.is_approved = True
            application.is_rejected = False
            application.reviewed_by = request.user
            application.review_date = datetime.date.today()
            application.save()
            
            # Update user verification status
            user = application.user
            user.is_verified = True
            user.membership_approved_date = datetime.date.today()
            user.membership_rejected_reason = ''
            user.save()
        
        self.message_user(request, f"{queryset.count()} application(s) have been approved.")
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        # Mark selected applications as rejected
        for application in queryset:
            application.is_approved = False
            application.is_rejected = True
            application.reviewed_by = request.user
            application.review_date = datetime.date.today()
            application.save()
            
            # Update user verification status
            user = application.user
            user.is_verified = False
            if application.rejection_reason:
                user.membership_rejected_reason = application.rejection_reason
            user.save()
        
        self.message_user(request, f"{queryset.count()} application(s) have been rejected.")
    reject_applications.short_description = "Reject selected applications"


class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_member_count', 'created_at')
    search_fields = ('name', 'description')
    
    def get_member_count(self, obj):
        return obj.members.count()
    get_member_count.short_description = 'Members'


admin.site.register(Sector, SectorAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(MembershipApplication, MembershipApplicationAdmin)
