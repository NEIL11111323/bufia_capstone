# Design Document

## Overview

This design document outlines the implementation of a dual transaction ID system for the BUFIA rental payment platform. The system will generate human-readable internal transaction IDs (format: BUF-TXN-YYYY-NNNNN) while maintaining Stripe's external payment identifiers. This approach ensures professional user-facing receipts, robust payment tracking, and future-proofing against payment processor changes.

The current system already has a Payment model (`bufia/models.py`) with Stripe fields (`stripe_session_id`, `stripe_payment_intent_id`), but lacks internal transaction IDs. The Rental model also stores `stripe_session_id` directly. This design will enhance both models to support the dual ID system while maintaining backward compatibility.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  (Receipts, Rental Details, Admin Dashboard, Reports)       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Display Internal Transaction ID
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Business Logic Layer                        │
│  (Payment Processing, Transaction ID Generation)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Store Both IDs
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Data Layer                                │
│  Payment Model: internal_transaction_id + stripe_*_id        │
│  Rental Model: payment relationship                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Webhook Events
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  External Services                           │
│  (Stripe Payment Processing, Webhooks)                       │
└─────────────────────────────────────────────────────────────┘
```

### Transaction ID Generation Flow

```
User Completes Payment
        │
        ▼
Generate Internal Transaction ID
(BUF-TXN-2026-00001)
        │
        ▼
Receive Stripe Payment Intent ID
(pi_3NkE12ABCDxyz)
        │
        ▼
Store Both IDs in Payment Record
        │
        ▼
Display Internal ID to User
(Receipt, Confirmation Page)
```

## Components and Interfaces

### 1. Transaction ID Generator

**Purpose**: Generate unique, sequential internal transaction IDs

**Interface**:
```python
class TransactionIDGenerator:
    @staticmethod
    def generate() -> str:
        """
        Generate a unique internal transaction ID in format BUF-TXN-YYYY-NNNNN
        
        Returns:
            str: Generated transaction ID (e.g., "BUF-TXN-2026-00045")
        """
        pass
    
    @staticmethod
    def get_next_sequence_number(year: int) -> int:
        """
        Get the next sequential number for the given year
        
        Args:
            year: The year for which to get the sequence number
            
        Returns:
            int: Next sequence number (1-based)
        """
        pass
```

**Implementation Details**:
- Uses database-level atomic operations to ensure uniqueness
- Queries the Payment model for the highest sequence number in the current year
- Resets counter to 1 on January 1st of each year
- Zero-pads sequence number to 5 digits
- Thread-safe using database transactions

### 2. Enhanced Payment Model

**Purpose**: Store both internal and external transaction IDs

**Schema Changes**:
```python
class Payment(models.Model):
    # Existing fields
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, default='pending')
    
    # NEW: Internal transaction ID
    internal_transaction_id = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Internal transaction ID (e.g., BUF-TXN-2026-00045)"
    )
    
    # Existing Stripe fields
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    
    # NEW: Additional Stripe field
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # Existing generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Existing timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
```

**New Methods**:
```python
def save(self, *args, **kwargs):
    """Override save to auto-generate internal transaction ID"""
    if not self.internal_transaction_id:
        self.internal_transaction_id = TransactionIDGenerator.generate()
    super().save(*args, **kwargs)

def get_display_transaction_id(self) -> str:
    """Return the user-facing transaction ID"""
    return self.internal_transaction_id

def get_stripe_dashboard_url(self) -> str:
    """Return URL to view this payment in Stripe dashboard"""
    if self.stripe_payment_intent_id:
        return f"https://dashboard.stripe.com/payments/{self.stripe_payment_intent_id}"
    return None
```

### 3. Payment Creation Service

**Purpose**: Handle payment creation with proper ID assignment

**Interface**:
```python
class PaymentService:
    @staticmethod
    def create_payment(
        user: User,
        payment_type: str,
        amount: Decimal,
        related_object: Any,
        stripe_session_id: str = None
    ) -> Payment:
        """
        Create a new payment record with auto-generated internal transaction ID
        
        Args:
            user: User making the payment
            payment_type: Type of payment (rental, appointment, irrigation)
            amount: Payment amount
            related_object: The rental, appointment, or irrigation request
            stripe_session_id: Optional Stripe session ID
            
        Returns:
            Payment: Created payment instance
        """
        pass
    
    @staticmethod
    def update_from_stripe_webhook(
        stripe_payment_intent_id: str,
        stripe_charge_id: str,
        status: str
    ) -> Payment:
        """
        Update payment record from Stripe webhook data
        
        Args:
            stripe_payment_intent_id: Stripe payment intent ID
            stripe_charge_id: Stripe charge ID
            status: Payment status from Stripe
            
        Returns:
            Payment: Updated payment instance
        """
        pass
```

### 4. Webhook Handler Enhancement

**Purpose**: Process Stripe webhooks and update payment records

**Interface**:
```python
@csrf_exempt
def stripe_webhook(request):
    """
    Enhanced webhook handler that:
    1. Validates Stripe signature
    2. Extracts payment_intent and charge IDs
    3. Locates payment by stripe_payment_intent_id
    4. Updates payment status and stripe_charge_id
    5. Logs event with internal transaction ID
    """
    pass
```

### 5. Receipt Generator Enhancement

**Purpose**: Display internal transaction ID on receipts

**Changes**:
- Update receipt templates to show `payment.internal_transaction_id`
- Add QR code containing internal transaction ID
- Include both internal and Stripe IDs in admin-only section
- Format internal ID prominently at top of receipt

### 6. Admin Dashboard Enhancement

**Purpose**: Enable searching and filtering by both ID types

**Features**:
- Search bar accepts both internal and Stripe transaction IDs
- Payment list displays internal transaction ID prominently
- Detail view shows both ID types
- Export functionality includes both ID columns
- Reconciliation report compares internal vs Stripe records

## Data Models

### Payment Model (Enhanced)

```python
class Payment(models.Model):
    """Enhanced payment model with dual transaction IDs"""
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Internal transaction ID (NEW)
    internal_transaction_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Internal transaction ID (BUF-TXN-YYYY-NNNNN)"
    )
    
    # User and payment info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Stripe IDs (ENHANCED)
    stripe_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Stripe PaymentIntent ID"
    )
    stripe_charge_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Stripe Charge ID (NEW)"
    )
    
    # Generic relation to rental/appointment/irrigation
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
                name='unique_internal_transaction_id'
            ),
            models.UniqueConstraint(
                fields=['stripe_payment_intent_id'],
                condition=models.Q(stripe_payment_intent_id__isnull=False),
                name='unique_stripe_payment_intent_id'
            ),
        ]
```

### Rental Model (Relationship Update)

The Rental model will maintain its existing `stripe_session_id` field for backward compatibility, but payment tracking will primarily use the Payment model relationship:

```python
class Rental(models.Model):
    # Existing fields...
    
    # Keep existing stripe_session_id for backward compatibility
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Access payment via reverse generic relation
    @property
    def payment(self):
        """Get associated payment record"""
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self)
        return Payment.objects.filter(content_type=ct, object_id=self.id).first()
    
    @property
    def transaction_id(self):
        """Get internal transaction ID for display"""
        payment = self.payment
        return payment.internal_transaction_id if payment else None
```

### Migration Strategy

**Migration 1: Add new fields**
- Add `internal_transaction_id` field (nullable initially)
- Add `stripe_charge_id` field
- Add database indexes

**Migration 2: Backfill data**
- Generate internal transaction IDs for existing payments
- Maintain chronological order when assigning sequence numbers
- Populate `stripe_charge_id` from Stripe API where possible

**Migration 3: Make field required**
- Change `internal_transaction_id` to non-nullable
- Add unique constraint

## Cor
rectness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Transaction ID Format Validity

*For any* generated internal transaction ID, it must match the format BUF-TXN-YYYY-NNNNN where YYYY is a valid year and NNNNN is a zero-padded 5-digit number.

**Validates: Requirements 1.1**

### Property 2: Transaction ID Uniqueness

*For any* set of generated internal transaction IDs, no two IDs should be identical.

**Validates: Requirements 1.1, 4.3**

### Property 3: Sequential Ordering Within Year

*For any* two payments created in the same calendar year where payment A is created before payment B, the sequence number in A's internal transaction ID must be less than the sequence number in B's internal transaction ID.

**Validates: Requirements 1.4**

### Property 4: Receipt Contains Internal Transaction ID

*For any* payment record, when rendered as a receipt, the output must contain the internal transaction ID.

**Validates: Requirements 1.2, 8.3**

### Property 5: Rental Detail Displays Transaction ID

*For any* rental with an associated payment, the rental detail view must display the internal transaction ID.

**Validates: Requirements 1.3, 8.5**

### Property 6: Stripe IDs Persistence

*For any* payment created with Stripe payment_intent_id and charge_id, both IDs must be retrievable from the stored payment record.

**Validates: Requirements 2.1, 2.2**

### Property 7: Admin View Shows All IDs

*For any* payment record viewed by an administrator, the display must include the internal transaction ID, stripe_payment_intent_id, stripe_charge_id, and stripe_session_id (when present).

**Validates: Requirements 2.3**

### Property 8: Search By Either ID Type

*For any* payment record, searching by either its internal transaction ID or its Stripe payment_intent_id must return that payment record.

**Validates: Requirements 2.4**

### Property 9: Webhook Locates Payment By Stripe ID

*For any* webhook event containing a stripe_payment_intent_id that matches an existing payment, the system must locate and return that payment record.

**Validates: Requirements 3.1**

### Property 10: Webhook Success Updates Status

*For any* payment record, when a Stripe success webhook is processed for that payment, the payment status must be updated to "Paid" or "completed".

**Validates: Requirements 3.2**

### Property 11: Webhook Failure Updates Status

*For any* payment record, when a Stripe failure webhook is processed for that payment, the payment status must be updated to "Failed".

**Validates: Requirements 3.3**

### Property 12: Refund Webhook Updates Correct Payment

*For any* refund webhook containing a stripe_payment_intent_id, the system must update the payment record with the matching internal transaction ID to "Refunded" status.

**Validates: Requirements 3.4**

### Property 13: Webhook Events Are Logged

*For any* webhook event processed, a log entry must be created containing both the internal transaction ID and the Stripe payment_intent_id.

**Validates: Requirements 3.5**

### Property 14: Internal Transaction ID Uniqueness Constraint

*For any* attempt to create two payment records with the same internal transaction ID, the second attempt must fail with a database constraint violation.

**Validates: Requirements 4.3**

### Property 15: Stripe Payment Intent ID Uniqueness Constraint

*For any* attempt to create two payment records with the same non-null stripe_payment_intent_id, the second attempt must fail with a database constraint violation.

**Validates: Requirements 4.4**

### Property 16: User View Shows Only Internal ID

*For any* payment displayed to a non-admin user, the view must show the internal transaction ID but not the Stripe IDs (unless in a payment processor details section).

**Validates: Requirements 5.2**

### Property 17: Reports Use Internal Transaction IDs

*For any* generated payment report, each payment entry must include its internal transaction ID as the primary reference.

**Validates: Requirements 5.3, 6.1**

### Property 18: Payment Exists Without Stripe IDs

*For any* payment record created without Stripe IDs, it must have a valid internal transaction ID.

**Validates: Requirements 5.5**

### Property 19: Export Includes Both ID Types

*For any* payment data export, the output must include separate columns for internal_transaction_id and stripe_payment_intent_id.

**Validates: Requirements 6.2**

### Property 20: Date Range Query Ordering

*For any* date range query on payments, the results must be ordered by internal transaction ID.

**Validates: Requirements 6.3**

### Property 21: Reconciliation View Shows Both IDs

*For any* payment in the reconciliation view, both the internal transaction ID and Stripe transaction IDs must be displayed.

**Validates: Requirements 6.4**

### Property 22: Payment Creation Timestamp

*For any* newly created payment record, it must have a non-null payment_date timestamp.

**Validates: Requirements 6.5**

### Property 23: Payment Success Page Shows Internal ID

*For any* successful payment, the confirmation page must display the internal transaction ID.

**Validates: Requirements 8.1, 8.2**

## Error Handling

### Transaction ID Generation Errors

**Scenario**: Database connection fails during ID generation

**Handling**:
- Retry with exponential backoff (3 attempts)
- If all retries fail, raise `TransactionIDGenerationError`
- Log error with user ID and timestamp
- Display user-friendly error message
- Do not create payment record without internal transaction ID

**Scenario**: Race condition causes duplicate sequence number

**Handling**:
- Database unique constraint will catch duplicate
- Retry ID generation with new sequence number
- Maximum 5 retry attempts
- If retries exhausted, raise `TransactionIDGenerationError`

### Stripe Webhook Errors

**Scenario**: Webhook contains payment_intent_id not in database

**Handling**:
- Log warning with payment_intent_id and event type
- Return HTTP 200 to Stripe (acknowledge receipt)
- Create alert for admin review
- Do not crash webhook handler

**Scenario**: Webhook signature validation fails

**Handling**:
- Log security warning with IP address
- Return HTTP 400 to Stripe
- Alert security team
- Do not process webhook data

**Scenario**: Webhook processing fails mid-update

**Handling**:
- Use database transaction to ensure atomicity
- Rollback on any error
- Log error with internal transaction ID
- Return HTTP 500 to Stripe (will retry)
- Implement idempotency to handle retries safely

### Payment Search Errors

**Scenario**: Search query matches no payments

**Handling**:
- Return empty result set
- Display "No payments found" message
- Suggest checking ID format
- Provide link to payment list

**Scenario**: Search query is ambiguous (partial match)

**Handling**:
- Return all matching payments
- Display count of results
- Allow filtering by date, status, user

### Migration Errors

**Scenario**: Existing payment has no created_at timestamp

**Handling**:
- Use current timestamp as fallback
- Log warning with payment ID
- Continue migration
- Generate report of affected payments

**Scenario**: Migration interrupted mid-process

**Handling**:
- Use database transaction for each batch
- Track migration progress in separate table
- Support resume from last successful batch
- Verify data integrity after completion

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples and edge cases:

**Transaction ID Generator**:
- Test format matches regex pattern
- Test year extraction is correct
- Test sequence number padding
- Test year boundary (Dec 31 → Jan 1)
- Test sequence number overflow (99999 → 100000)

**Payment Model**:
- Test auto-generation of internal transaction ID on save
- Test uniqueness constraint enforcement
- Test Stripe ID storage and retrieval
- Test generic relation to rental/appointment/irrigation
- Test payment status transitions

**Webhook Handler**:
- Test signature validation
- Test payment lookup by Stripe ID
- Test status updates for success/failure/refund
- Test logging of webhook events
- Test handling of unknown payment_intent_id

**Search Functionality**:
- Test search by internal transaction ID (exact match)
- Test search by Stripe payment_intent_id (exact match)
- Test search with no results
- Test search with multiple results

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using the Hypothesis library for Python:

**Configuration**:
- Minimum 100 iterations per property test
- Use database transactions for test isolation
- Generate realistic test data (valid dates, amounts, IDs)

**Test Generators**:

```python
from hypothesis import strategies as st
from hypothesis.extra.django import from_model
from datetime import datetime

# Generate valid years (2020-2030)
years = st.integers(min_value=2020, max_value=2030)

# Generate valid sequence numbers (1-99999)
sequence_numbers = st.integers(min_value=1, max_value=99999)

# Generate valid transaction IDs
transaction_ids = st.builds(
    lambda y, n: f"BUF-TXN-{y}-{n:05d}",
    years,
    sequence_numbers
)

# Generate payment amounts (0.01 to 10000.00)
amounts = st.decimals(
    min_value=0.01,
    max_value=10000.00,
    places=2
)

# Generate Stripe IDs (realistic format)
stripe_payment_intent_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd')),
    min_size=27,
    max_size=27
).map(lambda s: f"pi_{s}")

stripe_charge_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd')),
    min_size=27,
    max_size=27
).map(lambda s: f"ch_{s}")
```

**Property Test Examples**:

```python
from hypothesis import given, settings
from hypothesis.extra.django import TestCase

class TransactionIDPropertyTests(TestCase):
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_generated_ids_are_unique(self, count):
        """Property 2: Transaction ID Uniqueness"""
        ids = [TransactionIDGenerator.generate() for _ in range(count)]
        assert len(ids) == len(set(ids)), "Generated IDs must be unique"
    
    @given(years, sequence_numbers)
    @settings(max_examples=100)
    def test_id_format_is_valid(self, year, seq):
        """Property 1: Transaction ID Format Validity"""
        transaction_id = f"BUF-TXN-{year}-{seq:05d}"
        pattern = r"^BUF-TXN-\d{4}-\d{5}$"
        assert re.match(pattern, transaction_id), "ID must match format"

class PaymentPropertyTests(TestCase):
    @given(from_model(User), amounts, stripe_payment_intent_ids)
    @settings(max_examples=100)
    def test_payment_stores_stripe_ids(self, user, amount, stripe_id):
        """Property 6: Stripe IDs Persistence"""
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            stripe_payment_intent_id=stripe_id
        )
        retrieved = Payment.objects.get(pk=payment.pk)
        assert retrieved.stripe_payment_intent_id == stripe_id

class SearchPropertyTests(TestCase):
    @given(from_model(Payment))
    @settings(max_examples=100)
    def test_search_by_internal_id_finds_payment(self, payment):
        """Property 8: Search By Either ID Type"""
        results = Payment.objects.filter(
            internal_transaction_id=payment.internal_transaction_id
        )
        assert payment in results, "Search by internal ID must find payment"
```

### Integration Testing

Integration tests will verify end-to-end workflows:

**Payment Creation Flow**:
1. User initiates rental payment
2. System generates internal transaction ID
3. Stripe checkout session created
4. User completes payment in Stripe
5. Webhook received and processed
6. Payment record updated with Stripe IDs
7. User sees confirmation with internal transaction ID

**Admin Workflow**:
1. Admin searches for payment by internal transaction ID
2. Admin views payment details (both ID types shown)
3. Admin exports payment report
4. Report contains both internal and Stripe IDs

**Migration Workflow**:
1. Create test database with existing payments (no internal IDs)
2. Run migration script
3. Verify all payments have internal transaction IDs
4. Verify chronological order preserved
5. Verify Stripe IDs unchanged

### Manual Testing Checklist

- [ ] Create new rental payment and verify internal transaction ID format
- [ ] View receipt and confirm internal transaction ID is prominent
- [ ] Search for payment using internal transaction ID
- [ ] Search for payment using Stripe payment_intent_id
- [ ] Process Stripe webhook and verify payment status update
- [ ] Generate payment report and verify both ID types present
- [ ] Test year boundary (create payment on Dec 31 and Jan 1)
- [ ] Verify admin dashboard shows both ID types
- [ ] Verify user dashboard shows only internal ID
- [ ] Test reconciliation view shows matching IDs

## Implementation Notes

### Django Version Compatibility

- Requires Django 3.2 or higher for database constraints
- Uses Django's built-in transaction management
- Compatible with PostgreSQL, MySQL, SQLite

### Performance Considerations

**Transaction ID Generation**:
- Use `select_for_update()` to prevent race conditions
- Cache current year's max sequence number (invalidate on year change)
- Batch generation for bulk operations

**Database Indexes**:
- Index on `internal_transaction_id` for fast lookups
- Index on `stripe_payment_intent_id` for webhook processing
- Composite index on `(user_id, created_at)` for user history queries

**Query Optimization**:
- Use `select_related()` for payment → user queries
- Use `prefetch_related()` for rental → payment queries
- Implement pagination for large result sets

### Security Considerations

**Transaction ID Predictability**:
- Sequential IDs are predictable but acceptable for internal use
- Do not expose sequence numbers in public APIs
- Use UUIDs for public-facing payment links

**Stripe Webhook Validation**:
- Always validate webhook signatures
- Use HTTPS for webhook endpoints
- Implement rate limiting on webhook endpoint
- Log all webhook attempts for audit

**Data Access Control**:
- Users can only view their own internal transaction IDs
- Admins can view all transaction IDs
- Stripe IDs only visible to admins
- Implement row-level security for multi-tenant scenarios

### Backward Compatibility

**Existing Rental.stripe_session_id Field**:
- Keep field for backward compatibility
- Migrate data to Payment model
- Deprecate direct use in new code
- Provide property accessor to Payment model

**Existing Payment Records**:
- Migration will backfill internal transaction IDs
- Preserve all existing Stripe IDs
- Maintain chronological order
- No data loss during migration

### Monitoring and Observability

**Metrics to Track**:
- Transaction ID generation time (p50, p95, p99)
- Webhook processing time
- Payment search query time
- Migration progress and errors

**Alerts to Configure**:
- Transaction ID generation failures
- Webhook signature validation failures
- Duplicate transaction ID attempts
- Missing Stripe IDs for completed payments

**Logging Requirements**:
- Log all transaction ID generations with timestamp
- Log all webhook events with both ID types
- Log all payment status changes
- Log all search queries for audit

## Deployment Plan

### Phase 1: Database Migration (Week 1)

1. Deploy migration to add new fields (nullable)
2. Monitor for errors
3. Verify indexes created successfully

### Phase 2: Backfill Data (Week 1-2)

1. Run backfill script in batches (1000 records per batch)
2. Monitor progress and errors
3. Verify data integrity after each batch
4. Generate reconciliation report

### Phase 3: Code Deployment (Week 2)

1. Deploy updated Payment model with auto-generation
2. Deploy updated views to display internal transaction IDs
3. Deploy updated webhook handler
4. Monitor for errors

### Phase 4: Make Field Required (Week 3)

1. Verify all payments have internal transaction IDs
2. Deploy migration to make field non-nullable
3. Monitor for constraint violations

### Phase 5: UI Updates (Week 3-4)

1. Update receipt templates
2. Update admin dashboard
3. Update user dashboard
4. Update reports and exports

### Rollback Plan

If issues arise:
1. Revert code changes (keep database changes)
2. Internal transaction IDs remain in database
3. System falls back to Stripe IDs for display
4. Fix issues and redeploy

## Future Enhancements

### QR Code Generation

Generate QR codes containing internal transaction IDs for easy scanning and verification.

### SMS/Email Notifications

Include internal transaction ID in payment confirmation SMS and emails.

### Mobile App Integration

Expose internal transaction ID via API for mobile app display.

### Advanced Reconciliation

Build automated reconciliation tool that compares internal records with Stripe dashboard data.

### Multi-Currency Support

Extend internal transaction ID format to include currency code (e.g., BUF-TXN-USD-2026-00001).

### Payment Analytics Dashboard

Create dashboard showing payment trends by internal transaction ID patterns.
