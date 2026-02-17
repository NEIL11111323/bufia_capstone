"""
Add this model to machines/models.py

This model provides temporary locking mechanism to prevent race conditions
during the booking process. Locks expire after 5 minutes.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class RentalLock(models.Model):
    """
    Temporary lock to prevent race conditions during booking process.
    Locks expire after 5 minutes to prevent indefinite blocking.
    """
    machine = models.ForeignKey('Machine', on_delete=models.CASCADE, related_name='rental_locks')
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['machine', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Lock: {self.machine.name} ({self.start_date} to {self.end_date}) by {self.user.username}"
    
    def is_expired(self):
        """Check if this lock has expired"""
        return timezone.now() > self.expires_at
    
    def save(self, *args, **kwargs):
        """Set expiration time if not already set"""
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)


# After adding this model to machines/models.py, run:
# python manage.py makemigrations machines
# python manage.py migrate machines
