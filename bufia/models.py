from decimal import Decimal

from django.core.exceptions import ValidationError
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
        ('rice_sale', 'Rice Sale'),
        ('dryer', 'Dryer Rental'),
        ('irrigation', 'Irrigation Request'),
        ('membership', 'Membership Fee'),
    ]
    PAYMENT_PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('paymongo', 'PayMongo'),
        ('manual', 'Manual'),
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
    amount_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_provider = models.CharField(
        max_length=20,
        choices=PAYMENT_PROVIDER_CHOICES,
        blank=True,
        null=True,
        help_text="Payment gateway or channel used for this payment record.",
    )
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments',
        help_text="Staff user who processed the over-the-counter payment.",
    )

    # External gateway references. Legacy Stripe field names are retained for
    # backward compatibility with existing records and related workflows.
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Stripe Charge ID")
    
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
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['stripe_charge_id']),
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
    
    def get_stripe_dashboard_url(self) -> str:
        """Return URL to view this payment in Stripe dashboard when applicable."""
        if self.payment_provider == 'stripe' and self.stripe_payment_intent_id:
            return f"https://dashboard.stripe.com/payments/{self.stripe_payment_intent_id}"
        return None

    @property
    def provider_display_name(self) -> str:
        if self.payment_provider:
            return dict(self.PAYMENT_PROVIDER_CHOICES).get(self.payment_provider, self.payment_provider.title())
        if self.stripe_session_id or self.stripe_payment_intent_id or self.stripe_charge_id:
            return 'Online'
        return 'N/A'

    @property
    def payment_channel_display(self) -> str:
        if self.amount_received is not None:
            return 'Over the Counter'
        if self.stripe_session_id or self.stripe_payment_intent_id or self.stripe_charge_id:
            return 'Gcash Payment'
        if self.payment_provider == 'manual':
            return 'Office / Manual'
        return 'Over the Counter'

    def _gateway_reference_label(self, paymongo_label: str, stripe_label: str, default_label: str) -> str:
        if self.payment_provider == 'paymongo':
            return paymongo_label
        if self.payment_provider == 'stripe':
            return stripe_label
        return default_label

    @property
    def checkout_session_reference(self) -> str:
        return self.stripe_session_id or ''

    @property
    def checkout_session_reference_label(self) -> str:
        return self._gateway_reference_label(
            'PayMongo Checkout Session ID',
            'Stripe Checkout Session ID',
            'Checkout Session ID',
        )

    @property
    def payment_intent_reference(self) -> str:
        return self.stripe_payment_intent_id or ''

    @property
    def payment_intent_reference_label(self) -> str:
        return self._gateway_reference_label(
            'PayMongo Payment Intent ID',
            'Stripe Payment Intent ID',
            'Gateway Payment Intent ID',
        )

    @property
    def gateway_payment_reference(self) -> str:
        return self.stripe_charge_id or ''

    @property
    def gateway_payment_reference_label(self) -> str:
        return self._gateway_reference_label(
            'PayMongo Payment ID',
            'Stripe Charge ID',
            'Gateway Payment ID',
        )
    
    @property
    def transaction_id(self) -> str:
        """Property accessor for transaction ID"""
        return self.internal_transaction_id

    @property
    def total_refunded(self):
        total = self.refunds.filter(status='refunded').aggregate(
            total=models.Sum('amount')
        )['total']
        return total or Decimal('0.00')

    @property
    def refundable_balance(self):
        remaining = self.amount - self.total_refunded
        return remaining if remaining > Decimal('0.00') else Decimal('0.00')

    @property
    def has_refunded_record(self) -> bool:
        return self.refunds.filter(status='refunded').exists()

    @property
    def refund_status(self) -> str:
        total = self.total_refunded
        if total <= Decimal('0.00'):
            return 'Not Refunded'
        if total < self.amount:
            return 'Partially Refunded'
        return 'Fully Refunded'

    @property
    def net_retained(self):
        net = self.amount - self.total_refunded
        return net if net > Decimal('0.00') else Decimal('0.00')

    @property
    def can_accept_refunds(self) -> bool:
        return (
            self.status == 'completed'
            and self.refundable_balance > Decimal('0.00')
        )
    
    def __str__(self):
        if self.internal_transaction_id:
            return f"{self.internal_transaction_id} - {self.user.username} - ${self.amount}"
        return f"{self.get_payment_type_display()} - {self.user.username} - ${self.amount} ({self.status})"


class Refund(models.Model):
    REFUND_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('gcash', 'GCash'),
        ('bank_transfer', 'Bank Transfer'),
        ('manual', 'Manual / Office Adjustment'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=REFUND_METHOD_CHOICES)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='refunded')
    refunded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds',
    )
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['refunded_at']),
            models.Index(fields=['created_at']),
        ]

    def clean(self):
        super().clean()

        if self.amount is None:
            raise ValidationError({'amount': 'Refund amount is required.'})
        if self.amount <= Decimal('0.00'):
            raise ValidationError({'amount': 'Refund amount must be greater than 0.'})
        if not getattr(self, 'payment_id', None):
            return

        refunded_total = self.payment.refunds.filter(status='refunded').exclude(pk=self.pk).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        remaining = self.payment.amount - refunded_total

        if self.status == 'refunded' and self.amount > remaining:
            raise ValidationError({
                'amount': f'Refund amount cannot exceed the refundable balance of PHP {remaining:.2f}.'
            })

    def __str__(self):
        return f"Refund #{self.pk or 'new'} for payment #{self.payment_id}"
