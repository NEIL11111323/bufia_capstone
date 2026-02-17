from django.db import models
from django.utils import timezone
from users.models import CustomUser, MembershipApplication, Sector

class WaterIrrigationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='irrigation_requests')
    membership = models.ForeignKey(MembershipApplication, on_delete=models.SET_NULL, null=True, related_name='irrigation_requests')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, null=False, blank=False, related_name='irrigation_requests')
    
    # Request details
    request_date = models.DateTimeField(auto_now_add=True)
    requested_date = models.DateField(help_text="Requested date for irrigation")
    duration_hours = models.PositiveIntegerField(help_text="Requested duration in hours")
    purpose = models.CharField(max_length=255, help_text="Purpose of irrigation")
    crop_type = models.CharField(max_length=100, help_text="Type of crop being irrigated")
    area_size = models.DecimalField(max_digits=8, decimal_places=2, help_text="Size of area to be irrigated (hectares)")
    
    # Location details
    farm_location = models.CharField(max_length=255, blank=True, null=True, help_text="Farm location description")
    bufia_farm_location = models.CharField(max_length=255, blank=True, null=True, help_text="Specific location within BUFIA's jurisdiction")
    canal_number = models.CharField(max_length=50, blank=True, help_text="Canal number for irrigation")
    block_number = models.CharField(max_length=50, blank=True, help_text="Block number of the farm")
    
    # Additional notes
    special_requirements = models.TextField(blank=True, help_text="Any special requirements for irrigation")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_date = models.DateTimeField(auto_now=True)
    status_notes = models.TextField(blank=True)
    
    # Review information
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_irrigation_requests')
    review_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Water Irrigation Request"
        verbose_name_plural = "Water Irrigation Requests"
        ordering = ['-request_date']
    
    def __str__(self):
        return f"Irrigation Request {self.id} - {self.farmer.get_full_name()} - {self.status}"
    
    def get_transaction_id(self):
        """Get the internal transaction ID from associated payment"""
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        
        try:
            content_type = ContentType.objects.get_for_model(self)
            payment = Payment.objects.filter(
                content_type=content_type,
                object_id=self.id
            ).first()
            
            if payment and payment.internal_transaction_id:
                return payment.internal_transaction_id
        except:
            pass
        
        return None
    
    def save(self, *args, **kwargs):
        # Track when status changes
        if self.pk:
            old_instance = WaterIrrigationRequest.objects.get(pk=self.pk)
            status_changed = old_instance.status != self.status
        else:
            status_changed = True  # New instance
            
        super().save(*args, **kwargs)
        
        # Create history entry if this is a new instance or status changed
        if status_changed:
            IrrigationRequestHistory.objects.create(
                request=self,
                status=self.status,
                changed_by=self.reviewed_by,
                notes=self.status_notes or "Status updated"
            )


class IrrigationRequestHistory(models.Model):
    request = models.ForeignKey(WaterIrrigationRequest, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20, choices=WaterIrrigationRequest.STATUS_CHOICES)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    changed_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_date']
        verbose_name = "Irrigation Request History"
        verbose_name_plural = "Irrigation Request Histories"
    
    def __str__(self):
        return f"History: Request {self.request.id} - {self.status} on {self.changed_date}"
