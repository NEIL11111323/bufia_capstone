from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Payment(models.Model):
    """Track payments for rentals, appointments, and irrigation requests"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('rental', 'Machine Rental'),
        ('appointment', 'Rice Mill Appointment'),
        ('irrigation', 'Irrigation Request'),
    ]
    
    # Internal transaction ID (nullable initially for migration)
    internal_transaction_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        editable=False,
        help_text="Internal transaction ID (BUF-TXN-YYYY-NNNNN)"
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Stripe information
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Generic relation to link to rental, appointment, or irrigation request
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['internal_transaction_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['internal_transaction_id'],
                condition=models.Q(internal_transaction_id__isnull=False),
                name='unique_internal_transaction_id'
            ),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate internal transaction ID"""
        if not self.internal_transaction_id:
            from bufia.utils.transaction_id import TransactionIDGenerator
            self.internal_transaction_id = TransactionIDGenerator.generate()
        super().save(*args, **kwargs)
    
    def get_display_transaction_id(self) -> str:
        """Return the user-facing transaction ID"""
        return self.internal_transaction_id or "Pending"
    
    def get_formatted_transaction_id(self) -> str:
        """Return formatted transaction ID for display"""
        if self.internal_transaction_id:
            return self.internal_transaction_id
        return "N/A"
    
    @property
    def transaction_id(self) -> str:
        """Property accessor for transaction ID"""
        return self.internal_transaction_id
    
    def __str__(self):
        if self.internal_transaction_id:
            return f"{self.internal_transaction_id} - {self.user.username} - ${self.amount}"
        return f"{self.get_payment_type_display()} - {self.user.username} - ${self.amount} ({self.status})"
