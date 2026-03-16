"""
Property-based tests for IN-KIND Equipment Rental Workflow (Simplified)

These tests verify the 12 correctness properties with reduced hypothesis examples
for faster execution while maintaining comprehensive coverage.

Feature: in-kind-rental-workflow
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from machines.models import (
    Machine, Rental, HarvestReport, Settlement, RentalStateChange
)
from machines.utils import (
    validate_rental_request,
    create_rental_request,
    transition_rental_state,
    calculate_bufia_share,
    approve_rental,
    reject_rental,
    start_equipment_operation,
    record_harvest_report,
    verify_harvest_report,
    reject_harvest_report,
)
from notifications.models import UserNotification

User = get_user_model()


class PropertyBasedTestsSimplified(TestCase):
    """Simplified property-based tests for IN-KIND workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.member = User.objects.create_user(
            username='member_test',
            email='member@test.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.machine = Machine.objects.create(
            name='Test Machine',
            machine_type='harvester',
            status='available',
            rental_price_type='in_kind'
        )
    
    # ========================================================================
    # Property 1: Rental Request Creation with Correct Initial State
    # ========================================================================
    
    def test_property_1_rental_request_creation_basic(self):
        """Property 1: Basic rental request creation"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        assert rental.workflow_state == 'requested'
        assert rental.payment_type == 'in_kind'
        assert rental.settlement_status == 'pending'
        assert rental.machine_id == self.machine.id
        assert rental.user_id == self.member.id
    
    def test_property_1_rental_request_creation_various_dates(self):
        """Property 1: Rental request with various date ranges"""
        test_cases = [
            (1, 30),    # 1 day from now, 30 days harvest
            (7, 60),    # 1 week from now, 60 days harvest
            (30, 365),  # 30 days from now, 1 year harvest
        ]
        
        for offset, duration in test_cases:
            start_date = date.today() + timedelta(days=offset)
            harvest_date = start_date + timedelta(days=duration)
            
            rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
            
            assert rental.workflow_state == 'requested'
            assert rental.payment_type == 'in_kind'
            assert rental.settlement_status == 'pending'
    
    # ========================================================================
    # Property 2: Admin Approval State Transitions
    # ========================================================================
    
    def test_property_2_admin_approval_transitions(self):
        """Property 2: Admin approval creates correct state and notification"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        rental.refresh_from_db()
        
        assert rental.workflow_state == 'approved'
        
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_approved',
            related_object_id=rental.id
        ).first()
        assert notification is not None
    
    # ========================================================================
    # Property 3: Admin Rejection Sets Cancelled State
    # ========================================================================
    
    def test_property_3_admin_rejection_cancels(self):
        """Property 3: Admin rejection sets cancelled state"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        transition_rental_state(rental, 'pending_approval', self.admin)
        reject_rental(rental, self.admin, 'Equipment not available')
        rental.refresh_from_db()
        
        assert rental.workflow_state == 'cancelled'
        assert rental.settlement_status == 'cancelled'
    
    # ========================================================================
    # Property 4: Equipment Operation Tracking
    # ========================================================================
    
    def test_property_4_equipment_operation_tracking(self):
        """Property 4: Equipment operation records handover date and notification"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        start_equipment_operation(rental, self.admin)
        rental.refresh_from_db()
        
        assert rental.workflow_state == 'in_progress'
        assert rental.actual_handover_date is not None
        
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_in_progress',
            related_object_id=rental.id
        ).first()
        assert notification is not None
    
    # ========================================================================
    # Property 5: Harvest Report Recording and State Transition
    # ========================================================================
    
    def test_property_5_harvest_report_recording_various_amounts(self):
        """Property 5: Harvest report recording with various sack amounts"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        test_amounts = [1, 9, 90, 100, 1000]
        
        for amount in test_amounts:
            # Create new rental for each test
            rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
            approve_rental(rental, self.admin)
            start_equipment_operation(rental, self.admin)
            
            harvest_report = record_harvest_report(rental, amount, self.admin)
            rental.refresh_from_db()
            
            assert rental.workflow_state == 'harvest_report_submitted'
            assert harvest_report.total_rice_sacks_harvested == amount
            assert harvest_report.recorded_by_admin == self.admin
    
    # ========================================================================
    # Property 6: BUFIA Share Calculation Invariant
    # ========================================================================
    
    def test_property_6_bufia_share_calculation_invariant(self):
        """Property 6: BUFIA share calculation maintains invariant"""
        test_amounts = [1, 9, 18, 90, 100, 999, 1000, 9999, 10000]
        
        for total_sacks in test_amounts:
            bufia_share, member_share = calculate_bufia_share(total_sacks)
            
            # Verify calculation
            assert int(bufia_share) == total_sacks // 9
            
            # Verify invariant: bufia_share + member_share = total
            assert int(bufia_share) + int(member_share) == total_sacks
    
    # ========================================================================
    # Property 7: Harvest Report Verification Creates Settlement
    # ========================================================================
    
    def test_property_7_harvest_verification_creates_settlement(self):
        """Property 7: Harvest verification creates settlement"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        start_equipment_operation(rental, self.admin)
        record_harvest_report(rental, 90, self.admin)
        
        verify_harvest_report(rental, self.admin, 'Verified')
        rental.refresh_from_db()
        
        assert rental.workflow_state == 'completed'
        assert rental.settlement_status == 'paid'
        
        settlement = Settlement.objects.filter(rental=rental).first()
        assert settlement is not None
        assert settlement.bufia_share is not None
        assert settlement.member_share is not None
        assert settlement.settlement_date is not None
    
    # ========================================================================
    # Property 8: Harvest Report Rejection Reverts State
    # ========================================================================
    
    def test_property_8_harvest_rejection_reverts_state(self):
        """Property 8: Harvest rejection reverts to in_progress"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        start_equipment_operation(rental, self.admin)
        record_harvest_report(rental, 90, self.admin)
        
        reject_harvest_report(rental, 'Recount needed', self.admin)
        rental.refresh_from_db()
        
        assert rental.workflow_state == 'in_progress'
    
    # ========================================================================
    # Property 9: Rental Request Validation
    # ========================================================================
    
    def test_property_9_rental_validation_rejects_invalid_data(self):
        """Property 9: Validation rejects invalid rental data"""
        # Test 1: Non-existent equipment
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(99999, start_date, harvest_date)
        
        # Test 2: Past start date
        past_start = date.today() - timedelta(days=1)
        future_harvest = past_start + timedelta(days=30)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(self.machine.id, past_start, future_harvest)
        
        # Test 3: Harvest date before start date
        start = date.today() + timedelta(days=30)
        harvest = start - timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(self.machine.id, start, harvest)
    
    # ========================================================================
    # Property 10: Harvest Data Validation
    # ========================================================================
    
    def test_property_10_harvest_validation_rejects_invalid_sacks(self):
        """Property 10: Validation rejects invalid sack amounts"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        start_equipment_operation(rental, self.admin)
        
        # Test invalid amounts
        invalid_amounts = [0, -1, -100]
        
        for amount in invalid_amounts:
            with self.assertRaises(ValidationError):
                record_harvest_report(rental, amount, self.admin)
    
    # ========================================================================
    # Property 11: Audit Trail Completeness
    # ========================================================================
    
    def test_property_11_audit_trail_completeness(self):
        """Property 11: All state changes create complete audit records"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        approve_rental(rental, self.admin)
        
        state_changes = RentalStateChange.objects.filter(rental=rental)
        assert state_changes.count() > 0
        
        # Check that admin-initiated changes have changed_by populated
        admin_changes = state_changes.filter(changed_by__isnull=False)
        assert admin_changes.count() > 0
        
        for change in admin_changes:
            assert change.from_state is not None
            assert change.to_state is not None
            assert change.changed_at is not None
            assert change.changed_by is not None
    
    # ========================================================================
    # Property 12: Notification Delivery for Key Events
    # ========================================================================
    
    def test_property_12_notification_delivery_for_events(self):
        """Property 12: Key events create correct notifications"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        # Event 1: Rental request submitted
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        # Event 2: Rental approved
        approve_rental(rental, self.admin)
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_approved',
            related_object_id=rental.id
        ).first()
        assert notification is not None
        
        # Event 3: Equipment operation begins
        start_equipment_operation(rental, self.admin)
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_in_progress',
            related_object_id=rental.id
        ).first()
        assert notification is not None
