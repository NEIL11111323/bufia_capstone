from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Fields for dynamic routing
    related_object_id = models.IntegerField(null=True, blank=True, help_text="ID of the related object (rental, appointment, etc.)")
    action_url = models.CharField(max_length=255, null=True, blank=True, help_text="Direct URL to navigate to")

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"
    
    def get_redirect_url(self):
        """Get the URL to redirect to when notification is clicked"""
        # If action_url is set, use it directly
        if self.action_url:
            return self.action_url
        
        # Otherwise, determine URL based on notification type and related object
        from django.urls import reverse
        
        # General announcements and notifications without specific actions - stay on notifications page
        if self.notification_type in ['general', 'reminder', 'alert', 'update', 'maintenance', 'event']:
            return None  # Will stay on current page
        
        # Admin notifications for new requests
        if self.notification_type == 'rental_new_request':
            if self.related_object_id:
                return reverse('machines:rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:rental_list')
        
        elif self.notification_type == 'appointment_new_request':
            if self.related_object_id:
                return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:ricemill_appointment_list')
        
        elif self.notification_type == 'irrigation_new_request':
            if self.related_object_id:
                return reverse('irrigation:admin_irrigation_request_detail', kwargs={'pk': self.related_object_id})
            return reverse('irrigation:admin_irrigation_request_list')
        
        # User rental notifications
        elif self.notification_type in ['rental_approved', 'rental_rejected', 'rental_completed', 'rental_submitted', 'rental_cancelled']:
            if self.related_object_id:
                return reverse('machines:rental_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:rental_list')
        
        # User rice mill appointment notifications
        elif self.notification_type in ['appointment_approved', 'appointment_rejected', 'appointment_completed', 'appointment_submitted', 'appointment_cancelled']:
            if self.related_object_id:
                return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.related_object_id})
            return reverse('machines:ricemill_appointment_list')
        
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
        
        # Default: return None to stay on current page
        return None

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
