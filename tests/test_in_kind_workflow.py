"""
Unit tests for IN-KIND Equipment Rental Workflow
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from machines.models import Machine, Rental, HarvestReport, Settlement, RentalStateChange
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


class BUFIAShareCalculationTests(TestCase):
    """Test BUFIA share calculation with 9:1 ratio"""
    
    def test_calculate_bufia_share_basic(self):
        """Test basic BUFIA share calculation"""
        bufia, member = calculate_bufia_share(9)
        self.assertEqual(int(bufia), 1)
        self.assertEqual(int(member), 8)
    
    def test_calculate_bufia_share_invariant(self):
        """Test that bufia_share + member_share = total"""
        test_cases = [9, 18, 90, 100, 1000]
        for total in test_cases:
            bufia, member = calculate_bufia_share(total)
            self.assertEqual(int(bufia) + int(member), total)
    
    def test_calculate_bufia_share_floor_operation(self):
        """Test that floor operation is used correctly"""
        bufia, member = calculate_bufia_share(100)
        self.assertEqual(int(bufia), 11)  # floor(100/9) = 11
        self.assertEqual(int(member), 89)
    
    def test_calculate_bufia_share_invalid_zero(self):
        """Test that zero sacks raises error"""
        with self.assertRaises(ValidationError):
            calculate_bufia_share(0)
    
    def test_calculate_bufia_share_invalid_negative(self):
        """Test that negative sacks raises error"""
        with self.assertRaises(ValidationError):
            calculate_bufia_share(-10)


class RentalRequestCreationTests(TestCase):
    """Test rental request creation and validation"""
    
    def setUp(self):
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
    
    def test_create_rental_request_valid(self):
        """Test creating a valid rental request"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        # Set machine to support in_kind rentals
        self.machine.rental_price_type = 'in_kind'
        self.machine.save()
        
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        self.assertEqual(rental.workflow_state, 'requested')
        self.assertEqual(rental.payment_type, 'in_kind')
        self.assertEqual(rental.settlement_status, 'pending')
        self.assertEqual(rental.user, self.member)
        self.assertEqual(rental.machine, self.machine)
    
    def test_create_rental_request_creates_state_change(self):
        """Test that state change record is created"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        rental = create_rental_request(self.member, self.machine, start_date, harvest_date)
        
        state_changes = RentalStateChange.objects.filter(rental=rental)
        self.assertEqual(state_changes.count(), 1)
        self.assertEqual(state_changes.first().to_state, 'requested')
    
    def test_validate_rental_request_invalid_equipment(self):
        """Test validation with non-existent equipment"""
        start_date = date.today() + timedelta(days=1)
        harvest_date = start_date + timedelta(days=30)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(99999, start_date, harvest_date)
    
    def test_validate_rental_request_past_date(self):
        """Test validation with past start date"""
        start_date = date.today() - timedelta(days=1)
        harvest_date = date.today() + timedelta(days=30)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(self.machine.id, start_date, harvest_date)
    
    def test_validate_rental_request_invalid_harvest_date(self):
        """Test validation with harvest date before start date"""
        start_date = date.today() + timedelta(days=30)
        harvest_date = start_date - timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            validate_rental_request(self.machine.id, start_date, harvest_date)


class StateTransitionTests(TestCase):
    """Test rental state transitions"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='requested',
            settlement_status='pending',
            status='pending'
        )
    
    def test_valid_state_transition(self):
        """Test valid state transition"""
        transition_rental_state(self.rental, 'pending_approval', self.admin)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'pending_approval')
    
    def test_invalid_state_transition(self):
        """Test invalid state transition"""
        with self.assertRaises(ValidationError):
            transition_rental_state(self.rental, 'completed', self.admin)
    
    def test_state_transition_creates_audit_record(self):
        """Test that state transition creates audit record"""
        transition_rental_state(self.rental, 'pending_approval', self.admin)
        
        state_changes = RentalStateChange.objects.filter(rental=self.rental)
        self.assertGreater(state_changes.count(), 0)
        
        latest_change = state_changes.latest('changed_at')
        self.assertEqual(latest_change.from_state, 'requested')
        self.assertEqual(latest_change.to_state, 'pending_approval')
        self.assertEqual(latest_change.changed_by, self.admin)


class RentalApprovalTests(TestCase):
    """Test rental approval workflow"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='requested',
            settlement_status='pending',
            status='pending'
        )
    
    def test_approve_rental_transitions_state(self):
        """Test that approve_rental transitions to approved"""
        approve_rental(self.rental, self.admin)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'approved')
    
    def test_approve_rental_creates_notification(self):
        """Test that approval creates notification"""
        approve_rental(self.rental, self.admin)
        
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_approved',
            related_object_id=self.rental.id
        ).first()
        self.assertIsNotNone(notification)
    
    def test_reject_rental_transitions_to_cancelled(self):
        """Test that reject_rental transitions to cancelled"""
        reject_rental(self.rental, self.admin, 'Equipment not available')
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'cancelled')
        self.assertEqual(self.rental.settlement_status, 'cancelled')


class EquipmentOperationTests(TestCase):
    """Test equipment operation tracking"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='approved',
            settlement_status='pending',
            status='approved'
        )
    
    def test_start_equipment_operation_transitions_state(self):
        """Test that start_equipment_operation transitions to in_progress"""
        start_equipment_operation(self.rental, self.admin)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'in_progress')
    
    def test_start_equipment_operation_records_handover_date(self):
        """Test that actual_handover_date is recorded"""
        start_equipment_operation(self.rental, self.admin)
        self.rental.refresh_from_db()
        self.assertIsNotNone(self.rental.actual_handover_date)
    
    def test_start_equipment_operation_creates_notification(self):
        """Test that operation start creates notification"""
        start_equipment_operation(self.rental, self.admin)
        
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_in_progress',
            related_object_id=self.rental.id
        ).first()
        self.assertIsNotNone(notification)


class HarvestReportTests(TestCase):
    """Test harvest report recording and verification"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='in_progress',
            settlement_status='pending',
            status='approved'
        )
    
    def test_record_harvest_report_creates_record(self):
        """Test that harvest report is created"""
        harvest_report = record_harvest_report(self.rental, 90, self.admin)
        
        self.assertIsNotNone(harvest_report)
        self.assertEqual(harvest_report.total_rice_sacks_harvested, 90)
        self.assertEqual(harvest_report.recorded_by_admin, self.admin)
    
    def test_record_harvest_report_calculates_shares(self):
        """Test that BUFIA and member shares are calculated"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        self.assertEqual(int(self.rental.bufia_share), 10)
        self.assertEqual(int(self.rental.member_share), 80)
    
    def test_record_harvest_report_transitions_state(self):
        """Test that state transitions to harvest_report_submitted"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        self.assertEqual(self.rental.workflow_state, 'harvest_report_submitted')
    
    def test_record_harvest_report_invalid_sacks(self):
        """Test that zero or negative sacks raises error"""
        with self.assertRaises(ValidationError):
            record_harvest_report(self.rental, 0, self.admin)
        
        with self.assertRaises(ValidationError):
            record_harvest_report(self.rental, -10, self.admin)
    
    def test_verify_harvest_report_creates_settlement(self):
        """Test that verification creates settlement"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        settlement = verify_harvest_report(self.rental, self.admin)
        
        self.assertIsNotNone(settlement)
        self.assertEqual(settlement.bufia_share, self.rental.bufia_share)
        self.assertEqual(settlement.member_share, self.rental.member_share)
    
    def test_verify_harvest_report_transitions_to_completed(self):
        """Test that verification transitions to completed"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        verify_harvest_report(self.rental, self.admin)
        self.rental.refresh_from_db()
        
        self.assertEqual(self.rental.workflow_state, 'completed')
        self.assertEqual(self.rental.settlement_status, 'paid')
    
    def test_reject_harvest_report_reverts_state(self):
        """Test that rejection reverts to in_progress"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        reject_harvest_report(self.rental, 'Recount needed', self.admin)
        self.rental.refresh_from_db()
        
        self.assertEqual(self.rental.workflow_state, 'in_progress')


class SettlementTests(TestCase):
    """Test settlement creation and finalization"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='in_progress',
            settlement_status='pending',
            status='approved'
        )
    
    def test_settlement_created_on_verification(self):
        """Test that settlement is created when harvest is verified"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        settlement = verify_harvest_report(self.rental, self.admin)
        
        self.assertIsNotNone(settlement)
        self.assertEqual(settlement.rental, self.rental)
    
    def test_settlement_has_unique_reference(self):
        """Test that settlement reference is unique"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        settlement = verify_harvest_report(self.rental, self.admin)
        
        self.assertIsNotNone(settlement.settlement_reference)
        self.assertTrue(settlement.settlement_reference.startswith('SETTLE-'))
    
    def test_settlement_finalization_creates_notification(self):
        """Test that settlement finalization creates notification"""
        record_harvest_report(self.rental, 90, self.admin)
        self.rental.refresh_from_db()
        
        verify_harvest_report(self.rental, self.admin)
        
        notification = UserNotification.objects.filter(
            user=self.member,
            notification_type='settlement_finalized',
            related_object_id=self.rental.id
        ).first()
        self.assertIsNotNone(notification)


class AuditTrailTests(TestCase):
    """Test audit trail recording"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@test.com',
            password='testpass123'
        )
        self.machine = Machine.objects.create(
            name='Harvester 1',
            machine_type='harvester',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            payment_type='in_kind',
            workflow_state='requested',
            settlement_status='pending',
            status='pending'
        )
    
    def test_audit_trail_records_all_transitions(self):
        """Test that all state transitions are recorded"""
        approve_rental(self.rental, self.admin)
        self.rental.refresh_from_db()
        start_equipment_operation(self.rental, self.admin)
        
        state_changes = RentalStateChange.objects.filter(rental=self.rental).order_by('changed_at')
        
        # Should have at least 3 changes: requested->pending_approval, pending_approval->approved, approved->in_progress
        self.assertGreaterEqual(state_changes.count(), 3)
    
    def test_audit_trail_has_complete_information(self):
        """Test that audit records have all required fields"""
        transition_rental_state(self.rental, 'pending_approval', self.admin, reason='Test reason')
        
        state_change = RentalStateChange.objects.filter(rental=self.rental).first()
        
        self.assertIsNotNone(state_change.from_state)
        self.assertIsNotNone(state_change.to_state)
        self.assertIsNotNone(state_change.changed_at)
        self.assertIsNotNone(state_change.changed_by)
        self.assertEqual(state_change.reason, 'Test reason')
