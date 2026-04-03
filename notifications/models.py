from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

class UserNotification(models.Model):
    PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('important', 'Important'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ]
    
    CATEGORY_CHOICES = [
        ('rental', 'Rental'),
        ('operator', 'Operator'),
        ('payment', 'Payment'),
        ('maintenance', 'Maintenance'),
        ('system', 'System'),
        ('irrigation', 'Irrigation'),
        ('appointment', 'Appointment'),
        ('membership', 'Membership'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Enhanced fields
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    title = models.CharField(max_length=200, blank=True, help_text="Short notification title")
    
    # Fields for dynamic routing
    related_object_id = models.IntegerField(null=True, blank=True, help_text="ID of the related object (rental, appointment, etc.)")
    action_url = models.CharField(max_length=255, null=True, blank=True, help_text="Direct URL to navigate to")

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"

    def save(self, *args, **kwargs):
        if not self.category or self.category == 'system':
            self.category = self.infer_category()
        if not self.priority:
            self.priority = self.infer_priority()
        if not self.title or self._title_has_mojibake():
            self.title = self.build_display_title()
        super().save(*args, **kwargs)

    def infer_category(self):
        notification_type = (self.notification_type or '').lower()
        if 'rental' in notification_type:
            return 'rental'
        if 'operator' in notification_type:
            return 'operator'
        if 'payment' in notification_type or 'settlement' in notification_type:
            return 'payment'
        if 'maintenance' in notification_type or 'machine' in notification_type:
            return 'maintenance'
        if 'irrigation' in notification_type:
            return 'irrigation'
        if 'appointment' in notification_type or 'rice' in notification_type or 'dryer' in notification_type:
            return 'appointment'
        if 'membership' in notification_type:
            return 'membership'
        return 'system'

    def infer_priority(self):
        notification_type = (self.notification_type or '').lower()
        if any(token in notification_type for token in ['urgent', 'critical', 'breakdown']):
            return 'critical'
        if any(token in notification_type for token in ['new_request', 'submitted', 'approved', 'rejected']):
            return 'important'
        if any(token in notification_type for token in ['completed', 'payment', 'update', 'confirmed']):
            return 'normal'
        return 'low'

    def _title_has_mojibake(self):
        return bool(self.title and ('ðŸ' in self.title or 'â' in self.title))

    def _format_date(self, value, with_year=True):
        if not value:
            return ''
        if with_year:
            return value.strftime('%b %d, %Y')
        return value.strftime('%b %d')

    def _related_object(self):
        if hasattr(self, '_related_object_cache'):
            return self._related_object_cache

        obj = None
        if self.related_object_id:
            try:
                notification_type = (self.notification_type or '').lower()
                if 'dryer' in notification_type:
                    from machines.models import DryerRental
                    obj = DryerRental.objects.select_related('user', 'machine').filter(pk=self.related_object_id).first()
                elif 'appointment' in notification_type or 'rice' in notification_type:
                    from machines.models import RiceMillAppointment
                    obj = RiceMillAppointment.objects.select_related('user', 'machine').filter(pk=self.related_object_id).first()
                elif 'rental' in notification_type:
                    from machines.models import Rental
                    obj = Rental.objects.select_related('user', 'machine').filter(pk=self.related_object_id).first()
                elif 'irrigation' in notification_type:
                    from irrigation.models import WaterIrrigationRequest
                    obj = WaterIrrigationRequest.objects.select_related('farmer', 'sector').filter(pk=self.related_object_id).first()
            except Exception:
                obj = None

        self._related_object_cache = obj
        return obj

    def _actor_name(self):
        obj = self._related_object()
        if obj is None:
            return ''
        if hasattr(obj, 'user') and obj.user:
            return obj.user.get_full_name() or obj.user.username
        if hasattr(obj, 'farmer') and obj.farmer:
            return obj.farmer.get_full_name() or obj.farmer.username
        return ''

    def build_display_title(self):
        notification_type = (self.notification_type or '').lower()
        actor_name = self._actor_name()

        if notification_type == 'appointment_new_request':
            return f"Rice Mill Request{' • ' + actor_name if actor_name else ''}"
        if notification_type in ['appointment_submitted', 'appointment_approved', 'appointment_confirmed', 'appointment_payment_completed', 'appointment_rejected', 'appointment_completed', 'appointment_cancelled']:
            labels = {
                'appointment_submitted': 'Rice Mill Request Submitted',
                'appointment_approved': 'Rice Mill Request Approved',
                'appointment_confirmed': 'Rice Mill Weight Recorded',
                'appointment_payment_completed': 'Rice Mill Payment Confirmed',
                'appointment_rejected': 'Rice Mill Request Rejected',
                'appointment_completed': 'Rice Mill Request Completed',
                'appointment_cancelled': 'Rice Mill Request Cancelled',
            }
            return labels.get(notification_type, 'Rice Mill Update')
        if notification_type == 'dryer_new_request':
            return f"Dryer Booking{' • ' + actor_name if actor_name else ''}"
        if notification_type.startswith('dryer_'):
            return {
                'dryer_submitted': 'Dryer Booking Submitted',
                'dryer_approved': 'Dryer Booking Approved',
                'dryer_rejected': 'Dryer Booking Rejected',
                'dryer_completed': 'Dryer Booking Completed',
                'dryer_cancelled': 'Dryer Booking Cancelled',
                'dryer_confirmed': 'Dryer Booking Confirmed',
            }.get(notification_type, 'Dryer Service Update')
        if notification_type == 'rental_new_request':
            return f"Rental Request{' • ' + actor_name if actor_name else ''}"
        if notification_type.startswith('rental_'):
            return {
                'rental_submitted': 'Rental Request Submitted',
                'rental_approved': 'Rental Request Approved',
                'rental_rejected': 'Rental Request Rejected',
                'rental_completed': 'Rental Request Completed',
                'rental_cancelled': 'Rental Request Cancelled',
                'rental_payment_received': 'Rental Payment Received',
                'rental_payment_completed': 'Rental Payment Completed',
                'rental_update': 'Rental Update',
            }.get(notification_type, 'Rental Notification')
        if notification_type == 'irrigation_new_request':
            return f"Irrigation Request{' • ' + actor_name if actor_name else ''}"
        if notification_type.startswith('irrigation_'):
            return {
                'irrigation_submitted': 'Irrigation Request Submitted',
                'irrigation_approved': 'Irrigation Request Approved',
                'irrigation_rejected': 'Irrigation Request Rejected',
                'irrigation_completed': 'Irrigation Request Completed',
                'irrigation_cancelled': 'Irrigation Request Cancelled',
            }.get(notification_type, 'Irrigation Update')
        if notification_type.startswith('membership_'):
            return {
                'membership_approved': 'Membership Approved',
                'membership_rejected': 'Membership Rejected',
                'membership_required': 'Membership Required',
            }.get(notification_type, 'Membership Update')
        if self.title and not self._title_has_mojibake():
            return self.title.strip()
        return 'System Notification'

    @property
    def display_title(self):
        return self.build_display_title()

    @property
    def display_detail(self):
        obj = self._related_object()
        notification_type = (self.notification_type or '').lower()

        if obj is not None:
            if notification_type.startswith('appointment_') or notification_type == 'appointment_new_request':
                return f"{self._format_date(obj.appointment_date)} • {obj.rice_quantity} kg"
            if notification_type.startswith('dryer_') or notification_type == 'dryer_new_request':
                return f"{self._format_date(obj.rental_date)} • {obj.display_time_range}"
            if notification_type.startswith('rental_'):
                return f"{getattr(obj.machine, 'name', 'Machine')} • {self._format_date(obj.start_date, with_year=False)} - {self._format_date(obj.end_date)}"
            if notification_type.startswith('irrigation_'):
                return f"{self._format_date(obj.requested_date)} • {obj.area_size} ha"

        cleaned = ' '.join((self.message or '').split())
        if '. ' in cleaned:
            return cleaned.split('. ', 1)[0]
        return cleaned[:100]

    @property
    def status_label(self):
        notification_type = (self.notification_type or '').lower()
        if any(token in notification_type for token in ['new_request', 'submitted']):
            return 'Pending'
        if any(token in notification_type for token in ['approved', 'confirmed']):
            return 'Approved'
        if 'completed' in notification_type:
            return 'Completed'
        if any(token in notification_type for token in ['rejected', 'cancelled']):
            return 'Cancelled'
        if 'payment' in notification_type:
            return 'Payment'
        return 'Update'

    @property
    def tone(self):
        notification_type = (self.notification_type or '').lower()
        if any(token in notification_type for token in ['new_request', 'submitted']):
            return 'new'
        if any(token in notification_type for token in ['approved', 'confirmed']):
            return 'approved'
        if 'completed' in notification_type:
            return 'completed'
        if any(token in notification_type for token in ['rejected', 'cancelled']):
            return 'cancelled'
        if 'payment' in notification_type:
            return 'payment'
        return 'default'

    @property
    def tone_icon(self):
        return {
            'new': 'fa-clipboard-list',
            'approved': 'fa-circle-check',
            'completed': 'fa-flag-checkered',
            'cancelled': 'fa-circle-xmark',
            'payment': 'fa-money-bill-wave',
            'default': self.get_icon(),
        }.get(self.tone, 'fa-bell')

    @property
    def action_label(self):
        notification_type = (self.notification_type or '').lower()
        if 'new_request' in notification_type:
            return 'Review'
        if any(token in notification_type for token in ['approved', 'confirmed', 'completed', 'submitted', 'payment']):
            return 'View'
        return 'Open'

    @property
    def review_url(self):
        return self.get_redirect_url()

    @property
    def approval_url(self):
        notification_type = (self.notification_type or '').lower()

        if not self.related_object_id:
            return self.get_redirect_url()

        if notification_type == 'appointment_new_request':
            return reverse('machines:ricemill_appointment_approve', kwargs={'pk': self.related_object_id})
        if notification_type == 'dryer_new_request':
            return reverse('machines:dryer_rental_approve', kwargs={'pk': self.related_object_id})
        if notification_type == 'rental_new_request':
            return reverse('machines:admin_approve_rental', kwargs={'rental_id': self.related_object_id})
        if notification_type == 'irrigation_new_request':
            return reverse('irrigation:admin_irrigation_request_detail', kwargs={'pk': self.related_object_id})
        return self.get_redirect_url()

    @property
    def relative_time(self):
        delta = timezone.now() - self.timestamp
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return 'Just now'
        if seconds < 3600:
            minutes = seconds // 60
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        if seconds < 86400:
            hours = seconds // 3600
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        days = seconds // 86400
        return f'{days} day{"s" if days != 1 else ""} ago'
    
    def get_icon(self):
        """Get Font Awesome icon based on category"""
        icons = {
            'rental': 'fa-tractor',
            'operator': 'fa-user-gear',
            'payment': 'fa-money-bill-wave',
            'maintenance': 'fa-wrench',
            'system': 'fa-bell',
            'irrigation': 'fa-droplet',
            'appointment': 'fa-seedling',
            'membership': 'fa-users',
        }
        return icons.get(self.category, 'fa-bell')
    
    def get_color(self):
        """Get color based on category"""
        colors = {
            'rental': '#10b981',      # Green
            'operator': '#3b82f6',    # Blue
            'payment': '#f59e0b',     # Yellow/Orange
            'maintenance': '#ef4444', # Red
            'system': '#6b7280',      # Gray
            'irrigation': '#06b6d4',  # Cyan
            'appointment': '#8b5cf6', # Purple
            'membership': '#ec4899',  # Pink
        }
        return colors.get(self.category, '#6b7280')
    
    def get_priority_badge(self):
        """Get priority badge color"""
        badges = {
            'critical': 'danger',
            'important': 'warning',
            'normal': 'info',
            'low': 'secondary',
        }
        return badges.get(self.priority, 'info')
    
    def get_redirect_url(self):
        """Get the URL to redirect to when notification is clicked"""
        user = self.user
        is_operator = getattr(user, 'role', '') == 'operator'
        is_admin_user = (user.is_superuser or user.is_staff) and not is_operator

        # If action_url is set, use it directly
        if self.action_url:
            return self.action_url

        def notifications_index():
            if is_operator:
                return reverse('machines:operator_notifications')
            if is_admin_user or (hasattr(user, 'is_president') and user.is_president()):
                return reverse('notifications:all_notifications')
            return reverse('notifications:user_notifications')

        def admin_rental_target():
            if self.related_object_id:
                return reverse('machines:admin_approve_rental', kwargs={'rental_id': self.related_object_id})
            return reverse('machines:admin_rental_dashboard')
        
        # Operator-specific notifications
        if self.notification_type.startswith('operator_'):
            if 'job_assigned' in self.notification_type or 'job_updated' in self.notification_type:
                return reverse('machines:operator_ongoing_jobs')
            elif 'harvest' in self.notification_type:
                return reverse('machines:operator_awaiting_harvest')
            elif 'completed' in self.notification_type:
                return reverse('machines:operator_completed_jobs')
            elif 'machine' in self.notification_type:
                return reverse('machines:operator_view_machines')
            else:
                return reverse('machines:operator_dashboard')
        
        # General announcements and notifications without specific actions - stay on notifications page
        if self.notification_type in ['general', 'reminder', 'alert', 'update', 'maintenance', 'event']:
            return notifications_index()

        # Admin notifications for new requests
        if self.notification_type == 'rental_new_request':
            return admin_rental_target() if is_admin_user else reverse('machines:rental_list')
        
        elif self.notification_type == 'appointment_new_request':
            if self.related_object_id:
                return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:ricemill_appointment_list')

        elif self.notification_type == 'dryer_new_request':
            if self.related_object_id:
                return reverse('machines:dryer_rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:dryer_rental_list')
        
        elif self.notification_type == 'irrigation_new_request':
            if self.related_object_id:
                return reverse('irrigation:admin_irrigation_request_detail', kwargs={'pk': self.related_object_id})
            return reverse('irrigation:admin_irrigation_request_list')
        
        # Admin notifications for rental updates (harvest reports, etc.)
        elif self.notification_type == 'rental_update':
            return admin_rental_target() if is_admin_user else reverse('machines:rental_list')

        elif self.notification_type in [
            'rental_payment_received',
            'rental_payment_recorded',
            'rental_payment_completed',
            'rental_status_update',
            'rental_job_started',
            'rental_job_completed',
            'rental_in_progress',
        ]:
            if is_admin_user:
                return admin_rental_target()
            if self.related_object_id:
                return reverse('machines:rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:rental_list')

        elif self.notification_type in ['rental_conflict', 'rental_conflict_broadcast']:
            return reverse('machines:admin_conflicts_report') if is_admin_user else reverse('machines:rental_list')
        
        # User rental notifications
        elif self.notification_type in [
            'rental_approved',
            'rental_rejected',
            'rental_completed',
            'rental_submitted',
            'rental_cancelled',
            'rental_schedule_changed',
        ]:
            if self.related_object_id:
                return reverse('machines:rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:rental_list')

        elif self.notification_type == 'rental_deleted':
            return reverse('machines:admin_rental_dashboard') if is_admin_user else reverse('machines:rental_list')
        
        # User rice mill appointment notifications
        elif self.notification_type in [
            'appointment_approved',
            'appointment_rejected',
            'appointment_completed',
            'appointment_submitted',
            'appointment_cancelled',
            'appointment_confirmed',
            'appointment_payment_completed',
        ]:
            if self.related_object_id:
                return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:ricemill_appointment_list')

        elif self.notification_type in [
            'dryer_approved',
            'dryer_rejected',
            'dryer_completed',
            'dryer_submitted',
            'dryer_cancelled',
            'dryer_confirmed',
            'dryer_payment_completed',
        ]:
            if self.related_object_id:
                return reverse('machines:dryer_rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:dryer_rental_list')
        
        # User irrigation notifications
        elif self.notification_type in ['irrigation_approved', 'irrigation_rejected', 'irrigation_completed', 'irrigation_submitted', 'irrigation_cancelled']:
            if self.related_object_id:
                return reverse('irrigation:irrigation_request_detail', kwargs={'pk': self.related_object_id})
            return reverse('irrigation:irrigation_request_list')
        
        # Membership notifications
        elif self.notification_type in ['membership_approved', 'membership_rejected', 'membership_required']:
            return reverse('profile')
        
        # Machine status notifications
        elif self.notification_type in ['machine_maintenance', 'machine_available']:
            if self.related_object_id:
                return reverse('machines:machine_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:machine_list')

        elif self.notification_type == 'machine_maintenance_admin':
            return reverse('machines:maintenance_list')

        elif self.notification_type == 'machine_available_admin':
            if self.related_object_id:
                return reverse('machines:machine_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:machine_list')
        
        # Default: return None to stay on current page
        return notifications_index()

class MachineAlert(models.Model):
    machine_name = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.machine_name} - {self.alert_type}"

class RiceMillSchedulingAlert(models.Model):
    schedule_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Schedule {self.schedule_id} - {self.alert_type}"
