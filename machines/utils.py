"""
Utility functions for machine rental availability checking and management
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Rental, Machine, Maintenance, HarvestReport, Settlement, RentalStateChange


class AvailabilityChecker:
    """Utility class for checking machine availability with race condition protection"""
    
    @staticmethod
    def get_available_dates(machine, start_date=None, end_date=None):
        """
        Get list of blocked periods for a machine
        
        Args:
            machine: Machine instance
            start_date: Start date for checking (default: today)
            end_date: End date for checking (default: 90 days from start)
            
        Returns:
            List of dictionaries with blocked period information
        """
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=90)
        
        blocked_periods = []
        
        # Add rental periods (both approved and pending)
        rentals = Rental.objects.filter(
            machine=machine,
            status__in=['approved', 'pending'],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).order_by('start_date')
        
        for rental in rentals:
            blocked_periods.append({
                'start': rental.start_date,
                'end': rental.end_date,
                'type': 'rental',
                'status': rental.status,
                'user': rental.user.get_full_name() if rental.user else 'Unknown'
            })
        
        # Add maintenance periods
        maintenances = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        ).order_by('start_date')
        
        for maintenance in maintenances:
            end = maintenance.end_date.date() if maintenance.end_date else maintenance.start_date.date()
            blocked_periods.append({
                'start': maintenance.start_date.date(),
                'end': end,
                'type': 'maintenance',
                'status': maintenance.status,
                'description': maintenance.description
            })
        
        return blocked_periods
    
    @staticmethod
    @transaction.atomic
    def check_availability(machine, start_date, end_date, user=None, exclude_rental_id=None):
        """
        Check if machine is available for the given date range with database locking
        
        Args:
            machine: Machine instance
            start_date: Rental start date
            end_date: Rental end date
            user: User making the request (optional)
            exclude_rental_id: Rental ID to exclude from check (for updates)
            
        Returns:
            Tuple of (is_available: bool, message: str)
        """
        # Validate dates
        today = timezone.now().date()
        
        if start_date < today:
            return False, "Start date cannot be in the past"
        
        if end_date < start_date:
            return False, "End date must be after start date"
        
        # Maximum rental period check (30 days)
        if (end_date - start_date).days > 30:
            return False, "Rental period cannot exceed 30 days"
        
        # Check machine status
        if machine.status == 'maintenance':
            return False, "Machine is currently under maintenance"
        
        # Use select_for_update to lock the rows we're checking (prevents race conditions)
        overlapping_rentals = Rental.objects.select_for_update().filter(
            machine=machine,
            status__in=['approved', 'pending'],  # Check both approved AND pending
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if exclude_rental_id:
            overlapping_rentals = overlapping_rentals.exclude(id=exclude_rental_id)
        
        if overlapping_rentals.exists():
            conflict = overlapping_rentals.first()
            return False, (
                f"Machine is already booked from {conflict.start_date} to {conflict.end_date}. "
                f"Status: {conflict.get_status_display()}"
            )
        
        # Check maintenance schedule
        maintenance_conflicts = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        )
        
        if maintenance_conflicts.exists():
            maintenance = maintenance_conflicts.first()
            end_date_str = maintenance.end_date.date() if maintenance.end_date else maintenance.start_date.date()
            return False, (
                f"Machine has scheduled maintenance from "
                f"{maintenance.start_date.date()} to {end_date_str}"
            )
        
        return True, "Machine is available for the selected dates"
    
    @staticmethod
    def get_next_available_date(machine, preferred_start_date=None):
        """
        Find the next available date for a machine
        
        Args:
            machine: Machine instance
            preferred_start_date: Preferred start date (default: today)
            
        Returns:
            Next available date or None if not available in next 90 days
        """
        if not preferred_start_date:
            preferred_start_date = timezone.now().date()
        
        # Get all blocked periods for next 90 days
        blocked_periods = AvailabilityChecker.get_available_dates(
            machine,
            start_date=preferred_start_date,
            end_date=preferred_start_date + timedelta(days=90)
        )
        
        # Sort by start date
        blocked_periods.sort(key=lambda x: x['start'])
        
        # Find first gap
        current_date = preferred_start_date
        for period in blocked_periods:
            if current_date < period['start']:
                return current_date
            current_date = max(current_date, period['end'] + timedelta(days=1))
        
        # If we've checked all blocked periods and current_date is still reasonable
        if (current_date - preferred_start_date).days <= 90:
            return current_date
        
        return None



# IN-KIND Rental Workflow Utilities

def validate_rental_request(equipment_id, start_date, harvest_date):
    """
    Validate rental request data before creating a rental.
    
    Args:
        equipment_id: Machine ID
        start_date: Rental start date
        harvest_date: Expected harvest date
        
    Raises:
        ValidationError: If validation fails
    """
    from datetime import date
    
    # Check equipment exists
    try:
        machine = Machine.objects.get(id=equipment_id)
    except Machine.DoesNotExist:
        raise ValidationError("Equipment does not exist")
    
    # Check start_date not in past
    today = date.today()
    if start_date < today:
        raise ValidationError("Rental start date cannot be in the past")
    
    # Check harvest_date after start_date
    if harvest_date <= start_date:
        raise ValidationError(
            "Expected harvest date must be after rental start date"
        )


def create_rental_request(member, equipment, start_date, harvest_date):
    """
    Create a new IN-KIND rental request.
    
    Args:
        member: User instance (member requesting rental)
        equipment: Machine instance
        start_date: Rental start date
        harvest_date: Expected harvest date
        
    Returns:
        Rental instance with workflow_state='requested'
        
    Raises:
        ValidationError: If validation fails
    """
    # Validate input
    validate_rental_request(equipment.id, start_date, harvest_date)
    
    # Create rental
    rental = Rental.objects.create(
        machine=equipment,
        user=member,
        start_date=start_date,
        end_date=harvest_date,
        payment_type='in_kind',
        workflow_state='requested',
        settlement_status='pending',
        status='pending'
    )
    
    # Record initial state change
    RentalStateChange.objects.create(
        rental=rental,
        from_state='',
        to_state='requested',
        changed_by=None,
        reason='Initial rental request creation'
    )
    
    return rental


def transition_rental_state(rental, new_state, admin, reason=''):
    """
    Transition rental to a new workflow state with validation.
    
    Args:
        rental: Rental instance
        new_state: Target workflow state
        admin: User making the transition (admin)
        reason: Reason for transition
        
    Returns:
        Rental instance with updated state
        
    Raises:
        ValidationError: If transition is invalid
    """
    # Valid state transitions
    VALID_TRANSITIONS = {
        'requested': ['pending_approval', 'cancelled'],
        'pending_approval': ['approved', 'cancelled'],
        'approved': ['in_progress', 'cancelled'],
        'in_progress': ['harvest_report_submitted', 'completed', 'cancelled'],
        'harvest_report_submitted': ['completed', 'in_progress', 'cancelled'],
        'completed': ['cancelled'],
        'cancelled': [],
    }
    
    current_state = rental.workflow_state
    
    # Check if transition is valid
    if new_state not in VALID_TRANSITIONS.get(current_state, []):
        raise ValidationError(
            f"Cannot transition from '{current_state}' to '{new_state}'"
        )
    
    # Record state change
    RentalStateChange.objects.create(
        rental=rental,
        from_state=current_state,
        to_state=new_state,
        changed_by=admin,
        reason=reason
    )
    
    # Update rental
    rental.workflow_state = new_state
    rental.state_changed_by = admin
    rental.state_changed_at = timezone.now()
    rental.save()
    
    return rental


def calculate_bufia_share(total_sacks):
    """
    Calculate BUFIA share using 9:1 ratio.
    
    Args:
        total_sacks: Total rice sacks harvested
        
    Returns:
        Tuple of (bufia_share, member_share)
        
    Raises:
        ValidationError: If total_sacks <= 0
    """
    from decimal import Decimal
    
    if total_sacks <= 0:
        raise ValidationError("Total sacks must be greater than zero")
    
    total = Decimal(str(total_sacks))
    bufia_share = int(total // 9)
    member_share = int(total - bufia_share)
    
    # Verify invariant
    if bufia_share + member_share != int(total):
        raise ValidationError("BUFIA share calculation failed invariant check")
    
    return Decimal(str(bufia_share)), Decimal(str(member_share))


def approve_rental(rental, admin):
    """
    Approve a rental request (transition requested → pending_approval → approved).
    
    Args:
        rental: Rental instance in 'requested' state
        admin: Admin user approving the rental
        
    Returns:
        Rental instance with workflow_state='approved'
        
    Raises:
        ValidationError: If rental not in 'requested' state
    """
    if rental.workflow_state != 'requested':
        raise ValidationError(
            f"Can only approve rentals in 'requested' state, "
            f"current state: {rental.workflow_state}"
        )
    
    # Transition to pending_approval
    transition_rental_state(
        rental,
        'pending_approval',
        admin,
        reason='Admin initiated approval process'
    )
    
    # Transition to approved
    rental.refresh_from_db()
    transition_rental_state(
        rental,
        'approved',
        admin,
        reason='Admin approved rental request'
    )
    
    # Trigger notification
    notify_rental_approved(rental)
    
    return rental


def reject_rental(rental, admin, reason=''):
    """
    Reject a rental request (transition to cancelled).
    
    Args:
        rental: Rental instance
        admin: Admin user rejecting the rental
        reason: Reason for rejection
        
    Returns:
        Rental instance with workflow_state='cancelled'
    """
    transition_rental_state(
        rental,
        'cancelled',
        admin,
        reason=reason or 'Admin rejected rental request'
    )
    
    rental.settlement_status = 'cancelled'
    rental.save()
    
    return rental


def start_equipment_operation(rental, admin):
    """
    Start equipment operation (transition approved → in_progress).
    
    Args:
        rental: Rental instance in 'approved' state
        admin: Admin user starting operation
        
    Returns:
        Rental instance with workflow_state='in_progress'
        
    Raises:
        ValidationError: If rental not in 'approved' state
    """
    if rental.workflow_state != 'approved':
        raise ValidationError(
            f"Can only start operation for approved rentals, "
            f"current state: {rental.workflow_state}"
        )
    
    # Record handover date
    rental.actual_handover_date = timezone.now()
    
    # Transition to in_progress
    transition_rental_state(
        rental,
        'in_progress',
        admin,
        reason='Equipment operation started'
    )
    
    rental.save()
    
    # Trigger notification
    notify_rental_in_progress(rental)
    
    return rental


def record_harvest_report(rental, total_sacks, admin):
    """
    Record harvest report from operator (transition in_progress → harvest_report_submitted).
    
    Args:
        rental: Rental instance in 'in_progress' state
        total_sacks: Total rice sacks harvested
        admin: Admin user recording the report
        
    Returns:
        HarvestReport instance
        
    Raises:
        ValidationError: If validation fails
    """
    from .models import HarvestReport
    
    # Validate total_sacks
    if total_sacks <= 0:
        raise ValidationError("Total sacks harvested must be greater than zero")
    
    if rental.workflow_state != 'in_progress':
        raise ValidationError(
            f"Can only record harvest for in_progress rentals, "
            f"current state: {rental.workflow_state}"
        )
    
    # Calculate shares
    bufia_share, member_share = calculate_bufia_share(total_sacks)
    
    # Create harvest report
    harvest_report = HarvestReport.objects.create(
        rental=rental,
        total_rice_sacks_harvested=total_sacks,
        recorded_by_admin=admin
    )
    
    # Update rental with harvest data
    rental.total_rice_sacks_harvested = total_sacks
    rental.bufia_share = bufia_share
    rental.member_share = member_share
    
    # Transition to harvest_report_submitted
    transition_rental_state(
        rental,
        'harvest_report_submitted',
        admin,
        reason='Harvest report recorded from operator'
    )
    
    rental.save()
    
    return harvest_report


def verify_harvest_report(rental, admin, notes=''):
    """
    Verify harvest report and create settlement (transition harvest_report_submitted → completed).
    
    Args:
        rental: Rental instance in 'harvest_report_submitted' state
        admin: Admin user verifying the report
        notes: Verification notes
        
    Returns:
        Settlement instance
        
    Raises:
        ValidationError: If validation fails
    """
    from .models import Settlement
    
    if rental.workflow_state != 'harvest_report_submitted':
        raise ValidationError(
            f"Can only verify harvest for harvest_report_submitted rentals, "
            f"current state: {rental.workflow_state}"
        )
    
    # Get harvest report
    harvest_report = rental.harvest_reports.first()
    if not harvest_report:
        raise ValidationError("No harvest report found for this rental")
    
    # Mark harvest report as verified
    harvest_report.is_verified = True
    harvest_report.verified_at = timezone.now()
    harvest_report.verified_by = admin
    harvest_report.verification_notes = notes
    harvest_report.save()
    
    # Create settlement
    settlement_reference = f"SETTLE-{rental.id}-{timezone.now().timestamp()}"
    settlement = Settlement.objects.create(
        rental=rental,
        bufia_share=rental.bufia_share,
        member_share=rental.member_share,
        total_harvested=rental.total_rice_sacks_harvested,
        settlement_reference=settlement_reference,
        finalized_by=admin
    )
    
    # Transition to completed
    transition_rental_state(
        rental,
        'completed',
        admin,
        reason='Harvest report verified and settlement created'
    )
    
    rental.settlement_status = 'paid'
    rental.save()
    
    # Trigger notification
    notify_settlement_finalized(rental)
    
    return settlement


def reject_harvest_report(rental, reason, admin):
    """
    Reject harvest report (transition harvest_report_submitted → in_progress).
    
    Args:
        rental: Rental instance in 'harvest_report_submitted' state
        reason: Reason for rejection
        admin: Admin user rejecting the report
        
    Returns:
        Rental instance with workflow_state='in_progress'
        
    Raises:
        ValidationError: If validation fails
    """
    from .models import HarvestReport
    
    if rental.workflow_state != 'harvest_report_submitted':
        raise ValidationError(
            f"Can only reject harvest for harvest_report_submitted rentals, "
            f"current state: {rental.workflow_state}"
        )
    
    # Mark harvest report as rejected
    harvest_report = rental.harvest_reports.first()
    if harvest_report:
        harvest_report.is_rejected = True
        harvest_report.rejection_reason = reason
        harvest_report.rejection_timestamp = timezone.now()
        harvest_report.save()
    
    # Transition back to in_progress
    transition_rental_state(
        rental,
        'in_progress',
        admin,
        reason=f'Harvest report rejected: {reason}'
    )
    
    return rental


# Notification Functions

def notify_rental_approved(rental):
    """Send notification when rental is approved."""
    from notifications.models import UserNotification
    
    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_approved',
        message=f'Your rental request for {rental.machine.name} has been approved',
        related_object_id=rental.id
    )


def notify_rental_in_progress(rental):
    """Send notification when equipment operation begins."""
    from notifications.models import UserNotification
    
    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_in_progress',
        message=f'Equipment {rental.machine.name} is now in operation',
        related_object_id=rental.id
    )


def notify_settlement_finalized(rental):
    """Send notification when settlement is finalized."""
    from notifications.models import UserNotification
    
    UserNotification.objects.create(
        user=rental.user,
        notification_type='settlement_finalized',
        message=f'Your rental settlement for {rental.machine.name} is complete',
        related_object_id=rental.id
    )



def complete_rental_early(rental: Rental, admin, reason: str = '') -> Rental:
    """
    Mark a rental as completed early and make the machine available again.

    This function:
    - Sets workflow_state to 'completed'
    - Records actual_completion_time
    - Makes the machine available for new rentals
    - Preserves the rental record for history/auditing

    Args:
        rental: Rental instance to complete
        admin: User (admin) performing the action
        reason: Reason for early completion

    Returns:
        Updated Rental instance

    Raises:
        ValidationError: If rental cannot be completed early
    """
    from django.core.exceptions import ValidationError

    # Only rentals in 'in_progress' state can be completed early
    if rental.workflow_state != 'in_progress':
        raise ValidationError(
            f'Can only complete early rentals in in_progress state. '
            f'Current state: {rental.workflow_state}'
        )

    # Record the state change
    RentalStateChange.objects.create(
        rental=rental,
        from_state='in_progress',
        to_state='completed',
        changed_by=admin,
        reason=reason or 'Early completion by admin'
    )

    # Update rental
    rental.workflow_state = 'completed'
    rental.status = 'completed'
    rental.actual_completion_time = timezone.now()
    rental.state_changed_by = admin
    rental.state_changed_at = timezone.now()
    rental.save()
    rental.sync_machine_status()

    return rental


def calculate_bufia_share(total_sacks):
    """Calculate BUFIA and member shares using the rounded 1/9 harvest rule."""
    from decimal import Decimal, ROUND_HALF_UP

    if total_sacks <= 0:
        raise ValidationError("Total sacks must be greater than zero")

    total = Decimal(str(total_sacks))
    bufia_share = (total / Decimal('9')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    member_share = (total - bufia_share).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return bufia_share, member_share


def start_equipment_operation(rental, admin):
    """Start equipment operation and mark the machine as in use."""
    if rental.workflow_state != 'approved':
        raise ValidationError(
            f"Can only start operation for approved rentals, current state: {rental.workflow_state}"
        )

    rental.actual_handover_date = timezone.now()
    transition_rental_state(
        rental,
        'in_progress',
        admin,
        reason='Equipment operation started'
    )
    rental.machine.status = 'rented'
    rental.machine.save(update_fields=['status'])

    notify_rental_in_progress(rental)
    return rental


def record_harvest_report(rental, total_sacks, admin):
    """Record harvest data, compute rounded shares, and move to settlement."""
    from .models import HarvestReport

    if total_sacks <= 0:
        raise ValidationError("Total sacks harvested must be greater than zero")
    if rental.workflow_state != 'in_progress':
        raise ValidationError(
            f"Can only record harvest for in_progress rentals, current state: {rental.workflow_state}"
        )

    bufia_share, member_share = calculate_bufia_share(total_sacks)
    harvest_report = HarvestReport.objects.create(
        rental=rental,
        total_rice_sacks_harvested=total_sacks,
        recorded_by_admin=admin
    )

    rental.total_harvest_sacks = total_sacks
    rental.total_rice_sacks_harvested = total_sacks
    rental.bufia_share = bufia_share
    rental.member_share = member_share
    rental.organization_share_required = bufia_share
    rental.payment_status = 'pending'
    rental.settlement_status = 'waiting_for_delivery'

    transition_rental_state(
        rental,
        'harvest_report_submitted',
        admin,
        reason='Harvest report recorded from operator'
    )
    rental.save()
    return harvest_report
