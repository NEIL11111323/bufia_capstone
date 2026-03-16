# Implementation Plan: IN-KIND Equipment Rental Workflow

## Overview

This implementation plan breaks down the IN-KIND Equipment Rental Workflow feature into discrete, incremental coding tasks. The workflow manages the complete lifecycle of equipment rentals where members pay using harvested rice (9:1 ratio). Implementation follows a layered approach: database schema, core business logic, admin interfaces, member views, notifications, and comprehensive testing.

---

## Tasks

- [x] 1. Set up database models and migrations
  - [x] 1.1 Extend Rental model with workflow state and harvest fields
    - Add `workflow_state` field with 7 state choices
    - Add `actual_handover_date`, `total_rice_sacks_harvested`, `bufia_share`, `member_share` fields
    - Add `state_changed_at` and `state_changed_by` fields for audit tracking
    - _Requirements: 1.1, 1.2, 3.1, 5.1_
  
  - [x] 1.2 Create HarvestReport model
    - Define fields: `rental`, `total_rice_sacks_harvested`, `report_timestamp`, `recorded_by_admin`, `recording_timestamp`
    - Add verification fields: `is_verified`, `verified_at`, `verified_by`, `verification_notes`
    - Add rejection fields: `is_rejected`, `rejection_reason`, `rejection_timestamp`
    - Add database indexes on `(rental, is_verified)` and `(recorded_by_admin, report_timestamp)`
    - _Requirements: 4.2, 4.3, 6.2_
  
  - [x] 1.3 Create Settlement model
    - Define fields: `rental`, `settlement_date`, `bufia_share`, `member_share`, `total_harvested`
    - Add `settlement_reference` (unique), `finalized_by`, `finalized_at`
    - Add database indexes on `(rental, finalized_at)` and `settlement_reference`
    - _Requirements: 7.1, 7.2_
  
  - [x] 1.4 Create RentalStateChange model for audit trail
    - Define fields: `rental`, `from_state`, `to_state`, `changed_at`, `changed_by`
    - Add context fields: `reason`, `notes`
    - Add database indexes on `(rental, changed_at)` and `(changed_by, changed_at)`
    - _Requirements: 9.1, 9.2_
  
  - [x] 1.5 Create and run database migrations
    - Generate migrations for all new models and Rental model changes
    - Apply migrations to database
    - Verify schema integrity
    - _Requirements: 1.1, 4.2, 7.1, 9.1_

- [x] 2. Implement core business logic utilities
  - [x] 2.1 Create rental request creation and validation
    - Implement `create_rental_request(member, equipment, start_date, harvest_date)` function
    - Validate equipment exists, start_date not in past, harvest_date after start_date
    - Create Rental with `workflow_state='requested'`, `payment_type='in_kind'`, `settlement_status='pending'`
    - Record initial state change in RentalStateChange
    - _Requirements: 1.1, 1.2, 1.3, 8.1_
  
  - [ ]* 2.2 Write property test for rental request creation
    - **Property 1: Rental Request Creation with Correct Initial State**
    - **Validates: Requirements 1.1, 1.2, 1.3**
  
  - [x] 2.3 Implement state transition logic with validation
    - Create `transition_rental_state(rental, new_state, admin, reason='')` function
    - Validate state transition is allowed (check valid transitions list)
    - Create RentalStateChange record with from_state, to_state, changed_by, timestamp
    - Return error if transition invalid
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 4.4, 6.3_
  
  - [ ]* 2.4 Write property test for state transition validation
    - **Property 3: Admin Rejection Sets Cancelled State**
    - **Validates: Requirements 2.3**
  
  - [x] 2.5 Implement BUFIA share calculation
    - Create `calculate_bufia_share(total_sacks)` function
    - Calculate `bufia_share = floor(total_sacks / 9)`
    - Calculate `member_share = total_sacks - bufia_share`
    - Ensure invariant: `bufia_share + member_share == total_sacks`
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ]* 2.6 Write property test for BUFIA share calculation invariant
    - **Property 6: BUFIA Share Calculation Invariant**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 3. Implement rental approval workflow
  - [x] 3.1 Implement admin rental approval function
    - Create `approve_rental(rental, admin)` function
    - Transition from 'requested' → 'pending_approval' → 'approved'
    - Create RentalStateChange records for each transition
    - Trigger notification to member with `notification_type='rental_approved'`
    - _Requirements: 2.1, 2.2, 2.4_
  
  - [ ]* 3.2 Write property test for admin approval transitions
    - **Property 2: Admin Approval State Transitions**
    - **Validates: Requirements 2.1, 2.2, 2.4**
  
  - [x] 3.3 Implement admin rental rejection function
    - Create `reject_rental(rental, admin, reason='')` function
    - Transition to 'cancelled' state
    - Set `settlement_status='cancelled'`
    - Create RentalStateChange record
    - _Requirements: 2.3_

- [x] 4. Implement equipment operation tracking
  - [x] 4.1 Implement equipment operation start function
    - Create `start_equipment_operation(rental, admin)` function
    - Transition from 'approved' → 'in_progress'
    - Record `actual_handover_date` with current timestamp
    - Create RentalStateChange record
    - Trigger notification to member with `notification_type='rental_in_progress'`
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ]* 4.2 Write property test for equipment operation tracking
    - **Property 4: Equipment Operation Tracking**
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 5. Implement harvest report recording
  - [x] 5.1 Implement harvest report recording function
    - Create `record_harvest_report(rental, total_sacks, admin)` function
    - Validate `total_sacks > 0` (reject if invalid)
    - Create HarvestReport record with all fields populated
    - Calculate and store `bufia_share` and `member_share` on Rental
    - Transition rental to 'harvest_report_submitted'
    - Create RentalStateChange record
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 8.2_
  
  - [ ]* 5.2 Write property test for harvest report recording
    - **Property 5: Harvest Report Recording and State Transition**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  
  - [ ]* 5.3 Write property test for harvest data validation
    - **Property 10: Harvest Data Validation**
    - **Validates: Requirements 8.2**

- [x] 6. Implement harvest report verification
  - [x] 6.1 Implement harvest report verification function
    - Create `verify_harvest_report(rental, admin, notes='')` function
    - Transition rental to 'completed'
    - Set `settlement_status='paid'`
    - Mark HarvestReport as `is_verified=True`, record `verified_at` and `verified_by`
    - Create RentalStateChange record
    - _Requirements: 6.2, 7.1, 7.2_
  
  - [x] 6.2 Implement harvest report rejection function
    - Create `reject_harvest_report(rental, reason, admin)` function
    - Transition rental back to 'in_progress'
    - Mark HarvestReport as `is_rejected=True`, record `rejection_reason` and `rejection_timestamp`
    - Create RentalStateChange record
    - _Requirements: 6.3_
  
  - [ ]* 6.3 Write property test for harvest verification creates settlement
    - **Property 7: Harvest Report Verification Creates Settlement**
    - **Validates: Requirements 6.2, 7.1, 7.2**
  
  - [ ]* 6.4 Write property test for harvest rejection reverts state
    - **Property 8: Harvest Report Rejection Reverts State**
    - **Validates: Requirements 6.3**

- [x] 7. Implement settlement finalization
  - [x] 7.1 Implement settlement creation function
    - Create `finalize_settlement(rental, admin)` function
    - Create Settlement record with `settlement_date`, `bufia_share`, `member_share`, `total_harvested`
    - Generate unique `settlement_reference` using format: `SETTLE-{rental_id}-{timestamp}`
    - Set `finalized_by=admin`, `finalized_at=now()`
    - Trigger notification to member with `notification_type='settlement_finalized'`
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 8. Implement validation and error handling
  - [x] 8.1 Implement rental request validation
    - Create `validate_rental_request(equipment_id, start_date, harvest_date)` function
    - Check equipment exists (raise 404 if not)
    - Check start_date not in past (raise ValidationError if true)
    - Check harvest_date after start_date (raise ValidationError if false)
    - Return validation errors with descriptive messages
    - _Requirements: 8.1_
  
  - [ ]* 8.2 Write property test for rental request validation
    - **Property 9: Rental Request Validation**
    - **Validates: Requirements 8.1**

- [x] 9. Implement audit trail recording
  - [x] 9.1 Ensure all state transitions create audit records
    - Verify every `transition_rental_state()` call creates RentalStateChange
    - Verify all fields populated: `from_state`, `to_state`, `changed_at`, `changed_by`
    - Test audit trail completeness across all workflow paths
    - _Requirements: 9.1, 9.2_
  
  - [ ]* 9.2 Write property test for audit trail completeness
    - **Property 11: Audit Trail Completeness**
    - **Validates: Requirements 9.1, 9.2**

- [x] 10. Implement notification system integration
  - [x] 10.1 Create notification trigger functions
    - Create `notify_rental_request_submitted(rental)` - notify admin
    - Create `notify_rental_approved(rental)` - notify member
    - Create `notify_rental_in_progress(rental)` - notify member
    - Create `notify_harvest_report_submitted(rental)` - notify admin
    - Create `notify_harvest_report_approved(rental)` - notify operator
    - Create `notify_harvest_report_rejected(rental)` - notify operator
    - Create `notify_settlement_finalized(rental)` - notify member
    - Each function creates UserNotification with correct `notification_type` and recipient
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 10.2 Write property test for notification delivery
    - **Property 12: Notification Delivery for Key Events**
    - **Validates: Requirements 10.1, 10.2**

- [x] 11. Checkpoint - Verify core business logic
  - Ensure all business logic functions work correctly
  - Verify state transitions follow valid paths
  - Verify BUFIA share calculations are accurate
  - Ask the user if questions arise

- [x] 12. Update admin interface
  - [x] 12.1 Update admin dashboard to show pending rental approvals
    - Display rentals in 'requested' state in pending approvals section
    - Show equipment name, member name, rental dates
    - Add action buttons for approve/reject
    - _Requirements: 2.1_
  
  - [x] 12.2 Create harvest report verification interface
    - Display rentals in 'harvest_report_submitted' state
    - Show harvest report details (total sacks, recorded by, timestamp)
    - Add action buttons for verify/reject with notes field
    - _Requirements: 6.2, 6.3_
  
  - [x] 12.3 Add state transition actions to admin
    - Add action to transition approved rentals to 'in_progress'
    - Add action to cancel rentals at any state
    - Show current workflow state for each rental
    - _Requirements: 3.1, 2.3_
  
  - [x] 12.4 Display audit trail in rental detail view
    - Show RentalStateChange records in chronological order
    - Display from_state, to_state, changed_at, changed_by for each change
    - Show reason/notes if available
    - _Requirements: 9.1, 9.2_

- [ ] 13. Implement member views and forms
  - [ ] 13.1 Create rental request form
    - Create ModelForm for Rental with fields: equipment, start_date, expected_harvest_date
    - Add form validation for dates and equipment
    - _Requirements: 1.1, 1.2_
  
  - [ ] 13.2 Create rental detail view for members
    - Display rental information and current workflow_state
    - Show equipment details, dates, harvest information if available
    - Show settlement information if completed
    - _Requirements: 1.1, 3.1, 4.4, 7.1_
  
  - [ ] 13.3 Create rental list view for members
    - Display all rentals for logged-in member
    - Filter by workflow_state (requested, approved, in_progress, completed, cancelled)
    - Show summary: equipment, dates, current state
    - _Requirements: 1.1_

- [ ] 14. Checkpoint - Verify admin and member interfaces
  - Ensure admin dashboard displays pending approvals correctly
  - Ensure harvest verification interface works
  - Ensure member views display rental information correctly
  - Ask the user if questions arise

- [x] 15. Write comprehensive unit tests
  - [x] 15.1 Write unit tests for rental request creation
    - Test valid request creation with all fields
    - Test invalid equipment ID rejection
    - Test past date validation
    - Test end date before start date validation
    - _Requirements: 1.1, 1.2, 8.1_
  
  - [x] 15.2 Write unit tests for state transitions
    - Test valid transitions succeed
    - Test invalid transitions fail with error
    - Test state change records created correctly
    - Test audit trail populated
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 9.1_
  
  - [x] 15.3 Write unit tests for harvest report operations
    - Test recording harvest with valid sacks
    - Test zero/negative sacks rejection
    - Test duplicate report prevention
    - Test verification and rejection flows
    - _Requirements: 4.2, 4.3, 6.2, 6.3_
  
  - [x] 15.4 Write unit tests for BUFIA share calculation
    - Test 9:1 ratio calculation accuracy
    - Test floor operation correctness
    - Test member share calculation
    - Test sum validation (bufia_share + member_share = total)
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 15.5 Write unit tests for settlement operations
    - Test settlement creation on verification
    - Test unique reference generation
    - Test settlement status updates
    - _Requirements: 7.1, 7.2_
  
  - [x] 15.6 Write unit tests for notifications
    - Test correct notification type for each event
    - Test correct recipient selection
    - Test notification persistence
    - _Requirements: 10.1, 10.2_

- [ ] 16. Write property-based tests for all correctness properties
  - [ ]* 16.1 Property test: Rental request creation with correct initial state
    - **Property 1: Rental Request Creation with Correct Initial State**
    - **Validates: Requirements 1.1, 1.2, 1.3**
  
  - [ ]* 16.2 Property test: Admin approval state transitions
    - **Property 2: Admin Approval State Transitions**
    - **Validates: Requirements 2.1, 2.2, 2.4**
  
  - [ ]* 16.3 Property test: Admin rejection sets cancelled state
    - **Property 3: Admin Rejection Sets Cancelled State**
    - **Validates: Requirements 2.3**
  
  - [ ]* 16.4 Property test: Equipment operation tracking
    - **Property 4: Equipment Operation Tracking**
    - **Validates: Requirements 3.1, 3.2, 3.3**
  
  - [ ]* 16.5 Property test: Harvest report recording and state transition
    - **Property 5: Harvest Report Recording and State Transition**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  
  - [ ]* 16.6 Property test: BUFIA share calculation invariant
    - **Property 6: BUFIA Share Calculation Invariant**
    - **Validates: Requirements 5.1, 5.2, 5.3**
  
  - [ ]* 16.7 Property test: Harvest report verification creates settlement
    - **Property 7: Harvest Report Verification Creates Settlement**
    - **Validates: Requirements 6.2, 7.1, 7.2**
  
  - [ ]* 16.8 Property test: Harvest report rejection reverts state
    - **Property 8: Harvest Report Rejection Reverts State**
    - **Validates: Requirements 6.3**
  
  - [ ]* 16.9 Property test: Rental request validation
    - **Property 9: Rental Request Validation**
    - **Validates: Requirements 8.1**
  
  - [ ]* 16.10 Property test: Harvest data validation
    - **Property 10: Harvest Data Validation**
    - **Validates: Requirements 8.2**
  
  - [ ]* 16.11 Property test: Audit trail completeness
    - **Property 11: Audit Trail Completeness**
    - **Validates: Requirements 9.1, 9.2**
  
  - [ ]* 16.12 Property test: Notification delivery for key events
    - **Property 12: Notification Delivery for Key Events**
    - **Validates: Requirements 10.1, 10.2**

- [ ] 17. Write integration tests for complete workflow
  - [ ]* 17.1 Write end-to-end workflow integration test
    - Test complete flow: request → approval → in_progress → harvest_report → verification → settlement
    - Verify all state transitions occur correctly
    - Verify all notifications sent at each step
    - Verify audit trail complete
    - Verify settlement created with correct calculations
    - _Requirements: 1.1, 2.1, 3.1, 4.2, 6.2, 7.1, 9.1, 10.1_
  
  - [ ]* 17.2 Write error scenario integration tests
    - Test harvest report rejection and resubmission flow
    - Test rental cancellation at various states
    - Test validation error handling
    - _Requirements: 6.3, 2.3, 8.1, 8.2_

- [x] 18. Final checkpoint - Ensure all tests pass
  - Run all unit tests and verify passing
  - Run all property-based tests (minimum 100 iterations each)
  - Run all integration tests
  - Verify code coverage meets targets (85%+ for unit tests)
  - Ask the user if questions arise

---

## Implementation Notes

- **Database Migrations:** Create migrations after all models are defined. Test migrations on a fresh database.
- **State Machine:** Maintain a single source of truth for valid state transitions. Consider using a state machine library if complexity grows.
- **BUFIA Share Calculation:** Use integer division (`//`) to ensure floor operation. Always verify invariant: `bufia_share + member_share == total_sacks`.
- **Audit Trail:** Every state change must create a RentalStateChange record. This is critical for dispute resolution.
- **Notifications:** Integrate with existing UserNotification system. Ensure correct recipient selection (member vs admin vs operator).
- **Testing:** Property tests should use `hypothesis` library with minimum 100 iterations. Each property test should be independent and repeatable.
- **Error Handling:** Use Django's ValidationError for validation failures. Return descriptive error messages to users.
- **Performance:** Add database indexes on frequently queried fields (rental, admin, timestamps).

---

## Files to Create/Modify

**Models:**
- `machines/models.py` - Add Rental fields, HarvestReport, Settlement, RentalStateChange models

**Business Logic:**
- `machines/utils.py` - Add all business logic functions (create_rental_request, approve_rental, etc.)

**Views:**
- `machines/views.py` - Add member views (rental request, detail, list)
- `machines/admin_views.py` - Update admin dashboard and harvest verification interface

**Forms:**
- `machines/forms.py` - Add RentalRequestForm

**Signals/Notifications:**
- `machines/signals.py` - Add signal handlers for state transitions and notifications

**Templates:**
- `templates/machines/rental_request_form.html` - New rental request form template
- `templates/machines/rental_detail.html` - Update with workflow state and settlement info
- `templates/machines/rental_list.html` - New member rental list template
- `templates/machines/admin_rental_dashboard.html` - Update with pending approvals and harvest verification

**Tests:**
- `tests/test_in_kind_workflow.py` - Unit tests for all business logic
- `tests/test_in_kind_properties.py` - Property-based tests for all 12 correctness properties
- `tests/test_in_kind_integration.py` - Integration tests for complete workflows

**Migrations:**
- `machines/migrations/000X_add_in_kind_workflow.py` - Auto-generated migration file
