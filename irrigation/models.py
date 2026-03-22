from django.db import models
from django.utils import timezone
from users.models import CustomUser, MembershipApplication, Sector
from decimal import Decimal


IRRIGATION_RATE_PER_HECTARE = Decimal('1500.00')

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


class CroppingSeason(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_ACTIVE = 'active'
    STATUS_HARVESTED = 'harvested'
    STATUS_PAID = 'paid'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Planned'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_HARVESTED, 'Harvested'),
        (STATUS_PAID, 'Paid'),
        (STATUS_CLOSED, 'Closed'),
    ]

    name = models.CharField(max_length=150, unique=True)
    planting_date = models.DateField()
    harvest_date = models.DateField()
    irrigation_rate_per_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    billing_generated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_irrigation_seasons'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-planting_date', '-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Irrigation pricing is fixed system-wide: PHP 1,500 per hectare per cropping season.
        self.irrigation_rate_per_hectare = IRRIGATION_RATE_PER_HECTARE
        super().save(*args, **kwargs)

    @property
    def is_harvest_due(self):
        return timezone.localdate() >= self.harvest_date

    @property
    def total_billed_amount(self):
        return sum((record.total_fee for record in self.records.all()), Decimal('0.00'))

    @property
    def total_paid_amount(self):
        return sum((record.amount_paid for record in self.records.all()), Decimal('0.00'))

    @property
    def all_records_paid(self):
        records = self.records.all()
        return records.exists() and not records.exclude(
            status__in=[IrrigationSeasonRecord.STATUS_PAID, IrrigationSeasonRecord.STATUS_CLOSED]
        ).exists()

    def generate_billing(self):
        generated = False
        for record in self.records.select_related('membership').all():
            record.refresh_from_membership(commit=False)
            record.irrigation_rate = self.irrigation_rate_per_hectare
            record.total_fee = record.calculate_total_fee()
            record.billed_at = record.billed_at or timezone.now()
            if record.status in [
                IrrigationSeasonRecord.STATUS_PLANNED,
                IrrigationSeasonRecord.STATUS_ACTIVE,
            ]:
                record.status = IrrigationSeasonRecord.STATUS_HARVESTED
            record.save()
            generated = True

        if generated:
            self.billing_generated_at = self.billing_generated_at or timezone.now()
            if self.status != self.STATUS_CLOSED:
                self.status = self.STATUS_HARVESTED
            self.save(update_fields=['billing_generated_at', 'status', 'updated_at'])
        return generated

    def sync_status(self):
        today = timezone.localdate()
        original_status = self.status

        if self.status == self.STATUS_CLOSED:
            return False

        billing_locked = bool(self.billing_generated_at) or self.records.filter(
            status__in=[
                IrrigationSeasonRecord.STATUS_HARVESTED,
                IrrigationSeasonRecord.STATUS_PAID,
            ]
        ).exists()

        if billing_locked:
            self.status = self.STATUS_PAID if self.all_records_paid else self.STATUS_HARVESTED
        elif today < self.planting_date:
            self.status = self.STATUS_PLANNED
        elif today < self.harvest_date:
            self.status = self.STATUS_ACTIVE
            self.records.filter(
                status__in=[
                    IrrigationSeasonRecord.STATUS_PLANNED,
                    IrrigationSeasonRecord.STATUS_ACTIVE,
                ]
            ).update(status=IrrigationSeasonRecord.STATUS_ACTIVE)
        else:
            self.generate_billing()
            self.status = self.STATUS_PAID if self.all_records_paid else self.STATUS_HARVESTED

        if self.status != original_status:
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False


class IrrigationSeasonRecord(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_ACTIVE = 'active'
    STATUS_HARVESTED = 'harvested'
    STATUS_PAID = 'paid'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Planned'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_HARVESTED, 'Harvested'),
        (STATUS_PAID, 'Paid'),
        (STATUS_CLOSED, 'Closed'),
    ]

    season = models.ForeignKey(CroppingSeason, on_delete=models.CASCADE, related_name='records')
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='irrigation_season_records')
    membership = models.ForeignKey(
        MembershipApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='irrigation_season_records'
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='irrigation_season_records'
    )
    farm_area = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    irrigation_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    billed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_confirmed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_irrigation_payments'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['farmer__last_name', 'farmer__first_name']
        unique_together = ['season', 'farmer']

    def __str__(self):
        return f"{self.season.name} - {self.farmer.get_full_name() or self.farmer.username}"

    def refresh_from_membership(self, commit=True):
        membership = self.membership or getattr(self.farmer, 'membership_application', None)
        if membership:
            self.membership = membership
            self.sector = membership.assigned_sector or membership.sector
            self.farm_area = membership.farm_size or Decimal('0.00')
        self.irrigation_rate = IRRIGATION_RATE_PER_HECTARE
        if commit:
            self.save()

    def calculate_total_fee(self):
        area = self.farm_area or Decimal('0.00')
        rate = IRRIGATION_RATE_PER_HECTARE
        return (Decimal(area) * Decimal(rate)).quantize(Decimal('0.01'))

    @property
    def balance_due(self):
        return max(self.total_fee - self.amount_paid, Decimal('0.00'))

    @property
    def payment_status_label(self):
        return 'Paid' if self.status in [self.STATUS_PAID, self.STATUS_CLOSED] else 'Unpaid'

    def mark_paid(self, confirmed_by=None, amount=None):
        self.amount_paid = amount if amount is not None else self.total_fee
        self.paid_at = timezone.now()
        self.payment_confirmed_by = confirmed_by
        self.status = self.STATUS_PAID
        self.save(update_fields=['amount_paid', 'paid_at', 'payment_confirmed_by', 'status', 'updated_at'])
