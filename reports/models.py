from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserActivityReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"

class MachineUsageReport(models.Model):
    machine_name = models.CharField(max_length=100)
    usage_type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.machine_name} - {self.usage_type}"

class RiceMillSchedulingReport(models.Model):
    schedule_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"Schedule {self.schedule_id} - {self.user.username}" 


class RiceSaleSetting(models.Model):
    current_price_per_sack = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_available_for_sale = models.BooleanField(default=False)
    harvest_milling_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='harvest_milling_rice_sale_settings',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_rice_sale_settings',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rice Sale Setting'
        verbose_name_plural = 'Rice Sale Settings'

    def __str__(self):
        return f"Rice Sale Setting - PHP {self.current_price_per_sack:.2f} per sack"

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'current_price_per_sack': Decimal('0.00'),
                'is_available_for_sale': False,
            },
        )
        return obj


class RiceSale(models.Model):
    PAYMENT_METHOD_GCASH = 'gcash'
    PAYMENT_METHOD_OTC = 'otc'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_GCASH, 'Gcash Payment'),
        (PAYMENT_METHOD_OTC, 'Over the Counter'),
    ]
    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_PAID = 'paid'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending Payment'),
        (PAYMENT_STATUS_PAID, 'Paid'),
    ]
    ORDER_STATUS_RESERVED = 'reserved'
    ORDER_STATUS_READY = 'ready'
    ORDER_STATUS_CLAIMED = 'claimed'
    ORDER_STATUS_CANCELLED = 'cancelled'
    ORDER_STATUS_CHOICES = [
        (ORDER_STATUS_RESERVED, 'Reserved'),
        (ORDER_STATUS_READY, 'Ready for Pickup'),
        (ORDER_STATUS_CLAIMED, 'Claimed'),
        (ORDER_STATUS_CANCELLED, 'Cancelled'),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rice_purchases')
    rice_type = models.CharField(max_length=100, blank=True)
    sacks = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_sack = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pickup_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_OTC)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default=ORDER_STATUS_RESERVED)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_given = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_rice_sales',
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Rice Sale'
        verbose_name_plural = 'Rice Sales'

    def __str__(self):
        return f"{self.reference_number or self.pk} - {self.buyer.username}"

    def save(self, *args, **kwargs):
        self.total_amount = (Decimal(str(self.sacks or '0')) * Decimal(str(self.price_per_sack or '0'))).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
        if not self.reference_number:
            self.reference_number = f'BUFIA-RICE-{self.pk:05d}'
            super().save(update_fields=['reference_number'])

    @property
    def is_active_reservation(self):
        return self.order_status in {
            self.ORDER_STATUS_RESERVED,
            self.ORDER_STATUS_READY,
        }
