"""
Admin views for rental approval and payment verification
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Count, Case, When, Value, IntegerField
from decimal import Decimal
from datetime import timedelta
from django.core.exceptions import ValidationError

from .models import Rental, Machine, Maintenance, HarvestReport, Settlement, RentalPackage, RentalPackageItem
from .forms_enhanced import (
    AdminRentalApprovalForm,
    HarvestReportForm,
    ConfirmRiceReceivedForm,
    FaceToFacePaymentForm,
)
from notifications.models import UserNotification
from notifications.notification_helpers import create_notification
from notifications.operator_notifications import (
    notify_operator_job_assigned,
    notify_operator_job_updated,
    notify_operator_harvest_approved,
    notify_operator_job_completed,
)


User = get_user_model()


def _is_admin(user):
    """Check if user is admin or staff"""
    return user.is_staff or user.is_superuser


def _get_linked_rental_package(rental):
    try:
        package_item = rental.package_item
    except RentalPackageItem.DoesNotExist:
        return None
    return package_item.rental_package


def _sync_package_after_rental_update(rental):
    if not _get_linked_rental_package(rental):
        return None

    from .views import _sync_linked_package_after_rental_change

    return _sync_linked_package_after_rental_change(rental)


def _redirect_after_rental_action(request, rental):
    _sync_package_after_rental_update(rental)
    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


def _ensure_rental_payment_record(
    rental,
    *,
    status='pending',
    amount=None,
    paid_at=None,
    payment_provider=None,
    processed_by=None,
    amount_received=None,
    change_given=None,
):
    """Create or update the generic payment record linked to a rental."""
    from bufia.models import Payment
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(Rental)
    payment, _ = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=rental.id,
        defaults={
            'user': rental.user,
            'payment_type': 'rental',
            'amount': amount if amount is not None else (rental.payment_amount or 0),
            'currency': 'PHP',
            'status': status,
            'paid_at': paid_at,
        }
    )

    update_fields = []
    target_amount = amount if amount is not None else rental.payment_amount
    if payment.user_id != rental.user_id:
        payment.user = rental.user
        update_fields.append('user')
    if payment.payment_type != 'rental':
        payment.payment_type = 'rental'
        update_fields.append('payment_type')
    if target_amount is not None and payment.amount != target_amount:
        payment.amount = target_amount
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != status:
        payment.status = status
        update_fields.append('status')
    target_provider = payment_provider or ('paymongo' if rental.payment_method == 'online' else 'manual')
    if payment.payment_provider != target_provider:
        payment.payment_provider = target_provider
        update_fields.append('payment_provider')
    if paid_at and payment.paid_at != paid_at:
        payment.paid_at = paid_at
        update_fields.append('paid_at')
    if processed_by is not None and payment.processed_by_id != processed_by.id:
        payment.processed_by = processed_by
        update_fields.append('processed_by')
    if amount_received is not None and payment.amount_received != amount_received:
        payment.amount_received = amount_received
        update_fields.append('amount_received')
    if change_given is not None and payment.change_given != change_given:
        payment.change_given = change_given
        update_fields.append('change_given')

    if update_fields:
        payment.save(update_fields=update_fields)
    return payment


def _mark_rental_in_progress_after_payment(rental, admin_user, *, payment_status='paid'):
    """Mark a paid non-in-kind rental as in progress after payment verification or recording."""
    rental.payment_verified = True
    rental.payment_status = payment_status
    rental.status = 'approved'
    rental.workflow_state = 'in_progress'
    rental.verification_date = timezone.now()
    rental.verified_by = admin_user
    rental.save(update_fields=[
        'payment_verified',
        'payment_status',
        'status',
        'workflow_state',
        'verification_date',
        'verified_by',
        'updated_at',
    ])
    rental.sync_machine_status()
    return rental


def _operator_acceptance_pending_for_completion(rental):
    """True when an assigned operator has not yet accepted the rental task."""
    return (
        rental.requires_operator_service
        and rental.assigned_operator_id is not None
        and rental.operator_status in {'unassigned', 'assigned'}
    )


def _can_admin_complete_paid_rental(rental):
    """Whether a paid rental is eligible for admin completion."""
    return (
        rental.payment_type != 'in_kind'
        and rental.payment_verified
        and rental.workflow_state == 'in_progress'
        and rental.status == 'approved'
        and (
            not rental.requires_operator_service
            or (
                rental.assigned_operator_id is not None
                and not _operator_acceptance_pending_for_completion(rental)
            )
        )
    )


def _build_purpose_details(purpose_text):
    """Split stored purpose text into label/value rows for cleaner display."""
    details = []
    if not purpose_text:
        return details

    for raw_line in str(purpose_text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ':' in line:
            label, value = line.split(':', 1)
            details.append({
                'label': label.strip() or 'Detail',
                'value': value.strip() or 'N/A',
            })
        else:
            details.append({
                'label': 'Note',
                'value': line,
            })
    return details


def _get_rental_payments_map(rentals):
    """Fetch linked payment records for a batch of rentals."""
    from bufia.models import Payment
    from django.contrib.contenttypes.models import ContentType

    rentals = list(rentals)
    if not rentals:
        return {}

    rental_ids = [rental.id for rental in rentals]
    rental_content_type = ContentType.objects.get_for_model(Rental)
    payments = Payment.objects.filter(
        content_type=rental_content_type,
        object_id__in=rental_ids,
    ).select_related('user', 'processed_by').prefetch_related('refunds')

    return {payment.object_id: payment for payment in payments}


def _hydrate_dashboard_rentals(rentals):
    """Attach payment, refund, and conflict metadata used by the admin dashboard."""
    rentals = list(rentals)
    payments_map = _get_rental_payments_map(rentals)

    for rental in rentals:
        payment_record = payments_map.get(rental.id)
        rental.payment_record = payment_record
        rental.refund_status_display = payment_record.refund_status if payment_record else 'Not Available'
        rental.refundable_balance = payment_record.refundable_balance if payment_record else Decimal('0.00')

        rental.dashboard_has_conflicts = False
        rental.dashboard_conflict_count = 0
        rental.dashboard_conflicts = []
        rental.dashboard_is_overdue = rental.workflow_state == 'overdue'
        rental.dashboard_is_conflict_review = rental.workflow_state == 'conflict_review'

        if rental.status in {'pending', 'approved'} and rental.workflow_state != 'cancelled':
            is_available, conflicts = Rental.check_availability_for_approval(
                rental.machine,
                rental.start_date,
                rental.end_date,
                exclude_rental_id=rental.id,
            )
            if not is_available:
                rental.dashboard_conflicts = list(conflicts)
                rental.dashboard_conflict_count = len(rental.dashboard_conflicts)
                rental.dashboard_has_conflicts = rental.dashboard_conflict_count > 0

    return rentals


def _refund_queue_items(rentals):
    """Return cancelled rentals that still have refundable payment balances."""
    hydrated_rentals = _hydrate_dashboard_rentals(rentals)
    return [
        rental for rental in hydrated_rentals
        if rental.payment_record and rental.payment_record.can_accept_refunds
    ]


def _auto_cancel_conflicting_pending_rentals(approved_rental, admin_user):
    """Cancel overlapping pending rentals after one request is approved."""
    conflicting_rentals = list(
        Rental.objects.select_for_update().select_related('machine', 'user').filter(
            machine=approved_rental.machine,
            status='pending',
            start_date__lte=approved_rental.end_date,
            end_date__gte=approved_rental.start_date,
        ).exclude(pk=approved_rental.pk)
    )

    if not conflicting_rentals:
        return []

    schedule_label = (
        f'{approved_rental.start_date:%B %d, %Y} to {approved_rental.end_date:%B %d, %Y}'
    )
    system_note = (
        f'Automatically cancelled due to conflict with approved rental #{approved_rental.id} '
        f'for {approved_rental.machine.name} ({schedule_label}).'
    )

    for conflicting in conflicting_rentals:
        conflicting.mark_cancelled(
            cancellation_type='auto_conflict',
            cancel_reason='Cancelled due to scheduling conflict with an approved rental.',
            system_note=system_note,
            admin_note=f'Conflict resolved automatically after approving rental #{approved_rental.id}.',
        )
        conflicting.state_changed_by = admin_user
        conflicting.save(update_fields=[
            'status',
            'workflow_state',
            'cancellation_type',
            'cancel_reason',
            'system_note',
            'follow_up_admin_note',
            'state_changed_by',
            'updated_at',
        ])
        
        UserNotification.objects.create(
            user=conflicting.user,
            notification_type='rental_conflict',
            message='Your booking was cancelled due to a conflict with an approved rental. Please choose whether you want a refund or reschedule.',
            related_object_id=conflicting.id
        )

    return conflicting_rentals


def _sync_rental_schedule_states():
    """Keep overdue and conflict-review workflow states aligned with today's schedule."""
    return Rental.sync_overdue_workflow_states()


def _append_system_note(rental, note):
    """Append operational notes to the existing system note log."""
    note = (note or '').strip()
    if not note:
        return
    if rental.system_note:
        rental.system_note = f'{rental.system_note}\n\n{note}'
    else:
        rental.system_note = note


def _get_safe_return_url(request, default_url):
    """Return a safe same-host redirect target from the request payload when available."""
    candidate = (request.POST.get('return_url') or request.GET.get('return_url') or '').strip()
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return default_url


def _approved_dashboard_q():
    """Approved tab: standard approved rentals waiting on payment or admin follow-up."""
    return Q(status='approved') & Q(workflow_state='approved') & ~Q(payment_type='in_kind')


def _completed_dashboard_q():
    """Completed tab: finalized, settled, rejected, or cancelled rentals."""
    return (
        Q(status='completed') |
        Q(workflow_state='completed') |
        Q(status='rejected') |
        Q(status='cancelled') |
        Q(settlement_status='paid')
    )


def _in_progress_dashboard_q():
    """In-progress tab: active work, including approved non-cash payment settlement flow."""
    return (
        Q(workflow_state='in_progress') |
        Q(workflow_state='overdue') |
        Q(workflow_state='conflict_review') |
        Q(workflow_state='harvest_report_submitted') |
        (
            Q(payment_type='in_kind') &
            Q(status='approved') &
            Q(workflow_state__in=['approved', 'overdue'])
        )
    ) & ~_completed_dashboard_q()


def _active_schedule_tracking_q():
    return ~_completed_dashboard_q()


def _pickup_tracking_q():
    return (
        _active_schedule_tracking_q() &
        Q(scheduled_pickup_at__isnull=False) &
        Q(actual_pickup_at__isnull=True)
    )


def _return_tracking_q():
    return (
        _active_schedule_tracking_q() &
        Q(scheduled_return_at__isnull=False) &
        Q(actual_return_at__isnull=True)
    )


def _parse_local_datetime_input(raw_value):
    if not raw_value:
        return None

    parsed = parse_datetime(raw_value)
    if parsed is None:
        raise ValueError('invalid_datetime')

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _build_conflict_dashboard_counts(*, base_queryset=None, today=None):
    today = today or timezone.localdate()
    rental_queryset = base_queryset if base_queryset is not None else Rental.objects.all()
    rental_queryset = rental_queryset.select_related('machine', 'user')

    all_approved = rental_queryset.filter(
        status='approved',
        end_date__gte=today,
    ).order_by('start_date')

    conflicts = []
    for rental in all_approved:
        is_available, overlapping = Rental.check_availability_for_approval(
            rental.machine,
            rental.start_date,
            rental.end_date,
            exclude_rental_id=rental.id,
        )
        if not is_available:
            conflicts.append({
                'rental': rental,
                'conflicts_with': list(overlapping),
            })

    pending_conflicts = []
    pending_rentals = rental_queryset.filter(
        status='pending',
        payment_verified=True,
    )
    for rental in pending_rentals:
        is_available, conf = Rental.check_availability_for_approval(
            rental.machine,
            rental.start_date,
            rental.end_date,
            exclude_rental_id=rental.id,
        )
        if not is_available:
            pending_conflicts.append({
                'rental': rental,
                'conflicts_with': list(conf),
            })

    conflict_review_rentals = list(
        rental_queryset.filter(
            workflow_state='conflict_review',
            status='approved',
        ).order_by('start_date', 'created_at')
    )

    unique_conflict_ids = (
        {row['rental'].id for row in conflicts}
        | {row['rental'].id for row in pending_conflicts}
        | {rental.id for rental in conflict_review_rentals}
    )

    return {
        'conflicts': conflicts,
        'pending_conflicts': pending_conflicts,
        'conflict_review_rentals': conflict_review_rentals,
        'conflict_review_count': len(conflict_review_rentals),
        'total_conflicts': len(conflicts),
        'total_pending_conflicts': len(pending_conflicts),
        'conflict_alert_count': len(unique_conflict_ids),
    }


@login_required
def admin_rental_dashboard(request):
    """Main admin dashboard grouped by the rental transaction workflow."""
    if not _is_admin(request.user):
        return redirect('machines:rental_list')

    synced_rental_ids = _sync_rental_schedule_states()

    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    date_filter = request.GET.get('date', 'all')
    renter_type_filter = request.GET.get('renter_type', 'all')
    search_query = request.GET.get('search', '').strip()
    active_tab = request.GET.get('tab', '').strip()

    if renter_type_filter not in {'all', 'member', 'non_member'}:
        renter_type_filter = 'all'

    # Package-linked rentals are managed from the package workflow screens,
    # not the direct admin rental dashboard, to keep queues separated.
    dashboard_rentals = Rental.objects.select_related('machine', 'user').filter(package_item__isnull=True)
    filtered_rentals = dashboard_rentals

    if status_filter and status_filter != 'all':
        filtered_rentals = filtered_rentals.filter(status=status_filter)

    if payment_filter == 'verified':
        filtered_rentals = filtered_rentals.filter(payment_verified=True)
    elif payment_filter == 'unverified':
        filtered_rentals = filtered_rentals.filter(payment_verified=False)
    elif payment_filter == 'online':
        filtered_rentals = filtered_rentals.filter(payment_method='online')
    elif payment_filter == 'face_to_face':
        filtered_rentals = filtered_rentals.filter(payment_method='face_to_face')
    elif payment_filter == 'in_kind':
        filtered_rentals = filtered_rentals.filter(payment_type='in_kind')

    if renter_type_filter == 'member':
        filtered_rentals = filtered_rentals.exclude(user__username='system')
    elif renter_type_filter == 'non_member':
        filtered_rentals = filtered_rentals.filter(user__username='system')

    # Date filter
    today = timezone.localdate()
    if date_filter == 'today':
        filtered_rentals = filtered_rentals.filter(
            Q(start_date=today) | Q(end_date=today) | 
            Q(start_date__lte=today, end_date__gte=today)
        )
    elif date_filter == 'tomorrow':
        tomorrow = today + timedelta(days=1)
        filtered_rentals = filtered_rentals.filter(
            Q(start_date=tomorrow) | Q(end_date=tomorrow) |
            Q(start_date__lte=tomorrow, end_date__gte=tomorrow)
        )
    elif date_filter == 'this_week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        filtered_rentals = filtered_rentals.filter(
            Q(start_date__lte=week_end, end_date__gte=week_start)
        )
    elif date_filter == 'this_month':
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        filtered_rentals = filtered_rentals.filter(
            Q(start_date__lte=month_end, end_date__gte=month_start)
        )

    if search_query:
        filtered_rentals = filtered_rentals.filter(
            Q(customer_name__icontains=search_query) |
            Q(customer_contact_number__icontains=search_query) |
            Q(customer_address__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(machine__name__icontains=search_query)
        )

    approved_dashboard_q = _approved_dashboard_q()
    in_progress_dashboard_q = _in_progress_dashboard_q()
    completed_dashboard_q = _completed_dashboard_q()

    tab_counts = {
        'pending': filtered_rentals.filter(status='pending').count(),
        'approved': filtered_rentals.filter(approved_dashboard_q).count(),
        'in_progress': filtered_rentals.filter(in_progress_dashboard_q).count(),
        'completed': filtered_rentals.filter(completed_dashboard_q).count(),
    }

    if active_tab not in tab_counts:
        if status_filter == 'pending':
            active_tab = 'pending'
        elif status_filter == 'approved':
            active_tab = 'approved'
        elif status_filter in ('completed', 'rejected', 'cancelled'):
            active_tab = 'completed'
        else:
            active_tab = next((tab for tab, count in tab_counts.items() if count > 0), 'pending')
    elif search_query and tab_counts.get(active_tab, 0) == 0:
        active_tab = next((tab for tab, count in tab_counts.items() if count > 0), active_tab)

    if active_tab == 'pending':
        rentals = filtered_rentals.filter(status='pending')
    elif active_tab == 'approved':
        rentals = filtered_rentals.filter(approved_dashboard_q)
    elif active_tab == 'in_progress':
        rentals = filtered_rentals.filter(in_progress_dashboard_q)
    else:
        rentals = filtered_rentals.filter(completed_dashboard_q)

    rentals = rentals.annotate(
        status_priority=Case(
            When(status='pending', then=Value(1)),
            When(in_progress_dashboard_q, then=Value(2)),
            When(approved_dashboard_q, then=Value(3)),
            When(status='completed', then=Value(4)),
            default=Value(5),
            output_field=IntegerField()
        )
    ).order_by('-created_at', 'status_priority')

    harvest_settlement_queue = Rental.objects.select_related('machine', 'user').filter(
        package_item__isnull=True,
        payment_type='in_kind'
    ).exclude(
        Q(settlement_status='paid') | Q(status='cancelled')
    ).filter(
        Q(workflow_state='harvest_report_submitted') |
        Q(organization_share_required__isnull=False) |
        Q(workflow_state='in_progress')
    ).order_by('-created_at')

    if renter_type_filter == 'member':
        harvest_settlement_queue = harvest_settlement_queue.exclude(user__username='system')
    elif renter_type_filter == 'non_member':
        harvest_settlement_queue = harvest_settlement_queue.filter(user__username='system')

    from django.core.paginator import Paginator
    paginator = Paginator(rentals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_obj.object_list = _hydrate_dashboard_rentals(page_obj.object_list)

    overdue_rentals = filtered_rentals.filter(workflow_state='overdue').order_by('end_date', 'start_date')
    conflict_counts = _build_conflict_dashboard_counts(base_queryset=filtered_rentals, today=today)
    package_requests = RentalPackage.objects.select_related('user', 'approved_by').prefetch_related('items').order_by('-created_at')
    refund_queue_count = len(_refund_queue_items(
        dashboard_rentals.filter(
            status='cancelled',
        ).exclude(
            payment_type='in_kind',
        ).order_by('-updated_at', '-created_at')
    ))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_filter': date_filter,
        'renter_type_filter': renter_type_filter,
        'search_query': search_query,
        'active_tab': active_tab,
        'tab_counts': tab_counts,
        'in_kind_verification_queue': harvest_settlement_queue[:10],
        'in_kind_verification_count': harvest_settlement_queue.count(),
        'overdue_rentals_count': overdue_rentals.count(),
        'conflict_review_rentals': conflict_counts['conflict_review_rentals'][:10],
        'conflict_review_count': conflict_counts['conflict_review_count'],
        'conflict_alert_count': conflict_counts['conflict_alert_count'],
        'refund_queue_count': refund_queue_count,
        'schedule_sync_count': len(synced_rental_ids),
        'today': timezone.localdate(),
        'package_requests': package_requests[:6],
        'package_total_count': package_requests.count(),
        'package_pending_count': package_requests.filter(status='pending').count(),
        'package_active_count': package_requests.exclude(status__in=['completed', 'cancelled']).count(),
    }

    return render(request, 'machines/admin/rental_dashboard.html', context)


@login_required
def admin_refund_queue(request):
    """Dedicated admin page for cancelled rentals that still need refund handling."""
    if not _is_admin(request.user):
        return redirect('machines:rental_list')

    refund_queue = _refund_queue_items(
        Rental.objects.select_related('machine', 'user').filter(
            package_item__isnull=True,
            status='cancelled',
        ).exclude(
            payment_type='in_kind',
        ).order_by('-updated_at', '-created_at')
    )

    requested_refunds = [rental for rental in refund_queue if rental.follow_up_action == 'refund_requested']
    total_refundable_balance = sum(
        (rental.payment_record.refundable_balance for rental in refund_queue if rental.payment_record),
        Decimal('0.00'),
    )

    context = {
        'refund_queue': refund_queue,
        'refund_queue_count': len(refund_queue),
        'requested_refund_count': len(requested_refunds),
        'pending_refund_review_count': len(refund_queue) - len(requested_refunds),
        'total_refundable_balance': total_refundable_balance,
    }
    return render(request, 'machines/admin/refund_queue.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_approve_rental_legacy_unused(request, rental_id):
    """
    Admin view to approve/reject rental with payment verification
    """
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )
    
    if request.method == 'POST':
        form = AdminRentalApprovalForm(request.POST, instance=rental)
        
        if form.is_valid():
            # Save the rental with updates
            rental = form.save(commit=False)
            rental.verified_by = request.user
            
            # Handle status changes
            if rental.status == 'completed':
                # Mark as completed and free up the machine
                rental.workflow_state = 'completed'
                rental.actual_completion_time = timezone.now()
                
                rental.machine.sync_status()
                
                # Notify user
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_completed',
                    message=f'Your rental for {rental.machine.name} has been marked as completed. Thank you for using BUFIA services!',
                    related_object_id=rental.id
                )
                
                messages.success(
                    request,
                    f'Rental marked as completed for {rental.customer_display_name} - {rental.machine.name}. '
                    f'Machine status is now {rental.machine.get_status_display().lower()}.'
                )
                
            elif rental.status == 'approved':
                # Ensure workflow state follows admin action
                if rental.workflow_state == 'requested':
                    rental.workflow_state = 'approved'
                
                # Notify user of approval
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_approved',
                    message=f'Your rental for {rental.machine.name} has been approved! '
                            f'Dates: {rental.start_date} to {rental.end_date}',
                    related_object_id=rental.id
                )
                
                messages.success(
                    request,
                    f'Rental approved for {rental.customer_display_name} - {rental.machine.name}'
                )
                
            elif rental.status == 'rejected':
                # Notify user of rejection
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_rejected',
                    message=f'Your rental request for {rental.machine.name} has been rejected. '
                            f'Please contact admin for more information.',
                    related_object_id=rental.id
                )
                
                messages.warning(
                    request,
                    f'Rental rejected for {rental.customer_display_name} - {rental.machine.name}'
                )
            
            elif rental.status == 'cancelled':
                # Handle cancellation
                rental.workflow_state = 'cancelled'
                
                rental.machine.sync_status()
                
                messages.info(
                    request,
                    f'Rental cancelled for {rental.customer_display_name} - {rental.machine.name}'
                )
            
            rental.save()
            return redirect('machines:rental_list')
    else:
        form = AdminRentalApprovalForm(instance=rental)
    
    # Check for conflicts
    is_available, conflicts = Rental.check_availability_for_approval(
        machine=rental.machine,
        start_date=rental.start_date,
        end_date=rental.end_date,
        exclude_rental_id=rental.id
    )
    
    context = {
        'rental': rental,
        'form': form,
        'has_conflicts': not is_available,
        'conflicts': conflicts if not is_available else None,
    }
    
    return render(request, 'machines/admin/rental_approval.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def submit_harvest_report(request, rental_id):
    """Step 4: record harvest and compute BUFIA share using machine-configured ratio."""
    rental = get_object_or_404(Rental.objects.select_for_update(), pk=rental_id)
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Harvest reporting applies only to non-cash payment rentals.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    form = HarvestReportForm(request.POST, instance=rental)
    if not form.is_valid():
        messages.error(request, 'Please provide a valid harvest value.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental = form.save(commit=False)
    rental.organization_share_required = rental.calculate_rice_share()
    rental.payment_status = 'to_be_determined'
    rental.settlement_status = 'waiting_for_delivery'
    rental.settlement_type = 'after_harvest'
    rental.save(update_fields=[
        'total_harvest_sacks', 'organization_share_required',
        'payment_status', 'settlement_status', 'settlement_type', 'updated_at'
    ])

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_received',
        message=(
            f'You are required to deliver {rental.organization_share_required} sack(s) of rice to BUFIA '
            f'for your {rental.machine.name} rental settlement '
            f'(share ratio {rental.machine.in_kind_farmer_share}:{rental.machine.in_kind_organization_share}).'
        ),
        related_object_id=rental.id
    )
    messages.success(request, f'Harvest report submitted. BUFIA share required: {rental.organization_share_required} sack(s).')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def confirm_rice_received(request, rental_id):
    """Step 5/6: admin confirms physical rice delivery and marks settlement paid with automatic completion."""
    rental = get_object_or_404(Rental.objects.select_for_update(), pk=rental_id)
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Rice confirmation applies only to non-cash payment rentals.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    form = ConfirmRiceReceivedForm(request.POST, instance=rental)
    if not form.is_valid():
        messages.error(request, 'Please provide received sacks.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental = form.save(commit=False)
    
    # Validate received amount
    if rental.organization_share_required and rental.organization_share_received < rental.organization_share_required:
        messages.error(request, 'Received sacks are less than required BUFIA share.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    # Check if delivered amount equals required BUFIA share for automatic completion
    auto_complete = False
    if rental.organization_share_required and rental.organization_share_received:
        from decimal import Decimal
        required = Decimal(str(rental.organization_share_required))
        received = Decimal(str(rental.organization_share_received))
        
        # Automatic completion if delivered equals required (with 0.01 tolerance)
        if abs(received - required) <= Decimal('0.01'):
            auto_complete = True

    rental.payment_status = 'paid_in_kind'
    rental.settlement_status = 'paid'
    rental.payment_verified = True
    rental.settlement_date = timezone.now()
    rental.settlement_reference = rental.generate_settlement_reference()
    rental.transaction_reference = rental.generate_transaction_reference()
    rental.verified_by = request.user
    rental.verification_date = timezone.now()
    
    # Automatic completion logic
    if auto_complete:
        rental.status = 'completed'
        rental.workflow_state = 'completed'
        rental.actual_completion_time = timezone.now()
        
        rental.machine.sync_status()
        
        rental.save(update_fields=[
            'organization_share_received', 'payment_status', 'settlement_status',
            'payment_verified', 'settlement_date', 'settlement_reference',
            'transaction_reference', 'verified_by', 'verification_date',
            'status', 'workflow_state', 'actual_completion_time', 'updated_at'
        ])
        
        UserNotification.objects.create(
            user=rental.user,
            notification_type='rental_completed',
            message=(
                f'Non-cash payment settlement completed for {rental.machine.name}. '
                f'Rice delivered: {rental.organization_share_received} sacks. '
                f'Reference: {rental.settlement_reference}. Rental is now completed.'
            ),
            related_object_id=rental.id
        )
        messages.success(
            request, 
            f'Rice delivery confirmed ({rental.organization_share_received} sacks). '
            f'Settlement marked as paid (non-cash payment). Rental automatically completed. '
            f'Machine {rental.machine.name} status is now {rental.machine.get_status_display().lower()}.'
        )
    else:
        rental.save(update_fields=[
            'organization_share_received', 'payment_status', 'settlement_status',
            'payment_verified', 'settlement_date', 'settlement_reference',
            'transaction_reference', 'verified_by', 'verification_date', 'updated_at'
        ])
        
        UserNotification.objects.create(
            user=rental.user,
            notification_type='rental_payment_completed',
            message=(
                f'Non-cash payment settlement confirmed for {rental.machine.name}. '
                f'Reference: {rental.settlement_reference}.'
            ),
            related_object_id=rental.id
        )
        messages.success(request, 'Rice delivery confirmed and settlement marked as paid (non-cash payment).')
    
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
def view_payment_proof(request, rental_id):
    """
    View payment proof file
    """
    rental = get_object_or_404(Rental, pk=rental_id)
    
    if not rental.payment_slip:
        raise Http404("No payment proof uploaded")
    
    try:
        return FileResponse(
            rental.payment_slip.open('rb'),
            content_type='application/octet-stream'
        )
    except Exception as e:
        messages.error(request, f'Error opening file: {str(e)}')
        return redirect('machines:rental_list')


@login_required
@user_passes_test(_is_admin)
def verify_payment_ajax(request, rental_id):
    """
    AJAX endpoint to quickly verify payment
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)
    
    try:
        rental = Rental.objects.get(pk=rental_id)
        
        # Toggle payment verification
        rental.payment_verified = not rental.payment_verified
        if rental.payment_verified:
            rental.verification_date = timezone.now()
            rental.verified_by = request.user
            if rental.payment_type == 'cash':
                rental.payment_status = 'paid'
        else:
            rental.verification_date = None
            rental.verified_by = None
            if rental.payment_type == 'cash':
                rental.payment_status = 'pending'
        
        rental.save()
        
        return JsonResponse({
            'success': True,
            'verified': rental.payment_verified,
            'message': 'Payment verified' if rental.payment_verified else 'Payment unverified'
        })
        
    except Rental.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rental not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_approve_rental(request, rental_id):
    """Approve, reject, or manually complete a rental request."""
    _sync_rental_schedule_states()
    rental = (
        Rental.objects.select_for_update()
        .select_related('machine', 'user', 'assigned_operator', 'package_item__rental_package')
        .filter(pk=rental_id)
        .first()
    )
    if rental is None:
        messages.error(
            request,
            f'Rental #{rental_id} could not be found. It may have already been removed.'
        )
        return redirect('machines:admin_rental_dashboard')
    source = request.POST.get('source') or request.GET.get('source') or ''
    return_url = request.POST.get('return_url') or request.GET.get('return_url') or ''
    report_origin = source == 'reports_rental' and return_url.startswith('/reports/rental/')
    dashboard_origin = source == 'admin_dashboard' and return_url.startswith('/machines/admin/dashboard/')
    overdue_origin = source == 'overdue_rentals' and return_url.startswith('/machines/admin/overdue-rentals/')

    if request.method == 'POST':
        if (
            request.POST.get('status') == 'completed'
            and rental.requires_operator_service
            and rental.assigned_operator_id is None
        ):
            messages.error(
                request,
                'Assign an operator before marking this rental as completed.'
            )
            return redirect('machines:admin_approve_rental', rental_id=rental.id)
        if (
            request.POST.get('status') == 'completed'
            and _operator_acceptance_pending_for_completion(rental)
        ):
            messages.error(
                request,
                'The assigned operator must accept the task before this rental can be marked as completed.'
            )
            return redirect('machines:admin_approve_rental', rental_id=rental.id)

        form = AdminRentalApprovalForm(request.POST, instance=rental)
        if form.is_valid():
            rental = form.save(commit=False)

            try:
                if rental.status == 'approved':
                    rental.workflow_state = 'approved'
                    rental.verified_by = None
                    rental.verification_date = None
                    rental.cancellation_type = ''
                    rental.cancel_reason = ''
                    rental.system_note = ''
                    rental.follow_up_action = 'none'
                    rental.follow_up_requested_at = None
                    rental.follow_up_resolved_at = None
                    rental.follow_up_admin_note = ''
                    if rental.payment_type == 'in_kind':
                        rental.payment_status = 'pending'
                        rental.settlement_type = 'after_harvest'
                        rental.settlement_status = (
                            'waiting_for_delivery'
                            if rental.organization_share_required and rental.organization_share_required > 0
                            else 'pending'
                        )
                        success_message = (
                            f'Rental approved for {rental.customer_display_name} - {rental.machine.name}. '
                            'In-kind settlement is now in progress and will be completed after harvest and rice delivery.'
                        )
                    else:
                        # Preserve the original payment method (online/face_to_face)
                        # Don't force it to face_to_face
                        if rental.payment_status == 'to_be_determined':
                            rental.payment_status = 'pending'
                            
                        # Use appropriate success message based on payment method
                        if rental.payment_method == 'online':
                            success_message = (
                                f'Rental approved for {rental.customer_display_name} - {rental.machine.name}. '
                                'Waiting for GCash payment verification.'
                            )
                        else:
                            success_message = (
                                f'Rental approved for {rental.customer_display_name} - {rental.machine.name}. '
                                'Waiting for over-the-counter payment recording.'
                            )

                    rental.save()
                    if rental.payment_type != 'in_kind':
                        _ensure_rental_payment_record(rental, status='pending', amount=rental.payment_amount)

                    auto_cancelled = _auto_cancel_conflicting_pending_rentals(rental, request.user)

                    UserNotification.objects.create(
                        user=rental.user,
                        notification_type='rental_approved',
                        message=(
                            f'Your rental for {rental.machine.name} has been approved. '
                            f'Payment type: {rental.workflow_payment_type_display}.'
                        ),
                        related_object_id=rental.id
                    )
                    if auto_cancelled:
                        success_message = (
                            f'{success_message} {len(auto_cancelled)} overlapping pending request'
                            f'{"s were" if len(auto_cancelled) != 1 else " was"} automatically cancelled.'
                        )
                    messages.success(request, success_message)

                elif rental.status == 'completed':
                    rental.status = 'completed'
                    rental.payment_verified = True
                    rental.payment_status = 'paid'
                    rental.workflow_state = 'completed'
                    rental.actual_completion_time = timezone.now()
                    update_fields = [
                        'status',
                        'payment_verified',
                        'payment_status',
                        'workflow_state',
                        'actual_completion_time',
                        'updated_at',
                    ]
                    if rental.assigned_operator_id and rental.operator_status != 'completed':
                        rental.operator_status = 'completed'
                        update_fields.append('operator_status')
                    rental.save(update_fields=update_fields)
                    rental.sync_machine_status()
                    UserNotification.objects.create(
                        user=rental.user,
                        notification_type='rental_completed',
                        message=f'Your rental for {rental.machine.name} has been marked as completed.',
                        related_object_id=rental.id
                    )
                    messages.success(
                        request,
                        f'Rental marked as completed for {rental.customer_display_name} - {rental.machine.name}.'
                    )

                elif rental.status == 'rejected':
                    rental.workflow_state = 'cancelled'
                    rental.save()
                    rental.sync_machine_status()
                    UserNotification.objects.create(
                        user=rental.user,
                        notification_type='rental_rejected',
                        message=(
                            f'Your rental request for {rental.machine.name} has been rejected. '
                            'Please contact admin for more information.'
                        ),
                        related_object_id=rental.id
                    )
                    messages.warning(
                        request,
                        f'Rental rejected for {rental.customer_display_name} - {rental.machine.name}'
                    )

                elif rental.status == 'cancelled':
                    rental.mark_cancelled(
                        cancellation_type='admin',
                        cancel_reason='Cancelled by admin.',
                        system_note='Admin cancelled this rental during review.',
                        admin_note='Cancelled from the admin approval page.',
                    )
                    rental.follow_up_action = 'none'
                    rental.follow_up_requested_at = None
                    rental.follow_up_resolved_at = None
                    rental.save()
                    rental.sync_machine_status()
                    messages.info(
                        request,
                        f'Rental cancelled for {rental.customer_display_name} - {rental.machine.name}'
                    )
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages) if exc.messages else 'Unable to save this rental decision.')
                return redirect('machines:admin_approve_rental', rental_id=rental.id)

            _sync_package_after_rental_update(rental)
            if report_origin or dashboard_origin or overdue_origin:
                return redirect(return_url)
            return redirect('machines:rental_list')
    else:
        form = AdminRentalApprovalForm(instance=rental)

    is_available, conflicts = Rental.check_availability_for_approval(
        machine=rental.machine,
        start_date=rental.start_date,
        end_date=rental.end_date,
        exclude_rental_id=rental.id
    )
    payment_record = rental.payment
    linked_package = _get_linked_rental_package(rental)

    workflow_type = rental.workflow_payment_type
    is_in_kind = rental.payment_type == 'in_kind'
    is_truly_completed = (
        rental.status == 'completed'
        or rental.workflow_state == 'completed'
        or (is_in_kind and rental.settlement_status == 'paid')
    )
    is_cancelled_or_rejected = (
        rental.status in ('cancelled', 'rejected')
        or rental.workflow_state == 'cancelled'
    )
    review_status_label = rental.get_status_display()

    if is_in_kind:
        if rental.workflow_state == 'completed' or rental.settlement_status == 'paid':
            review_status_label = 'Completed'
        elif rental.workflow_state == 'overdue':
            review_status_label = 'Overdue'
        elif rental.workflow_state == 'conflict_review':
            review_status_label = 'Conflict Review'
        elif rental.workflow_state == 'harvest_report_submitted' or rental.settlement_status in {'waiting_for_delivery', 'partially_settled'}:
            review_status_label = 'Harvest Submitted'
        elif rental.workflow_state == 'in_progress' or rental.status == 'approved':
            review_status_label = 'In Progress'
    elif (
        rental.requires_operator_service
        and rental.operator_status == 'completed'
        and rental.workflow_state == 'in_progress'
        and rental.status == 'approved'
    ):
        review_status_label = 'Waiting For Admin Validation'
    elif rental.workflow_state == 'overdue':
        review_status_label = 'Overdue'
    elif rental.workflow_state == 'conflict_review':
        review_status_label = 'Conflict Review'

    can_manage_status = rental.status in ('pending', 'approved') and not is_truly_completed
    payment_ready_for_assignment = (
        rental.payment_type == 'in_kind'
        or rental.payment_verified
        or rental.payment_status == 'paid'
    )
    can_assign_operator = (
        rental.requires_operator_service
        and rental.status == 'approved'
        and payment_ready_for_assignment
        and rental.operator_status not in ('completed', 'harvest_reported')
    )
    can_record_face_to_face_payment = (
        rental.payment_method == 'face_to_face'
        and rental.status == 'approved'
        and not rental.payment_verified
    )
    can_verify_online_payment = (
        rental.payment_method == 'online'
        and rental.status == 'approved'
        and not rental.payment_verified
        and bool(rental.payment_date or rental.stripe_session_id)
    )
    can_complete_paid_rental = _can_admin_complete_paid_rental(rental)
    completion_waiting_for_operator_acceptance = (
        rental.payment_type != 'in_kind'
        and rental.payment_verified
        and rental.workflow_state == 'in_progress'
        and rental.status == 'approved'
        and _operator_acceptance_pending_for_completion(rental)
    )
    can_start_operation = (
        rental.payment_type == 'in_kind'
        and rental.workflow_state == 'approved'
        and rental.assigned_operator_id is not None
    )
    can_submit_harvest = (
        rental.payment_type == 'in_kind'
        and rental.workflow_state in ('in_progress', 'harvest_report_submitted')
    )
    can_confirm_rice_received = (
        rental.payment_type == 'in_kind'
        and rental.settlement_status in {'waiting_for_delivery', 'partially_settled'}
    )
    is_effectively_completed = is_truly_completed or is_cancelled_or_rejected
    has_admin_actions = any([
        can_manage_status,
        can_assign_operator,
        can_record_face_to_face_payment,
        can_verify_online_payment,
        can_complete_paid_rental,
        can_start_operation,
        can_submit_harvest,
        can_confirm_rice_received,
    ]) and not is_effectively_completed
    show_workflow_panel = not is_effectively_completed
    show_operator_assignment_panel = not linked_package and rental.requires_operator_service and (
        can_assign_operator or bool(rental.assigned_operator)
    ) and not is_effectively_completed
    refund_available = bool(
        payment_record
        and rental.status == 'cancelled'
        and payment_record.can_accept_refunds
    )

    if rental.workflow_state == 'overdue':
        payment_headline = 'This rental has exceeded its scheduled end date and still blocks the machine'
        payment_tone = 'danger'
    elif rental.workflow_state == 'conflict_review':
        payment_headline = 'This approved rental is blocked by an overdue machine conflict and needs admin review'
        payment_tone = 'warning'
    elif is_cancelled_or_rejected:
        if refund_available:
            payment_headline = 'Rental cancelled and waiting for refund processing'
            payment_tone = 'warning'
        elif payment_record and payment_record.total_refunded > 0:
            payment_headline = f'Rental cancelled and {payment_record.refund_status.lower()}'
            payment_tone = 'success'
        elif rental.status == 'rejected':
            payment_headline = 'Rental request rejected'
            payment_tone = 'danger'
        else:
            payment_headline = 'Rental cancelled'
            payment_tone = 'warning'
    elif workflow_type == 'online':
        if is_effectively_completed:
            payment_headline = 'Gcash payment verified and rental completed'
            payment_tone = 'success'
        elif rental.payment_verified:
            payment_headline = 'Gcash payment verified and rental in progress'
            payment_tone = 'success'
        elif rental.status == 'pending':
            payment_headline = 'Approval needed before sending the member to payment'
            payment_tone = 'warning'
        elif rental.payment_date or rental.stripe_session_id:
            payment_headline = 'Gcash payment received and waiting for admin verification'
            payment_tone = 'warning'
        else:
            payment_headline = 'Approved and waiting for Gcash payment'
            payment_tone = 'info'
    elif workflow_type == 'face_to_face':
        if is_effectively_completed:
            payment_headline = 'Over-the-counter payment recorded and rental completed'
            payment_tone = 'success'
        elif rental.operator_status == 'completed' and rental.workflow_state == 'in_progress':
            payment_headline = 'Operator completed the work and the rental is waiting for admin validation'
            payment_tone = 'warning'
        elif rental.payment_verified:
            payment_headline = 'Over-the-counter payment recorded and rental in progress'
            payment_tone = 'success'
        elif rental.status == 'pending':
            payment_headline = 'Approval needed before recording over-the-counter payment'
            payment_tone = 'warning'
        elif rental.status == 'approved':
            payment_headline = 'Approved and waiting for over-the-counter payment recording'
            payment_tone = 'info'
        else:
            payment_headline = 'Over-the-counter payment workflow'
            payment_tone = 'secondary'
    else:
        if rental.workflow_state == 'completed':
            payment_headline = 'In-kind settlement completed'
            payment_tone = 'success'
        elif rental.settlement_status in {'waiting_for_delivery', 'partially_settled'} or rental.workflow_state == 'harvest_report_submitted':
            payment_headline = 'Harvest recorded and waiting for rice delivery'
            payment_tone = 'warning'
        elif rental.workflow_state == 'in_progress':
            payment_headline = 'Operation in progress and waiting for harvest report'
            payment_tone = 'info'
        elif rental.status == 'approved':
            payment_headline = 'In-kind settlement is in progress and ready for operation, harvest, and delivery tracking'
            payment_tone = 'info'
        else:
            payment_headline = 'In-kind settlement workflow'
            payment_tone = 'secondary'

    if (
        not is_in_kind
        and rental.operator_status == 'completed'
        and rental.workflow_state == 'in_progress'
        and rental.status == 'approved'
    ):
        payment_headline = 'Operator completed the work and the rental is waiting for admin validation'
        payment_tone = 'warning'

    overdue_conflicts = []
    if rental.workflow_state == 'conflict_review':
        overdue_conflicts = [
            conflict
            for conflict in Rental.objects.filter(machine=rental.machine, workflow_state='overdue').exclude(pk=rental.pk)
            if conflict.overlaps_schedule(rental.start_date, rental.end_date)
        ]
    affected_approved_rentals = []
    if rental.workflow_state == 'overdue':
        affected_approved_rentals = [
            approved
            for approved in Rental.objects.filter(
                machine=rental.machine,
                status='approved',
                workflow_state__in=['approved', 'conflict_review'],
            ).exclude(pk=rental.pk)
            if rental.overlaps_schedule(approved.start_date, approved.end_date)
        ]
    can_reschedule_conflict = (
        rental.status in {'pending', 'approved'}
        and not is_effectively_completed
        and rental.workflow_state == 'conflict_review'
    )

    context = {
        'rental': rental,
        'purpose_details': _build_purpose_details(rental.purpose),
        'form': form,
        'face_to_face_form': FaceToFacePaymentForm(instance=rental),
        'operator_candidates': User.objects.filter(is_active=True, role=User.OPERATOR).order_by('first_name', 'last_name', 'username'),
        'has_conflicts': not is_available,
        'conflicts': conflicts if not is_available else None,
        'workflow_type': workflow_type,
        'review_status_label': review_status_label,
        'can_manage_status': can_manage_status,
        'can_assign_operator': can_assign_operator,
        'can_record_face_to_face_payment': can_record_face_to_face_payment,
        'can_verify_online_payment': can_verify_online_payment,
        'can_complete_paid_rental': can_complete_paid_rental,
        'completion_waiting_for_operator_acceptance': completion_waiting_for_operator_acceptance,
        'can_start_operation': can_start_operation,
        'can_submit_harvest': can_submit_harvest,
        'can_confirm_rice_received': can_confirm_rice_received,
        'is_effectively_completed': is_effectively_completed,
        'has_admin_actions': has_admin_actions,
        'payment_record': payment_record,
        'refund_available': refund_available,
        'show_workflow_panel': show_workflow_panel,
        'show_operator_assignment_panel': show_operator_assignment_panel,
        'linked_package': linked_package,
        'payment_headline': payment_headline,
        'payment_tone': payment_tone,
        'is_overdue_rental': rental.workflow_state == 'overdue',
        'is_conflict_review': rental.workflow_state == 'conflict_review',
        'overdue_days': rental.overdue_days,
        'effective_end_date': rental.effective_end_date,
        'overdue_conflicts': overdue_conflicts,
        'affected_approved_rentals': affected_approved_rentals,
        'can_reschedule_conflict': can_reschedule_conflict,
        'report_origin': report_origin,
        'return_source': source if (report_origin or dashboard_origin or overdue_origin) else '',
        'return_url': return_url if (report_origin or dashboard_origin or overdue_origin) else '',
    }
    return render(request, 'machines/admin/rental_approval.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def start_equipment_operation(request, rental_id):
    """Move a ready in-kind rental into active operation."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id,
        payment_type='in_kind'
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if rental.workflow_state == 'in_progress':
        messages.info(request, 'This non-cash payment rental is already marked as in progress.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if rental.workflow_state not in {'approved', 'ready_for_operation'}:
        messages.error(request, 'Only non-cash payment rentals that are ready for operation can be started.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental.workflow_state = 'in_progress'
    rental.actual_handover_date = timezone.now()
    rental.save(update_fields=['workflow_state', 'actual_handover_date', 'updated_at'])
    rental.sync_machine_status()

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_in_progress',
        message=f'Equipment operation for {rental.machine.name} is now in progress.',
        related_object_id=rental.id
    )
    messages.success(request, f'Equipment operation started for {rental.machine.name}.')
    return _redirect_after_rental_action(request, rental)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def update_rental_schedule_tracking(request, rental_id):
    """Store planned pickup/return times and optional actual timestamps for alert tracking."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    try:
        rental.scheduled_pickup_at = _parse_local_datetime_input(request.POST.get('scheduled_pickup_at'))
        rental.scheduled_return_at = _parse_local_datetime_input(request.POST.get('scheduled_return_at'))
        rental.actual_pickup_at = _parse_local_datetime_input(request.POST.get('actual_pickup_at'))
        rental.actual_return_at = _parse_local_datetime_input(request.POST.get('actual_return_at'))
    except ValueError:
        messages.error(request, 'Please enter valid date and time values.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    update_fields = [
        'scheduled_pickup_at',
        'scheduled_return_at',
        'actual_pickup_at',
        'actual_return_at',
        'updated_at',
    ]

    if rental.actual_pickup_at and not rental.actual_handover_date:
        rental.actual_handover_date = rental.actual_pickup_at
        update_fields.append('actual_handover_date')

    if rental.actual_return_at and rental.status == 'completed' and not rental.actual_completion_time:
        rental.actual_completion_time = rental.actual_return_at
        update_fields.append('actual_completion_time')

    try:
        rental.save(update_fields=update_fields)
    except Exception as exc:
        messages.error(request, f'Could not save the rental schedule: {exc}')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    messages.success(request, 'Rental schedule tracking was updated.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def mark_rental_picked_up(request, rental_id):
    """Quick action to clear pickup overdue alerts once the machine is handed over."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    now = timezone.now()
    rental.actual_pickup_at = now
    update_fields = ['actual_pickup_at', 'updated_at']

    if not rental.actual_handover_date:
        rental.actual_handover_date = now
        update_fields.append('actual_handover_date')

    rental.save(update_fields=update_fields)
    messages.success(request, 'Pickup time recorded.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def mark_rental_returned(request, rental_id):
    """Quick action to clear overdue return alerts after the machine comes back."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    now = timezone.now()
    rental.actual_return_at = now
    update_fields = ['actual_return_at', 'updated_at']

    if rental.status == 'completed' and not rental.actual_completion_time:
        rental.actual_completion_time = now
        update_fields.append('actual_completion_time')

    rental.save(update_fields=update_fields)

    create_notification(
        user=rental.user,
        notification_type='rental_status_update',
        title=f'Return recorded - {rental.machine.name}',
        message=f'BUFIA recorded the return of {rental.machine.name}.',
        category='rental',
        priority='normal',
        related_object_id=rental.id,
    )
    messages.success(request, 'Return time recorded.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def submit_harvest_report(request, rental_id):
    """Record the harvest for an in-kind rental and compute settlement shares."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id
    )
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Harvest reporting applies only to non-cash payment rentals.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if rental.workflow_state not in ('in_progress', 'harvest_report_submitted'):
        messages.error(request, 'Start equipment operation before recording the harvest.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    form = HarvestReportForm(request.POST, instance=rental)
    if not form.is_valid():
        messages.error(request, 'Please provide a valid harvest value.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental = form.save(commit=False)
    
    # Calculate shares using machine-configured ratio
    bufia_share, member_share = rental.calculate_harvest_shares(rental.total_harvest_sacks)
    rental.total_rice_sacks_harvested = rental.total_harvest_sacks
    rental.bufia_share = bufia_share
    rental.member_share = member_share
    rental.organization_share_required = bufia_share
    rental.payment_status = 'pending'
    rental.settlement_status = 'waiting_for_delivery'
    rental.settlement_type = 'after_harvest'
    rental.workflow_state = 'harvest_report_submitted'
    rental.save(update_fields=[
        'total_harvest_sacks',
        'total_rice_sacks_harvested',
        'bufia_share',
        'member_share',
        'organization_share_required',
        'payment_status',
        'settlement_status',
        'settlement_type',
        'workflow_state',
        'updated_at',
    ])

    HarvestReport.objects.create(
        rental=rental,
        total_rice_sacks_harvested=rental.total_harvest_sacks,
        recorded_by_admin=request.user,
    )

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_received',
        message=(
            f'Harvest recorded for {rental.machine.name}. '
            f'Total harvest: {rental.total_harvest_sacks} sacks. '
            f'BUFIA share required: {rental.bufia_share} sacks (ratio {rental.machine.get_in_kind_ratio_display()}). '
            f'Member share: {rental.member_share} sacks. '
            f'Please deliver {rental.bufia_share} sacks to BUFIA for settlement.'
        ),
        related_object_id=rental.id
    )
    messages.success(
        request,
        f'Harvest recorded. Total harvest: {rental.total_harvest_sacks} sacks. '
        f'BUFIA share: {rental.bufia_share} sacks. Member share: {rental.member_share} sacks.'
    )
    return _redirect_after_rental_action(request, rental)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def confirm_rice_received(request, rental_id):
    """Record rice delivery and automatically complete a settled in-kind rental."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id
    )
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Rice confirmation applies only to non-cash payment rentals.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    form = ConfirmRiceReceivedForm(request.POST, instance=rental)
    if not form.is_valid():
        messages.error(request, 'Please provide delivered sacks.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental = form.save(commit=False)
    rental.save(update_fields=['organization_share_received', 'updated_at'])

    required_share = rental.required_bufia_share or 0
    if required_share and rental.organization_share_received < required_share:
        remaining = required_share - rental.organization_share_received
        rental.payment_status = 'partially_settled'
        rental.settlement_status = 'partially_settled'
        rental.save(update_fields=['payment_status', 'settlement_status', 'updated_at'])
        messages.warning(
            request,
            f'Partial rice delivery recorded. {remaining} sack(s) still need to be delivered before completion.'
        )
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    settlement_reference = rental.generate_settlement_reference()
    Settlement.objects.update_or_create(
        rental=rental,
        defaults={
            'bufia_share': rental.required_bufia_share or 0,
            'member_share': rental.member_share or 0,
            'total_harvested': rental.harvest_total or 0,
            'settlement_reference': settlement_reference,
            'finalized_by': request.user,
        }
    )

    rental.payment_status = 'paid_in_kind'
    rental.settlement_status = 'paid'
    rental.payment_verified = True
    rental.settlement_date = timezone.now()
    rental.settlement_reference = settlement_reference
    rental.transaction_reference = rental.generate_transaction_reference()
    rental.verified_by = request.user
    rental.verification_date = timezone.now()
    rental.status = 'completed'
    rental.workflow_state = 'completed'
    if rental.assigned_operator_id and rental.operator_status != 'completed':
        rental.operator_status = 'completed'
    rental.actual_completion_time = timezone.now()
    update_fields = [
        'organization_share_received',
        'payment_status',
        'settlement_status',
        'payment_verified',
        'settlement_date',
        'settlement_reference',
        'transaction_reference',
        'verified_by',
        'verification_date',
        'status',
        'workflow_state',
        'operator_status',
        'actual_completion_time',
        'updated_at',
    ]
    rental.save(update_fields=update_fields)
    rental.sync_machine_status()

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'Non-cash payment settlement completed for {rental.machine.name}. '
            f'Transaction: {rental.transaction_reference}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, 'Rice delivery confirmed. Rental automatically marked as completed.')
    return _redirect_after_rental_action(request, rental)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def verify_online_payment(request, rental_id):
    """Verify a completed Gcash payment and move the rental into progress."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if rental.payment_method != 'online':
        messages.error(request, 'This action only applies to Gcash payments.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if not rental.payment_date and not rental.stripe_session_id:
        messages.error(request, 'No Gcash payment record was found for this rental.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    # Ensure rental is approved before verifying payment
    if rental.status != 'approved':
        messages.error(request, 'Rental must be approved before verifying payment.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    payment = _ensure_rental_payment_record(
        rental,
        status='completed',
        amount=rental.payment_amount,
        paid_at=rental.payment_date or timezone.now(),
        payment_provider='paymongo',
        processed_by=request.user,
    )
    _mark_rental_in_progress_after_payment(rental, request.user)

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'Your Gcash payment for {rental.machine.name} has been verified. '
            f'Transaction ID: {payment.internal_transaction_id}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, f'Gcash payment verified. Rental moved into operation. Transaction ID: {payment.internal_transaction_id}')
    return _redirect_after_rental_action(request, rental)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def record_face_to_face_payment(request, rental_id):
    """Record an over-the-counter payment and move the rental into progress."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id
    )

    if rental.payment_method not in [None, '', 'face_to_face']:
        messages.error(request, 'This action only applies to over-the-counter payments.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    # Ensure rental is approved before recording payment
    if rental.status != 'approved':
        messages.error(request, 'Rental must be approved before recording payment.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    package_linked_rental = bool(getattr(getattr(rental, 'package_item', None), 'rental_package_id', None))
    if package_linked_rental and rental.workflow_state not in {'approved', 'ready_for_payment'}:
        messages.error(request, 'This rental is not yet ready for payment.')
        return _redirect_after_rental_action(request, rental)

    form = FaceToFacePaymentForm(request.POST, instance=rental)
    if not form.is_valid():
        for error in form.non_field_errors():
            messages.error(request, error)
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental = form.save(commit=False)
    rental.payment_method = 'face_to_face'
    rental.payment_status = 'paid'
    rental.save(update_fields=[
        'payment_amount',
        'payment_date',
        'receipt_number',
        'payment_method',
        'payment_status',
        'updated_at',
    ])

    payment = _ensure_rental_payment_record(
        rental,
        status='completed',
        amount=rental.payment_amount,
        paid_at=rental.payment_date,
        payment_provider='manual',
        processed_by=request.user,
        amount_received=rental.payment_amount,
        change_given=Decimal('0.00'),
    )
    _mark_rental_in_progress_after_payment(rental, request.user)

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'Your over-the-counter payment for {rental.machine.name} has been recorded. '
            f'Transaction ID: {payment.internal_transaction_id}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, f'Over-the-counter payment recorded. Rental moved into operation. Transaction ID: {payment.internal_transaction_id}')
    return _redirect_after_rental_action(request, rental)


@login_required
@user_passes_test(_is_admin)
def verify_payment_ajax(request, rental_id):
    """AJAX endpoint to verify Gcash payments from the dashboard."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)

    try:
        rental = Rental.objects.get(pk=rental_id)
        if rental.payment_method != 'online':
            return JsonResponse({'success': False, 'message': 'Only Gcash payments can be verified here.'}, status=400)
        if not rental.payment_date and not rental.stripe_session_id:
            return JsonResponse({'success': False, 'message': 'No Gcash payment record found.'}, status=400)

        payment = _ensure_rental_payment_record(
            rental,
            status='completed',
            amount=rental.payment_amount,
            paid_at=rental.payment_date or timezone.now(),
            payment_provider='paymongo',
            processed_by=request.user,
        )
        _mark_rental_in_progress_after_payment(rental, request.user)
        _sync_package_after_rental_update(rental)

        return JsonResponse({
            'success': True,
            'verified': True,
            'transaction_id': payment.internal_transaction_id,
            'message': 'Payment verified. Rental moved to in progress.',
        })
    except Rental.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rental not found'}, status=404)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=500)


@login_required
@user_passes_test(_is_admin)
def admin_conflicts_report(request):
    """
    Show potential conflicts and scheduling issues
    """
    today = timezone.now().date()
    Rental.sync_overdue_workflow_states(today=today)
    conflict_counts = _build_conflict_dashboard_counts(today=today)
    conflicts = conflict_counts['conflicts']
    pending_conflicts = conflict_counts['pending_conflicts']

    overdue_by_machine = {}
    for overdue in Rental.objects.filter(
        workflow_state='overdue',
        status='approved',
    ).select_related('machine', 'user').order_by('end_date', 'start_date'):
        overdue_by_machine.setdefault(overdue.machine_id, []).append(overdue)

    conflict_review_rentals = conflict_counts['conflict_review_rentals']

    for rental in conflict_review_rentals:
        rental.overdue_conflicts = [
            overdue
            for overdue in overdue_by_machine.get(rental.machine_id, [])
            if overdue.overlaps_schedule(rental.start_date, rental.end_date)
        ]
    
    context = {
        'conflicts': conflicts,
        'pending_conflicts': pending_conflicts,
        'conflict_review_rentals': conflict_review_rentals,
        'conflict_review_count': conflict_counts['conflict_review_count'],
        'total_conflicts': conflict_counts['total_conflicts'],
        'total_pending_conflicts': conflict_counts['total_pending_conflicts'],
        'conflict_alert_count': conflict_counts['conflict_alert_count'],
    }
    
    return render(request, 'machines/admin/conflicts_report.html', context)


@login_required
@user_passes_test(_is_admin)
def bulk_approve_rentals(request):
    """
    Bulk approve multiple rentals at once
    """
    if request.method != 'POST':
        return redirect('machines:admin_rental_dashboard')
    
    # Get rental IDs from either format
    rental_ids = request.POST.getlist('rental_ids')
    if not rental_ids:
        rental_ids_input = request.POST.get('rental_ids_input', '')
        if rental_ids_input:
            rental_ids = [rid.strip() for rid in rental_ids_input.split(',') if rid.strip()]
    
    if not rental_ids:
        messages.warning(request, 'No rentals selected')
        return redirect('machines:admin_rental_dashboard')
    
    approved_count = 0
    failed_count = 0
    
    for rental_id in rental_ids:
        try:
            with transaction.atomic():
                rental = Rental.objects.select_for_update().get(pk=rental_id)
                
                if rental.status != 'pending':
                    messages.warning(
                        request,
                        f'Skipped Rental #{rental_id}: Only pending rentals can be approved'
                    )
                    failed_count += 1
                    continue
                
                # Check for conflicts
                is_available, conflicts = Rental.check_availability_for_approval(
                    rental.machine,
                    rental.start_date,
                    rental.end_date,
                    exclude_rental_id=rental.id
                )
                
                if not is_available:
                    messages.warning(
                        request,
                        f'Skipped Rental #{rental_id}: Has conflicts'
                    )
                    failed_count += 1
                    continue
                
                # Approve and initialize the next workflow step.
                rental.status = 'approved'
                rental.workflow_state = 'approved'
                rental.verified_by = None
                rental.verification_date = None
                if rental.payment_type == 'in_kind':
                    rental.payment_status = 'pending'
                    rental.settlement_type = 'after_harvest'
                    rental.settlement_status = (
                        'waiting_for_delivery'
                        if rental.organization_share_required and rental.organization_share_required > 0
                        else 'pending'
                    )
                else:
                    rental.payment_status = 'pending'
                rental.save()

                if rental.payment_type != 'in_kind':
                    _ensure_rental_payment_record(rental, status='pending', amount=rental.payment_amount)
                
                # Notify user
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_approved',
                    message=f'Your rental for {rental.machine.name} has been approved!',
                    related_object_id=rental.id
                )
                
                approved_count += 1
                
        except Exception as e:
            messages.error(request, f'Error approving Rental #{rental_id}: {str(e)}')
            failed_count += 1
    
    if approved_count > 0:
        messages.success(request, f'Successfully approved {approved_count} rental(s)')
    
    if failed_count > 0:
        messages.warning(request, f'Failed to approve {failed_count} rental(s)')
    
    return redirect('machines:admin_rental_dashboard')


@login_required
@user_passes_test(_is_admin)
def bulk_delete_rentals(request):
    """
    Bulk delete multiple rentals at once
    """
    if request.method != 'POST':
        return redirect('machines:rental_list')
    
    # Get rental IDs from either format
    rental_ids = request.POST.getlist('rental_ids')
    if not rental_ids:
        rental_ids_input = request.POST.get('rental_ids_input', '')
        if rental_ids_input:
            rental_ids = [rid.strip() for rid in rental_ids_input.split(',') if rid.strip()]
    
    if not rental_ids:
        messages.warning(request, 'No rentals selected')
        return redirect('machines:rental_list')
    
    deleted_count = 0
    failed_count = 0
    
    for rental_id in rental_ids:
        try:
            with transaction.atomic():
                rental = Rental.objects.select_for_update().get(pk=rental_id)
                
                # Store info for notification
                user = rental.user
                machine_name = rental.machine.name
                
                # Delete the rental
                rental.delete()
                
                # Notify user
                UserNotification.objects.create(
                    user=user,
                    notification_type='rental_deleted',
                    message=f'Your rental request for {machine_name} has been deleted by admin.',
                )
                
                deleted_count += 1
                
        except Rental.DoesNotExist:
            messages.error(request, f'Rental #{rental_id} not found')
            failed_count += 1
        except Exception as e:
            messages.error(request, f'Error deleting Rental #{rental_id}: {str(e)}')
            failed_count += 1
    
    if deleted_count > 0:
        messages.success(request, f'Successfully deleted {deleted_count} rental(s)')
    
    if failed_count > 0:
        messages.warning(request, f'Failed to delete {failed_count} rental(s)')
    
    return redirect('machines:rental_list')



# IN-KIND Workflow Admin Views

@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_in_kind_dashboard(request):
    """
    Admin dashboard for non-cash payment rental workflow management
    Shows pending approvals, in-progress rentals, and harvest verification queue
    """
    from machines.utils import (
        approve_rental, reject_rental, start_equipment_operation,
        record_harvest_report, verify_harvest_report, reject_harvest_report
    )
    from .models import HarvestReport, Settlement
    
    today = timezone.now().date()
    
    # Get IN-KIND rentals by workflow state
    pending_approvals = Rental.objects.filter(
        payment_type='in_kind',
        workflow_state='requested'
    ).select_related('machine', 'user').order_by('-created_at')
    
    approved_rentals = Rental.objects.filter(
        payment_type='in_kind',
        workflow_state='approved'
    ).select_related('machine', 'user').order_by('-created_at')
    
    in_progress_rentals = Rental.objects.filter(
        payment_type='in_kind',
        workflow_state='in_progress'
    ).select_related('machine', 'user').order_by('-created_at')
    
    harvest_verification_queue = Rental.objects.filter(
        payment_type='in_kind',
        workflow_state='harvest_report_submitted'
    ).select_related('machine', 'user').prefetch_related('harvest_reports').order_by('-created_at')
    
    completed_rentals = Rental.objects.filter(
        payment_type='in_kind',
        workflow_state='completed'
    ).select_related('machine', 'user').order_by('-created_at')[:10]
    
    context = {
        'pending_approvals': pending_approvals,
        'pending_approvals_count': pending_approvals.count(),
        'approved_rentals': approved_rentals,
        'approved_rentals_count': approved_rentals.count(),
        'in_progress_rentals': in_progress_rentals,
        'in_progress_rentals_count': in_progress_rentals.count(),
        'harvest_verification_queue': harvest_verification_queue,
        'harvest_verification_count': harvest_verification_queue.count(),
        'completed_rentals': completed_rentals,
        'today': today,
    }
    
    return render(request, 'machines/admin/in_kind_dashboard.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_approve_in_kind_rental(request, rental_id):
    """
    Approve a non-cash payment rental request (transition requested → pending_approval → approved)
    """
    from machines.utils import approve_rental
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    if rental.workflow_state != 'requested':
        messages.error(request, f'Can only approve rentals in requested state. Current: {rental.workflow_state}')
        return redirect('machines:admin_in_kind_dashboard')
    
    try:
        approve_rental(rental, request.user)
        messages.success(
            request,
            f'Rental approved for {rental.customer_display_name} - {rental.machine.name}'
        )
    except Exception as e:
        messages.error(request, f'Error approving rental: {str(e)}')
    
    return redirect('machines:admin_in_kind_dashboard')


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_reject_in_kind_rental(request, rental_id):
    """
    Reject a non-cash payment rental request (transition to cancelled)
    """
    from machines.utils import reject_rental
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    reason = request.POST.get('reason', 'No reason provided')
    
    try:
        reject_rental(rental, request.user, reason)
        messages.warning(
            request,
            f'Rental rejected for {rental.customer_display_name} - {rental.machine.name}'
        )
    except Exception as e:
        messages.error(request, f'Error rejecting rental: {str(e)}')
    
    return redirect('machines:admin_in_kind_dashboard')


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_start_equipment_operation(request, rental_id):
    """
    Start equipment operation (transition approved → in_progress)
    """
    from machines.utils import start_equipment_operation
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    if rental.workflow_state != 'approved':
        messages.error(request, f'Can only start operation for approved rentals. Current: {rental.workflow_state}')
        return redirect('machines:admin_in_kind_dashboard')
    
    try:
        start_equipment_operation(rental, request.user)
        messages.success(
            request,
            f'Equipment operation started for {rental.machine.name}'
        )
    except Exception as e:
        messages.error(request, f'Error starting equipment operation: {str(e)}')
    
    return redirect('machines:admin_in_kind_dashboard')


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_record_harvest_report(request, rental_id):
    """
    Record harvest report from operator (transition in_progress → harvest_report_submitted)
    """
    from machines.utils import record_harvest_report
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    if request.method == 'POST':
        total_sacks = request.POST.get('total_sacks')
        
        if not total_sacks:
            messages.error(request, 'Please provide total sacks harvested')
            return redirect('machines:admin_in_kind_dashboard')
        
        try:
            total_sacks = float(total_sacks)
            harvest_report = record_harvest_report(rental, total_sacks, request.user)
            messages.success(
                request,
                f'Harvest report recorded: {total_sacks} sacks. '
                f'BUFIA share: {rental.bufia_share}, Member share: {rental.member_share}'
            )
        except Exception as e:
            messages.error(request, f'Error recording harvest report: {str(e)}')
        
        return redirect('machines:admin_in_kind_dashboard')
    
    context = {
        'rental': rental,
    }
    return render(request, 'machines/admin/record_harvest_report.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_verify_harvest_report(request, rental_id):
    """
    Verify harvest report and create settlement (transition harvest_report_submitted → completed)
    """
    from machines.utils import verify_harvest_report
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    if rental.workflow_state != 'harvest_report_submitted':
        messages.error(request, f'Can only verify harvest for harvest_report_submitted rentals. Current: {rental.workflow_state}')
        return redirect('machines:admin_in_kind_dashboard')
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        
        try:
            settlement = verify_harvest_report(rental, request.user, notes)
            messages.success(
                request,
                f'Harvest report verified and settlement created. '
                f'Reference: {settlement.settlement_reference}'
            )
        except Exception as e:
            messages.error(request, f'Error verifying harvest report: {str(e)}')
        
        return redirect('machines:admin_in_kind_dashboard')
    
    harvest_report = rental.harvest_reports.first()
    context = {
        'rental': rental,
        'harvest_report': harvest_report,
    }
    return render(request, 'machines/admin/verify_harvest_report.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_reject_harvest_report(request, rental_id):
    """
    Reject harvest report (transition harvest_report_submitted → in_progress)
    """
    from machines.utils import reject_harvest_report
    
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    
    if rental.workflow_state != 'harvest_report_submitted':
        messages.error(request, f'Can only reject harvest for harvest_report_submitted rentals. Current: {rental.workflow_state}')
        return redirect('machines:admin_in_kind_dashboard')
    
    reason = request.POST.get('reason', 'No reason provided')
    
    try:
        reject_harvest_report(rental, reason, request.user)
        messages.warning(
            request,
            f'Harvest report rejected. Operator needs to recount and resubmit.'
        )
    except Exception as e:
        messages.error(request, f'Error rejecting harvest report: {str(e)}')
    
    return redirect('machines:admin_in_kind_dashboard')



def admin_complete_rental_early(request, rental_id):
    """
    Mark a rental as completed early and make the machine available.
    Transition: in_progress → completed
    """
    from machines.utils import complete_rental_early

    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )

    if rental.workflow_state != 'in_progress':
        messages.error(
            request,
            f'Can only complete early rentals in progress. '
            f'Current state: {rental.workflow_state}'
        )
        return redirect('machines:admin_in_kind_dashboard')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        try:
            complete_rental_early(rental, request.user, reason)
            messages.success(
                request,
                f'Rental completed early. Machine {rental.machine.name} '
                f'is now available for new bookings.'
            )
        except Exception as e:
            messages.error(request, f'Error completing rental: {str(e)}')

        return redirect('machines:admin_in_kind_dashboard')

    context = {
        'rental': rental,
    }
    return render(
        request,
        'machines/admin/complete_rental_early.html',
        context
    )


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def bulk_approve_rentals(request):
    """Bulk-approve pending rentals using the same approval-first workflow."""
    if request.method != 'POST':
        return redirect('machines:admin_rental_dashboard')

    rental_ids = request.POST.getlist('rental_ids')
    if not rental_ids:
        rental_ids_input = request.POST.get('rental_ids_input', '')
        if rental_ids_input:
            rental_ids = [rid.strip() for rid in rental_ids_input.split(',') if rid.strip()]

    if not rental_ids:
        messages.warning(request, 'No rentals selected')
        return redirect('machines:admin_rental_dashboard')

    approved_count = 0
    failed_count = 0

    for rental_id in rental_ids:
        try:
            rental = Rental.objects.select_for_update().get(pk=rental_id)
            if rental.status != 'pending':
                failed_count += 1
                messages.warning(request, f'Skipped Rental #{rental_id}: Only pending rentals can be approved')
                continue

            is_available, _ = Rental.check_availability_for_approval(
                rental.machine,
                rental.start_date,
                rental.end_date,
                exclude_rental_id=rental.id
            )
            if not is_available:
                failed_count += 1
                messages.warning(request, f'Skipped Rental #{rental_id}: Has conflicts')
                continue

            rental.status = 'approved'
            rental.workflow_state = 'approved'
            rental.payment_verified = False
            rental.verified_by = None
            rental.verification_date = None

            if rental.payment_type == 'in_kind':
                rental.payment_status = 'pending'
                rental.settlement_type = 'after_harvest'
                rental.settlement_status = (
                    'waiting_for_delivery'
                    if rental.organization_share_required and rental.organization_share_required > 0
                    else 'pending'
                )
            else:
                rental.payment_status = 'pending'

            rental.save()

            if rental.payment_type != 'in_kind':
                _ensure_rental_payment_record(rental, status='pending', amount=rental.payment_amount)

            UserNotification.objects.create(
                user=rental.user,
                notification_type='rental_approved',
                message=(
                    f'Your rental for {rental.machine.name} has been approved. '
                    f'Payment type: {rental.workflow_payment_type_display}.'
                ),
                related_object_id=rental.id
            )
            approved_count += 1
        except Exception as exc:
            failed_count += 1
            messages.error(request, f'Error approving Rental #{rental_id}: {exc}')

    if approved_count:
        messages.success(request, f'Successfully approved {approved_count} rental(s)')
    if failed_count:
        messages.warning(request, f'Failed to approve {failed_count} rental(s)')

    return redirect('machines:admin_rental_dashboard')


@login_required
@user_passes_test(_is_admin)
def admin_complete_rental_early(request, rental_id):
    """Mark a paid cash rental as completed once the job is actually done."""
    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id,
    )

    if rental.payment_type == 'in_kind':
        messages.error(
            request,
            'Non-cash payment rentals are completed automatically after the required rice share is recorded.'
        )
        return _redirect_after_rental_action(request, rental)

    if rental.workflow_state != 'in_progress' or not rental.payment_verified:
        messages.error(
            request,
            'Only paid rentals that are already in progress can be marked completed.'
        )
        return _redirect_after_rental_action(request, rental)

    if rental.requires_operator_service and rental.assigned_operator_id is None:
        messages.error(
            request,
            'Assign an operator before marking this rental as completed.'
        )
        return _redirect_after_rental_action(request, rental)

    if _operator_acceptance_pending_for_completion(rental):
        messages.error(
            request,
            'The assigned operator must accept the task before this rental can be marked as completed.'
        )
        return _redirect_after_rental_action(request, rental)

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return _redirect_after_rental_action(request, rental)

    rental.status = 'completed'
    rental.workflow_state = 'completed'
    rental.actual_completion_time = timezone.now()
    update_fields = ['status', 'workflow_state', 'actual_completion_time', 'updated_at']
    if rental.assigned_operator_id and rental.operator_status != 'completed':
        rental.operator_status = 'completed'
        update_fields.append('operator_status')
    rental.save(update_fields=update_fields)
    rental.sync_machine_status()

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_completed',
        message=f'Your rental for {rental.machine.name} has been marked as completed.',
        related_object_id=rental.id
    )
    messages.success(request, f'Rental marked as completed for {rental.machine.name}.')
    return _redirect_after_rental_action(request, rental)



@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_overview(request):
    """Overview of all operators and their workload for admin"""
    from users.models import CustomUser
    from django.db.models import Count, Q
    
    # Get all operators by role
    operators = CustomUser.objects.filter(
        role=CustomUser.OPERATOR,
        is_active=True
    ).annotate(
        active_jobs=Count(
            'operator_rentals',
            filter=Q(operator_rentals__status='approved')
        ),
        completed_jobs=Count(
            'operator_rentals',
            filter=Q(operator_rentals__status='completed')
        ),
        total_assignments=Count('operator_rentals')
    ).order_by('first_name', 'last_name')
    
    # Calculate summary stats
    total_operators = operators.count()
    available_operators = operators.filter(active_jobs=0).count()
    busy_operators = operators.filter(active_jobs__gt=0).count()
    overloaded_operators = operators.filter(active_jobs__gt=2).count()
    
    # Get recent assignments for each operator
    for operator in operators:
        operator.active_rentals = list(
            operator.operator_rentals.select_related(
                'machine', 'user'
            ).filter(
                status='approved'
            ).exclude(
                workflow_state__in=['completed', 'cancelled']
            ).order_by('start_date', 'created_at')[:3]
        )
        operator.recent_rentals = list(
            operator.operator_rentals.select_related(
                'machine', 'user'
            ).exclude(
                status__in=['cancelled', 'rejected']
            ).order_by('-updated_at')[:5]
        )
        operator.last_completed_rental = operator.operator_rentals.select_related(
            'machine', 'user'
        ).filter(status='completed').order_by('-actual_completion_time').first()
        
        # Determine availability status
        if operator.active_jobs == 0:
            operator.availability_status = 'available'
            operator.availability_class = 'success'
        elif operator.active_jobs <= 2:
            operator.availability_status = 'busy'
            operator.availability_class = 'warning'
        else:
            operator.availability_status = 'overloaded'
            operator.availability_class = 'danger'
        operator.account_status_label = 'Active' if operator.is_active else 'Inactive'
    
    context = {
        'operators': operators,
        'total_operators': total_operators,
        'available_operators': available_operators,
        'busy_operators': busy_operators,
        'overloaded_operators': overloaded_operators,
    }
    
    return render(request, 'machines/admin/operator_overview.html', context)


@user_passes_test(_is_admin)
@transaction.atomic
def reschedule_rental(request, rental_id):
    """
    Reschedule a pending or approved rental to resolve scheduling conflicts.
    """
    rental = get_object_or_404(Rental.objects.select_for_update(), pk=rental_id)
    return_url = _get_safe_return_url(
        request,
        redirect('machines:admin_approve_rental', rental_id=rental.id).url,
    )
    
    if rental.status not in {'pending', 'approved'} or rental.workflow_state in {'completed', 'cancelled'}:
        messages.error(request, 'Only active pending or approved rentals can be rescheduled.')
        return redirect(return_url)
    
    if request.method == 'POST':
        new_start_date = request.POST.get('new_start_date')
        new_end_date = request.POST.get('new_end_date')
        admin_notes = request.POST.get('admin_notes', '')
        
        if not new_start_date or not new_end_date:
            messages.error(request, 'Please provide both start and end dates.')
            return redirect(return_url)
        
        try:
            from datetime import datetime
            new_start = datetime.strptime(new_start_date, '%Y-%m-%d').date()
            new_end = datetime.strptime(new_end_date, '%Y-%m-%d').date()
            
            if new_end < new_start:
                messages.error(request, 'End date cannot be before start date.')
                return redirect(return_url)
            
            if new_start < timezone.now().date():
                messages.error(request, 'Start date cannot be in the past.')
                return redirect(return_url)
            
            is_available, conflicting_rentals = Rental.check_availability_for_approval(
                rental.machine,
                new_start,
                new_end,
                exclude_rental_id=rental.id,
            )

            if not is_available:
                messages.error(request, 'The new dates conflict with other approved rentals.')
                return redirect(return_url)
            
            # Update the rental dates
            old_start = rental.start_date
            old_end = rental.end_date
            previous_workflow_state = rental.workflow_state
            
            rental.start_date = new_start
            rental.end_date = new_end
            if rental.status == 'approved' and rental.workflow_state == 'conflict_review':
                rental.workflow_state = 'approved'
            elif rental.status == 'pending' and rental.workflow_state == 'conflict_review':
                rental.workflow_state = previous_workflow_state or 'requested'
            
            if admin_notes:
                _append_system_note(
                    rental,
                    f"Rescheduled by {request.user.get_full_name() or request.user.username}: {admin_notes}",
                )
            
            rental.save()
            
            # Create notification for the customer
            create_notification(
                user=rental.user,
                title='Rental Rescheduled',
                message=f'Your rental for {rental.machine.name} has been rescheduled from {old_start} - {old_end} to {new_start} - {new_end}.',
                notification_type='rental_rescheduled',
                related_object_id=rental.id
            )
            
            messages.success(
                request, 
                f'Rental successfully rescheduled from {old_start} - {old_end} to {new_start} - {new_end}.'
            )
            
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
        except Exception as e:
            messages.error(request, f'Error rescheduling rental: {str(e)}')
    
    return redirect(return_url)


@user_passes_test(_is_admin)
def overdue_rentals_report(request):
    """
    Dedicated page for viewing and managing overdue rentals.
    """
    _sync_rental_schedule_states()
    
    # Get overdue rentals
    overdue_rentals = Rental.objects.filter(
        workflow_state='overdue'
    ).select_related('machine', 'user').order_by('-end_date')
    conflict_review_rentals = list(
        Rental.objects.filter(
            workflow_state='conflict_review',
            status='approved',
        ).select_related('machine', 'user').order_by('start_date', 'created_at')
    )

    from django.utils import timezone
    today = timezone.now().date()

    overdue_by_machine = {}
    for overdue in overdue_rentals:
        overdue_by_machine.setdefault(overdue.machine_id, []).append(overdue)

    approved_by_machine = {}
    for approved in Rental.objects.filter(
        status='approved',
        workflow_state__in=['approved', 'conflict_review'],
    ).exclude(workflow_state__in=['completed', 'cancelled']).select_related('machine', 'user'):
        approved_by_machine.setdefault(approved.machine_id, []).append(approved)

    for overdue in overdue_rentals:
        overdue.affected_approved_rentals = [
            approved
            for approved in approved_by_machine.get(overdue.machine_id, [])
            if approved.id != overdue.id and overdue.overlaps_schedule(approved.start_date, approved.end_date)
        ]

    for rental in conflict_review_rentals:
        rental.overdue_conflicts = [
            overdue
            for overdue in overdue_by_machine.get(rental.machine_id, [])
            if overdue.overlaps_schedule(rental.start_date, rental.end_date)
        ]
    
    context = {
        'overdue_rentals': overdue_rentals,
        'overdue_count': overdue_rentals.count(),
        'conflict_review_rentals': conflict_review_rentals,
        'conflict_review_count': len(conflict_review_rentals),
        'today': today,
    }
    
    return render(request, 'machines/admin/overdue_rentals_report.html', context)


@user_passes_test(_is_admin)
@transaction.atomic
def extend_rental(request, rental_id):
    """
    Extend an overdue rental by adding additional days to the end date.
    """
    rental = get_object_or_404(Rental.objects.select_for_update(), pk=rental_id)
    return_url = _get_safe_return_url(
        request,
        redirect('machines:admin_overdue_rentals_report').url,
    )
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(return_url)
    
    try:
        extension_days = int(request.POST.get('extension_days', 0) or 0)
        custom_days = int(request.POST.get('custom_days', 0) or 0)
        extension_reason = request.POST.get('extension_reason', '').strip()
        if custom_days > 0:
            extension_days = custom_days
        
        if extension_days <= 0:
            messages.error(request, 'Extension days must be greater than 0.')
            return redirect(return_url)
        
        if not extension_reason:
            messages.error(request, 'Extension reason is required.')
            return redirect(return_url)
        
        # Calculate new end date
        from datetime import timedelta
        old_end_date = rental.end_date
        new_end_date = old_end_date + timedelta(days=extension_days)
        
        # Check for conflicts with the new end date
        conflicting_rentals = Rental.objects.filter(
            machine=rental.machine,
            status__in=['approved', 'in_progress'],
            start_date__lt=new_end_date,
            end_date__gt=old_end_date
        ).exclude(id=rental.id)
        
        if conflicting_rentals.exists():
            messages.error(request, f'Cannot extend rental. The new end date ({new_end_date.strftime("%Y-%m-%d")}) conflicts with other approved rentals.')
            return redirect(return_url)
        
        # Update the rental
        rental.end_date = new_end_date
        
        # Add admin notes
        extension_note = f"Extended by {extension_days} day(s) by {request.user.get_full_name() or request.user.username}. Reason: {extension_reason}"
        _append_system_note(rental, extension_note)
        
        # Update workflow state if it was overdue
        if rental.workflow_state == 'overdue':
            rental.workflow_state = 'approved'  # Reset to approved since it's no longer overdue
        
        rental.save()
        
        # Create notification for the customer
        create_notification(
            user=rental.user,
            title='Rental Extended',
            message=f'Your rental for {rental.machine.name} has been extended until {new_end_date.strftime("%B %d, %Y")}.',
            notification_type='rental_extended',
            related_object_id=rental.id
        )
        
        messages.success(
            request, 
            f'Rental successfully extended by {extension_days} day(s). New end date: {new_end_date.strftime("%Y-%m-%d")}'
        )
        
    except ValueError:
        messages.error(request, 'Invalid extension days value.')
    except Exception as e:
        messages.error(request, f'Error extending rental: {str(e)}')
    
    return redirect(return_url)


@user_passes_test(_is_admin)
@transaction.atomic
def complete_overdue_rental(request, rental_id):
    """
    Mark an overdue rental as completed with optional notes.
    """
    rental = get_object_or_404(Rental.objects.select_for_update(), pk=rental_id)
    return_url = _get_safe_return_url(
        request,
        redirect('machines:admin_overdue_rentals_report').url,
    )
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(return_url)
    
    try:
        completion_notes = request.POST.get('completion_notes', '').strip()
        
        # Update rental status
        old_status = rental.status
        old_workflow_state = rental.workflow_state
        
        now = timezone.now()
        rental.status = 'completed'
        rental.workflow_state = 'completed'
        rental.actual_return_at = rental.actual_return_at or now
        rental.actual_completion_time = rental.actual_completion_time or now
        
        # Add completion notes
        completion_note = f"Completed by {request.user.get_full_name() or request.user.username}"
        if completion_notes:
            completion_note += f". Notes: {completion_notes}"
        
        _append_system_note(rental, completion_note)
        
        rental.save()
        rental.sync_machine_status()
        
        # Create notification for the customer
        create_notification(
            user=rental.user,
            title='Rental Completed',
            message=f'Your rental for {rental.machine.name} has been marked as completed.',
            notification_type='rental_completed',
            related_object_id=rental.id
        )
        
        # Notify operator if assigned
        if rental.assigned_operator:
            create_notification(
                user=rental.assigned_operator,
                title='Rental Completed',
                message=f'Rental for {rental.machine.name} has been completed by admin.',
                notification_type='rental_completed',
                related_object_id=rental.id
            )
        
        messages.success(
            request, 
            f'Rental for {rental.machine.name} has been marked as completed. Machine is now available for new bookings.'
        )
        
    except Exception as e:
        messages.error(request, f'Error completing rental: {str(e)}')
    
    return redirect(return_url)
