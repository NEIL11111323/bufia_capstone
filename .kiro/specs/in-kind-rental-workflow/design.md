# Design Document: IN-KIND Equipment Rental Workflow

## Overview

The IN-KIND Equipment Rental Workflow is a comprehensive system for managing agricultural equipment rentals where members pay using harvested rice instead of cash. The system orchestrates a complete lifecycle from rental request submission through harvest reporting and settlement finalization.

**Key Features:**
- Multi-state workflow management (7 states)
- Automatic BUFIA share calculation using 9:1 rice ratio
- Admin approval and harvest verification
- Harvest report communication via chat
- Settlement finalization with audit trail
- Integrated notification system

**Payment Model:** Members pay BUFIA 1 sack of rice for every 9 sacks harvested (9:1 ratio)

**Workflow Duration:** From rental request to settlement completion, typically spanning the agricultural season

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    IN-KIND Rental Workflow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Rental     │  │ Harvest      │  │ Settlement   │          │
│  │   Management │  │ Report       │  │ Management   │          │
│  │   Module     │  │ Module       │  │ Module       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                    ┌───────▼────────┐                           │
│                    │  Notification  │                           │
│                    │  System        │                           │
│                    └────────────────┘                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Audit Trail & State Machine                      │  │
│  │  (Tracks all state transitions and admin actions)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow State Machine

```
                    ┌─────────────┐
                    │  Requested  │
                    └──────┬──────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │  Pending Approval   │
                  └──────┬──────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
      ┌──────────┐            ┌──────────────┐
      │ Approved │            │  Cancelled   │
      └────┬─────┘            └──────────────┘
           │
           ▼
      ┌──────────────┐
      │ In Progress  │
      └────┬─────────┘
           │
           ▼
  ┌──────────────────────────┐
  │ Harvest Report Submitted │
  └────┬─────────────────────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌────────┐ ┌──────────────┐
│Completed│ │ In Progress  │ (if rejected)
└────────┘ └──────────────┘
```

**Valid State Transitions:**
- Requested → Pending Approval
- Pending Approval → Approved
- Pending Approval → Cancelled
- Approved → In Progress
- Approved → Cancelled
- In Progress → Harvest Report Submitted
- In Progress → Cancelled
- Harvest Report Submitted → Completed
- Harvest Report Submitted → In Progress (if rejected)
- Harvest Report Submitted → Cancelled
- Any State → Cancelled

---

## Components and Interfaces

### 1. Rental Management Module

**Responsibilities:**
- Create and manage rental requests
- Validate rental data
- Track rental lifecycle
- Manage state transitions

**Key Operations:**
- `create_rental_request()` - Member submits rental request
- `approve_rental()` - Admin approves request
- `reject_rental()` - Admin rejects request
- `start_equipment_operation()` - Transition to In Progress
- `cancel_rental()` - Cancel at any point

### 2. Harvest Report Module

**Responsibilities:**
- Record harvest information from operators
- Calculate BUFIA share automatically
- Manage harvest report verification
- Handle report rejection and resubmission

**Key Operations:**
- `record_harvest_report()` - Admin records operator's harvest data
- `verify_harvest_report()` - Admin approves harvest report
- `reject_harvest_report()` - Admin rejects for recount
- `calculate_bufia_share()` - Automatic 9:1 calculation

### 3. Settlement Module

**Responsibilities:**
- Finalize rental transactions
- Create settlement records
- Update settlement status
- Generate settlement references

**Key Operations:**
- `finalize_settlement()` - Create settlement record
- `generate_settlement_reference()` - Create unique reference
- `update_settlement_status()` - Mark as paid

### 4. Notification Module

**Responsibilities:**
- Send notifications at key workflow points
- Route notifications to appropriate users
- Provide action URLs for quick access

**Notification Types:**
- `rental_new_request` - Admin notified of new request
- `rental_approved` - Member notified of approval
- `rental_in_progress` - Member notified equipment is operating
- `harvest_report_submitted` - Admin notified of harvest report
- `harvest_report_approved` - Operator notified of approval
- `harvest_report_rejected` - Operator notified to recount
- `settlement_finalized` - Member notified of completion

---

## Data Models

### Rental Model (Extended)

**New/Modified Fields:**

```python
class Rental(models.Model):
    # Existing fields
    machine = ForeignKey(Machine)
    user = ForeignKey(User)  # Member
    start_date = DateField()
    end_date = DateField()
    payment_type = CharField(choices=[('cash', ...), ('in_kind', ...)])
    settlement_status = CharField(choices=[...])
    
    # IN-KIND Workflow Fields
    workflow_state = CharField(
        max_length=30,
        choices=[
            ('requested', 'Requested'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('in_progress', 'In Progress'),
            ('harvest_report_submitted', 'Harvest Report Submitted'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='requested'
    )
    
    # Equipment Operation Tracking
    actual_handover_date = DateTimeField(null=True, blank=True)
    
    # Harvest Information
    total_rice_sacks_harvested = DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total sacks harvested by operator"
    )
    bufia_share = DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="BUFIA's share (1 sack per 9 harvested)"
    )
    member_share = DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Member's share (remaining sacks)"
    )
    
    # Audit Trail
    state_changed_at = DateTimeField(auto_now=True)
    state_changed_by = ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rental_state_changes'
    )
```

### HarvestReport Model (New)

```python
class HarvestReport(models.Model):
    rental = ForeignKey(Rental, on_delete=models.CASCADE, related_name='harvest_reports')
    
    # Harvest Data
    total_rice_sacks_harvested = DecimalField(max_digits=10, decimal_places=2)
    report_timestamp = DateTimeField(auto_now_add=True)
    
    # Admin Recording
    recorded_by_admin = ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_harvest_reports'
    )
    recording_timestamp = DateTimeField(auto_now_add=True)
    
    # Verification
    is_verified = BooleanField(default=False)
    verified_at = DateTimeField(null=True, blank=True)
    verified_by = ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_harvest_reports'
    )
    verification_notes = TextField(blank=True)
    
    # Rejection Handling
    is_rejected = BooleanField(default=False)
    rejection_reason = TextField(blank=True)
    rejection_timestamp = DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-report_timestamp']
        indexes = [
            models.Index(fields=['rental', 'is_verified']),
            models.Index(fields=['recorded_by_admin', 'report_timestamp']),
        ]
    
    def __str__(self):
        return f"Harvest Report - Rental {self.rental.id} ({self.total_rice_sacks_harvested} sacks)"
```

### Settlement Model (New)

```python
class Settlement(models.Model):
    rental = ForeignKey(Rental, on_delete=models.CASCADE, related_name='settlements')
    
    # Settlement Details
    settlement_date = DateTimeField(auto_now_add=True)
    bufia_share = DecimalField(max_digits=10, decimal_places=2)
    member_share = DecimalField(max_digits=10, decimal_places=2)
    total_harvested = DecimalField(max_digits=10, decimal_places=2)
    
    # Settlement Reference
    settlement_reference = CharField(max_length=50, unique=True)
    
    # Finalization
    finalized_by = ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='finalized_settlements'
    )
    finalized_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-finalized_at']
        indexes = [
            models.Index(fields=['rental', 'finalized_at']),
            models.Index(fields=['settlement_reference']),
        ]
    
    def __str__(self):
        return f"Settlement {self.settlement_reference} - {self.bufia_share} sacks"
```

### RentalStateChange Model (New - Audit Trail)

```python
class RentalStateChange(models.Model):
    rental = ForeignKey(Rental, on_delete=models.CASCADE, related_name='state_changes')
    
    # State Transition
    from_state = CharField(max_length=30)
    to_state = CharField(max_length=30)
    changed_at = DateTimeField(auto_now_add=True)
    changed_by = ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rental_state_changes_made'
    )
    
    # Context
    reason = TextField(blank=True)
    notes = TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['rental', 'changed_at']),
            models.Index(fields=['changed_by', 'changed_at']),
        ]
    
    def __str__(self):
        return f"{self.rental.id}: {self.from_state} → {self.to_state}"
```

### Data Relationships

```
Rental (1) ──────────────── (N) HarvestReport
   │                              │
   │                              └─ recorded_by_admin (User)
   │                              └─ verified_by (User)
   │
   ├─ (1) Settlement
   │       └─ finalized_by (User)
   │
   └─ (N) RentalStateChange
           └─ changed_by (User)
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Rental Request Creation with Correct Initial State

For any member submitting a rental request with valid equipment_id, rental_start_date (not in past), and expected_harvest_date (after start date), the system SHALL create a Rental record with workflow_state = 'requested', payment_type = 'in_kind', settlement_status = 'pending', and all required fields (equipment_id, member_id, rental_start_date, expected_harvest_date) populated.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Admin Approval State Transitions

For any rental in 'requested' state, when an admin approves it, the workflow_state SHALL transition through 'pending_approval' to 'approved', and a UserNotification SHALL be created for the member with notification_type = 'rental_approved'.

**Validates: Requirements 2.1, 2.2, 2.4**

### Property 3: Admin Rejection Sets Cancelled State

For any rental in 'pending_approval' state, when an admin rejects it, the workflow_state SHALL transition to 'cancelled' and settlement_status SHALL be set to 'cancelled'.

**Validates: Requirements 2.3**

### Property 4: Equipment Operation Tracking

For any approved rental transitioning to 'in_progress', the system SHALL record the actual_handover_date with a non-null timestamp, and a UserNotification SHALL be created for the member with notification_type = 'rental_in_progress'.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 5: Harvest Report Recording and State Transition

For any in_progress rental, when an admin records a harvest report with total_rice_sacks_harvested > 0, the system SHALL create a HarvestReport record with all fields (total_rice_sacks_harvested, report_timestamp, recorded_by_admin) populated, and the rental workflow_state SHALL transition to 'harvest_report_submitted'.

**Validates: Requirements 4.2, 4.3, 4.4**

### Property 6: BUFIA Share Calculation Invariant

For any harvest report with total_rice_sacks_harvested = N (where N > 0), the system SHALL calculate bufia_share = floor(N / 9) and member_share = N - bufia_share, such that the invariant bufia_share + member_share = N always holds.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 7: Harvest Report Verification Creates Settlement

For any rental in 'harvest_report_submitted' state, when an admin approves the harvest report, the workflow_state SHALL transition to 'completed', settlement_status SHALL be set to 'paid', and a Settlement record SHALL be created containing settlement_date, bufia_share, member_share, and rental_id.

**Validates: Requirements 6.2, 7.1, 7.2**

### Property 8: Harvest Report Rejection Reverts State

For any rental in 'harvest_report_submitted' state, when an admin rejects the harvest report, the workflow_state SHALL transition back to 'in_progress'.

**Validates: Requirements 6.3**

### Property 9: Settlement Finalization Notification

For any Settlement record created, a UserNotification SHALL be created for the member with notification_type = 'settlement_finalized' and related_object_id pointing to the rental.

**Validates: Requirements 7.3**

### Property 10: Rental Request Validation

For any rental request submission, if equipment_id does not exist, or rental_start_date is in the past, or expected_harvest_date is before or equal to rental_start_date, the system SHALL reject the request and return a validation error.

**Validates: Requirements 8.1**

### Property 11: Harvest Data Validation

For any harvest report recording attempt, if total_rice_sacks_harvested ≤ 0, the system SHALL reject the recording and return a validation error.

**Validates: Requirements 8.2**

### Property 12: Audit Trail Completeness

For any rental, every workflow_state change SHALL create a RentalStateChange record with from_state, to_state, changed_at, and changed_by all populated with non-null values.

**Validates: Requirements 9.1, 9.2**

### Property 13: Notification Delivery for Key Events

For any of the following events (rental request submitted, rental approved, equipment operation begins, harvest report recorded, harvest report approved, settlement finalized), the system SHALL create a UserNotification record with the correct notification_type and recipient (member or admin as appropriate).

**Validates: Requirements 10.1, 10.2**

---

## Error Handling

### Validation Errors

**Rental Request Validation:**
- Equipment does not exist → Return 404 or validation error
- Start date in past → Return validation error with message
- End date before start date → Return validation error with message
- Member has no active membership → Return error requiring membership

**Harvest Report Validation:**
- Total sacks ≤ 0 → Return validation error
- Rental not in 'in_progress' state → Return state error
- Harvest report already submitted → Return duplicate error

### State Transition Errors

**Invalid State Transitions:**
- Attempting to approve a rental not in 'pending_approval' → Return state error
- Attempting to record harvest for non-'in_progress' rental → Return state error
- Attempting to verify harvest for non-'harvest_report_submitted' rental → Return state error

**Conflict Errors:**
- Equipment already booked for dates → Return conflict error
- Multiple harvest reports for same rental → Return duplicate error

### Data Integrity Errors

**Calculation Errors:**
- BUFIA share calculation fails → Log error, use fallback calculation
- Settlement reference generation fails → Retry with timestamp suffix

**Audit Trail Errors:**
- State change record creation fails → Log error, continue with state transition
- Notification sending fails → Log error, retry asynchronously

### Error Response Format

```python
{
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",  # or STATE_ERROR, CONFLICT_ERROR, etc.
        "message": "Human-readable error message",
        "field": "field_name",  # if applicable
        "details": {}  # Additional context
    }
}
```

---

## Testing Strategy

### Dual Testing Approach

The IN-KIND rental workflow requires both unit tests and property-based tests to ensure comprehensive correctness:

- **Unit Tests:** Verify specific examples, edge cases, and error conditions
- **Property Tests:** Verify universal properties across all inputs
- Both are complementary and necessary for complete coverage

### Unit Testing Approach

**Test Categories:**

1. **Rental Request Creation Tests**
   - Valid request creation with all required fields
   - Invalid equipment ID rejection
   - Past date validation
   - End date before start date validation
   - Member without membership rejection

2. **State Transition Tests**
   - Valid transitions succeed
   - Invalid transitions fail with appropriate error
   - State change records created correctly
   - Audit trail populated

3. **Harvest Report Tests**
   - Recording harvest with valid sacks
   - Zero or negative sacks rejection
   - Duplicate report prevention
   - Report verification and rejection flows

4. **BUFIA Share Calculation Tests**
   - 9:1 ratio calculation accuracy
   - Floor operation correctness
   - Member share calculation
   - Sum validation (bufia_share + member_share = total)

5. **Settlement Tests**
   - Settlement creation on verification
   - Unique reference generation
   - Settlement status updates
   - Notification triggers

6. **Notification Tests**
   - Correct notification type for each event
   - Correct recipient selection
   - Action URL generation
   - Notification persistence

7. **Validation Tests**
   - Equipment existence check
   - Date range validation
   - Sack count validation
   - Member status validation

**Unit Test Balance:**
- Focus on specific examples and edge cases
- Avoid writing too many unit tests—property tests handle broad input coverage
- Use Django's `TestCase` for model and view tests
- Mock external dependencies (chat system, payment gateway)
- Aim for meaningful coverage, not just high numbers

### Property-Based Testing Approach

**Testing Library:** `hypothesis` (Python)

**Property Test Configuration:**
- Minimum 100 iterations per property test (due to randomization)
- Each test tagged with design property reference
- Tag format: `Feature: in-kind-rental-workflow, Property {number}: {property_text}`
- Each correctness property SHALL be implemented by a SINGLE property-based test

**Property Tests:**

#### Property 1: Rental Request Creation with Correct Initial State
```python
# Feature: in-kind-rental-workflow, Property 1: Rental Request Creation with Correct Initial State
# For any member submitting a rental request with valid equipment_id, rental_start_date (not in past),
# and expected_harvest_date (after start date), the system SHALL create a Rental record with
# workflow_state = 'requested', payment_type = 'in_kind', settlement_status = 'pending'
@given(
    member=st.just(create_member()),
    equipment=st.just(create_equipment()),
    start_date=st.dates(min_value=date.today()),
    days_until_harvest=st.integers(min_value=1, max_value=365)
)
def test_rental_request_creation(member, equipment, start_date, days_until_harvest):
    harvest_date = start_date + timedelta(days=days_until_harvest)
    rental = create_rental_request(member, equipment, start_date, harvest_date)
    assert rental.workflow_state == 'requested'
    assert rental.payment_type == 'in_kind'
    assert rental.settlement_status == 'pending'
```

#### Property 2: Admin Approval State Transitions
```python
# Feature: in-kind-rental-workflow, Property 2: Admin Approval State Transitions
# For any rental in 'requested' state, when an admin approves it, the workflow_state SHALL
# transition through 'pending_approval' to 'approved', and a UserNotification SHALL be created
@given(rental=st.just(create_rental_in_requested_state()))
def test_admin_approval_transitions(rental):
    admin = create_admin()
    approve_rental(rental, admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'approved'
    notification = UserNotification.objects.filter(
        user=rental.user,
        notification_type='rental_approved',
        related_object_id=rental.id
    ).first()
    assert notification is not None
```

#### Property 3: Admin Rejection Sets Cancelled State
```python
# Feature: in-kind-rental-workflow, Property 3: Admin Rejection Sets Cancelled State
# For any rental in 'pending_approval' state, when an admin rejects it, the workflow_state
# SHALL transition to 'cancelled' and settlement_status SHALL be set to 'cancelled'
@given(rental=st.just(create_rental_in_pending_approval_state()))
def test_admin_rejection_cancels(rental):
    admin = create_admin()
    reject_rental(rental, admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'cancelled'
    assert rental.settlement_status == 'cancelled'
```

#### Property 4: Equipment Operation Tracking
```python
# Feature: in-kind-rental-workflow, Property 4: Equipment Operation Tracking
# For any approved rental transitioning to 'in_progress', the system SHALL record the
# actual_handover_date with a non-null timestamp, and a UserNotification SHALL be created
@given(rental=st.just(create_rental_in_approved_state()))
def test_equipment_operation_tracking(rental):
    admin = create_admin()
    start_equipment_operation(rental, admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'in_progress'
    assert rental.actual_handover_date is not None
    notification = UserNotification.objects.filter(
        user=rental.user,
        notification_type='rental_in_progress',
        related_object_id=rental.id
    ).first()
    assert notification is not None
```

#### Property 5: Harvest Report Recording and State Transition
```python
# Feature: in-kind-rental-workflow, Property 5: Harvest Report Recording and State Transition
# For any in_progress rental, when an admin records a harvest report with
# total_rice_sacks_harvested > 0, the system SHALL create a HarvestReport record
@given(
    rental=st.just(create_rental_in_progress()),
    total_sacks=st.integers(min_value=1, max_value=1000)
)
def test_harvest_report_recording(rental, total_sacks):
    admin = create_admin()
    harvest_report = record_harvest_report(rental, total_sacks, admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'harvest_report_submitted'
    assert harvest_report.total_rice_sacks_harvested == total_sacks
    assert harvest_report.recorded_by_admin == admin
```

#### Property 6: BUFIA Share Calculation Invariant
```python
# Feature: in-kind-rental-workflow, Property 6: BUFIA Share Calculation Invariant
# For any harvest report with total_rice_sacks_harvested = N (where N > 0), the system
# SHALL calculate bufia_share = floor(N / 9) and member_share = N - bufia_share,
# such that the invariant bufia_share + member_share = N always holds
@given(total_sacks=st.integers(min_value=1, max_value=10000))
def test_bufia_share_calculation_invariant(total_sacks):
    bufia_share = calculate_bufia_share(total_sacks)
    member_share = total_sacks - bufia_share
    assert bufia_share == total_sacks // 9
    assert bufia_share + member_share == total_sacks
```

#### Property 7: Harvest Report Verification Creates Settlement
```python
# Feature: in-kind-rental-workflow, Property 7: Harvest Report Verification Creates Settlement
# For any rental in 'harvest_report_submitted' state, when an admin approves the harvest report,
# the workflow_state SHALL transition to 'completed', settlement_status SHALL be set to 'paid'
@given(rental=st.just(create_rental_with_harvest_report_submitted()))
def test_harvest_verification_creates_settlement(rental):
    admin = create_admin()
    verify_harvest_report(rental, admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'completed'
    assert rental.settlement_status == 'paid'
    settlement = Settlement.objects.filter(rental=rental).first()
    assert settlement is not None
    assert settlement.bufia_share is not None
    assert settlement.member_share is not None
```

#### Property 8: Harvest Report Rejection Reverts State
```python
# Feature: in-kind-rental-workflow, Property 8: Harvest Report Rejection Reverts State
# For any rental in 'harvest_report_submitted' state, when an admin rejects the harvest report,
# the workflow_state SHALL transition back to 'in_progress'
@given(rental=st.just(create_rental_with_harvest_report_submitted()))
def test_harvest_rejection_reverts_state(rental):
    admin = create_admin()
    reject_harvest_report(rental, "Recount needed", admin)
    rental.refresh_from_db()
    assert rental.workflow_state == 'in_progress'
```

#### Property 9: Rental Request Validation
```python
# Feature: in-kind-rental-workflow, Property 9: Rental Request Validation
# For any rental request submission, if equipment_id does not exist, or rental_start_date
# is in the past, or expected_harvest_date is before or equal to rental_start_date,
# the system SHALL reject the request and return a validation error
@given(
    equipment_id=st.just(99999),  # Non-existent
    start_date=st.dates(max_value=date.today() - timedelta(days=1)),  # Past date
    harvest_date=st.dates()
)
def test_rental_validation_rejects_invalid_data(equipment_id, start_date, harvest_date):
    member = create_member()
    with pytest.raises(ValidationError):
        create_rental_request(member, equipment_id, start_date, harvest_date)
```

#### Property 10: Harvest Data Validation
```python
# Feature: in-kind-rental-workflow, Property 10: Harvest Data Validation
# For any harvest report recording attempt, if total_rice_sacks_harvested ≤ 0,
# the system SHALL reject the recording and return a validation error
@given(
    rental=st.just(create_rental_in_progress()),
    invalid_sacks=st.integers(max_value=0)
)
def test_harvest_validation_rejects_invalid_sacks(rental, invalid_sacks):
    admin = create_admin()
    with pytest.raises(ValidationError):
        record_harvest_report(rental, invalid_sacks, admin)
```

#### Property 11: Audit Trail Completeness
```python
# Feature: in-kind-rental-workflow, Property 11: Audit Trail Completeness
# For any rental, every workflow_state change SHALL create a RentalStateChange record
# with from_state, to_state, changed_at, and changed_by all populated
@given(rental=st.just(create_rental_in_requested_state()))
def test_audit_trail_completeness(rental):
    admin = create_admin()
    initial_state = rental.workflow_state
    approve_rental(rental, admin)
    state_changes = RentalStateChange.objects.filter(rental=rental)
    assert state_changes.count() > 0
    for change in state_changes:
        assert change.from_state is not None
        assert change.to_state is not None
        assert change.changed_at is not None
        assert change.changed_by is not None
```

#### Property 12: Notification Delivery for Key Events
```python
# Feature: in-kind-rental-workflow, Property 12: Notification Delivery for Key Events
# For any of the following events (rental request submitted, rental approved, equipment
# operation begins, harvest report recorded, harvest report approved, settlement finalized),
# the system SHALL create a UserNotification record with the correct notification_type
@given(
    event_type=st.sampled_from([
        'rental_submitted', 'rental_approved', 'rental_in_progress',
        'harvest_report_submitted', 'harvest_report_approved', 'settlement_finalized'
    ])
)
def test_notification_delivery_for_events(event_type):
    rental = create_rental_in_requested_state()
    admin = create_admin()
    
    # Trigger event
    if event_type == 'rental_submitted':
        # Rental already submitted on creation
        pass
    elif event_type == 'rental_approved':
        approve_rental(rental, admin)
    elif event_type == 'rental_in_progress':
        approve_rental(rental, admin)
        start_equipment_operation(rental, admin)
    elif event_type == 'harvest_report_submitted':
        approve_rental(rental, admin)
        start_equipment_operation(rental, admin)
        record_harvest_report(rental, 100, admin)
    elif event_type == 'harvest_report_approved':
        approve_rental(rental, admin)
        start_equipment_operation(rental, admin)
        record_harvest_report(rental, 100, admin)
        verify_harvest_report(rental, admin)
    elif event_type == 'settlement_finalized':
        approve_rental(rental, admin)
        start_equipment_operation(rental, admin)
        record_harvest_report(rental, 100, admin)
        verify_harvest_report(rental, admin)
    
    # Verify notification exists
    notification = UserNotification.objects.filter(
        notification_type=event_type,
        related_object_id=rental.id
    ).first()
    assert notification is not None
```

### Integration Testing

**End-to-End Workflow Test:**
1. Member creates rental request
2. Admin approves request
3. Admin transitions to in_progress
4. Admin records harvest report
5. Admin verifies harvest
6. Settlement created and finalized
7. Verify all notifications sent
8. Verify audit trail complete

**Error Scenario Tests:**
- Harvest report rejection and resubmission
- Rental cancellation at various states
- Concurrent requests handling
- Data consistency after failures

### Test Coverage Goals

- **Unit Tests:** 85%+ code coverage
- **Property Tests:** All 12 properties covered with minimum 100 iterations each
- **Integration Tests:** Complete workflow + error scenarios
- **Edge Cases:** Zero/negative harvests, boundary values, concurrent operations

