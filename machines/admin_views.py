"""
Admin views for rental approval and payment verification
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Count, Case, When, Value, IntegerField
from datetime import timedelta

from .models import Rental, Machine, Maintenance, HarvestReport, Settlement
from .forms_enhanced import (
    AdminRentalApprovalForm,
    HarvestReportForm,
    ConfirmRiceReceivedForm,
    FaceToFacePaymentForm,
)
from notifications.models import UserNotification
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


def _ensure_rental_payment_record(rental, *, status='pending', amount=None, paid_at=None):
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
    if target_amount is not None and payment.amount != target_amount:
        payment.amount = target_amount
        update_fields.append('amount')
    if payment.status != status:
        payment.status = status
        update_fields.append('status')
    if paid_at and payment.paid_at != paid_at:
        payment.paid_at = paid_at
        update_fields.append('paid_at')

    if update_fields:
        payment.save(update_fields=update_fields)
    return payment


def _complete_rental_after_payment(rental, admin_user, *, payment_status='paid'):
    """Finalize a non-in-kind rental after payment verification or recording."""
    completed_at = rental.payment_date or timezone.now()
    rental.payment_verified = True
    rental.payment_status = payment_status
    rental.status = 'completed'
    rental.workflow_state = 'completed'
    rental.verification_date = timezone.now()
    rental.verified_by = admin_user
    rental.actual_completion_time = completed_at
    rental.save(update_fields=[
        'payment_verified',
        'payment_status',
        'status',
        'workflow_state',
        'verification_date',
        'verified_by',
        'actual_completion_time',
        'updated_at',
    ])
    rental.sync_machine_status()
    return rental


@login_required
@user_passes_test(_is_admin)
def admin_rental_dashboard(request):
    """Main admin dashboard grouped by the rental transaction workflow."""
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    search_query = request.GET.get('search', '').strip()
    active_tab = request.GET.get('tab', '').strip()
    status_filter_labels = {
        'all': 'All',
        'pending': 'Pending',
        'approved': 'Approved',
        'completed': 'Completed',
        'rejected': 'Rejected',
        'cancelled': 'Cancelled',
    }
    payment_filter_labels = {
        'all': 'All',
        'online': 'Online Payment',
        'face_to_face': 'Face-to-Face Payment',
        'in_kind': 'IN-KIND Payment',
        'verified': 'Verified',
        'unverified': 'Unverified',
    }

    filtered_rentals = Rental.objects.select_related('machine', 'user').all()

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

    if search_query:
        filtered_rentals = filtered_rentals.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(machine__name__icontains=search_query)
        )

    tab_counts = {
        'pending': filtered_rentals.filter(status='pending').count(),
        'approved': filtered_rentals.filter(status='approved', workflow_state='approved').count(),
        'in_progress': filtered_rentals.filter(workflow_state='in_progress').count(),
        'completed': filtered_rentals.filter(
            Q(status='completed') |
            Q(workflow_state='completed') |
            Q(status='rejected') |
            Q(status='cancelled')
        ).count(),
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
        rentals = filtered_rentals.filter(status='approved', workflow_state='approved')
    elif active_tab == 'in_progress':
        rentals = filtered_rentals.filter(workflow_state='in_progress')
    else:
        rentals = filtered_rentals.filter(
            Q(status='completed') |
            Q(workflow_state='completed') |
            Q(status='rejected') |
            Q(status='cancelled')
        )

    rentals = rentals.annotate(
        status_priority=Case(
            When(status='pending', then=Value(1)),
            When(workflow_state='in_progress', then=Value(2)),
            When(status='approved', then=Value(3)),
            When(status='completed', then=Value(4)),
            default=Value(5),
            output_field=IntegerField()
        )
    ).order_by('-created_at', 'status_priority')

    harvest_settlement_queue = Rental.objects.select_related('machine', 'user').filter(
        payment_type='in_kind'
    ).exclude(
        Q(settlement_status='paid') | Q(status='cancelled')
    ).filter(
        Q(workflow_state='harvest_report_submitted') |
        Q(organization_share_required__isnull=False) |
        Q(workflow_state='in_progress')
    ).order_by('-created_at')

    stats = {
        'pending_requests': Rental.objects.filter(status='pending').count(),
        'approved_rentals': Rental.objects.filter(status='approved', workflow_state='approved').count(),
        'rentals_in_progress': Rental.objects.filter(workflow_state='in_progress').count(),
        'harvest_settlements': harvest_settlement_queue.count(),
        'completed_rentals': Rental.objects.filter(
            Q(status='completed') | Q(workflow_state='completed')
        ).count(),
    }

    from django.core.paginator import Paginator
    paginator = Paginator(rentals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'status_filter_label': status_filter_labels.get(status_filter, status_filter),
        'payment_filter_label': payment_filter_labels.get(payment_filter, payment_filter),
        'search_query': search_query,
        'active_tab': active_tab,
        'tab_counts': tab_counts,
        'active_tab_count': tab_counts.get(active_tab, 0),
        'has_active_filters': status_filter != 'all' or payment_filter != 'all' or bool(search_query),
        'in_kind_verification_queue': harvest_settlement_queue[:10],
        'in_kind_verification_count': harvest_settlement_queue.count(),
    }

    return render(request, 'machines/admin/rental_dashboard.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_approve_rental(request, rental_id):
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
                
                # Check if there are other active rentals for this machine
                other_active_rentals = Rental.objects.filter(
                    machine=rental.machine,
                    status='approved'
                ).exclude(pk=rental.id).exists()
                
                # If no other active rentals, make machine available
                if not other_active_rentals:
                    rental.machine.status = 'available'
                    rental.machine.save()
                
                # Notify user
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_completed',
                    message=f'✅ Your rental for {rental.machine.name} has been marked as completed. Thank you for using BUFIA services!',
                    related_object_id=rental.id
                )
                
                messages.success(
                    request,
                    f'✅ Rental marked as completed for {rental.user.get_full_name()} - {rental.machine.name}. Machine is now available for booking.'
                )
                
            elif rental.status == 'approved':
                # Ensure workflow state follows admin action
                if rental.workflow_state == 'requested':
                    rental.workflow_state = 'approved'
                
                # Notify user of approval
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_approved',
                    message=f'✅ Your rental for {rental.machine.name} has been approved! '
                            f'Dates: {rental.start_date} to {rental.end_date}',
                    related_object_id=rental.id
                )
                
                messages.success(
                    request,
                    f'✅ Rental approved for {rental.user.get_full_name()} - {rental.machine.name}'
                )
                
            elif rental.status == 'rejected':
                # Notify user of rejection
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_rejected',
                    message=f'❌ Your rental request for {rental.machine.name} has been rejected. '
                            f'Please contact admin for more information.',
                    related_object_id=rental.id
                )
                
                messages.warning(
                    request,
                    f'Rental rejected for {rental.user.get_full_name()} - {rental.machine.name}'
                )
            
            elif rental.status == 'cancelled':
                # Handle cancellation
                rental.workflow_state = 'cancelled'
                
                # Check if there are other active rentals for this machine
                other_active_rentals = Rental.objects.filter(
                    machine=rental.machine,
                    status='approved'
                ).exclude(pk=rental.id).exists()
                
                # If no other active rentals, make machine available
                if not other_active_rentals:
                    rental.machine.status = 'available'
                    rental.machine.save()
                
                messages.info(
                    request,
                    f'Rental cancelled for {rental.user.get_full_name()} - {rental.machine.name}'
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
        messages.error(request, 'Harvest reporting applies only to IN-KIND rentals.')
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
        messages.error(request, 'Rice confirmation applies only to IN-KIND rentals.')
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
        
        # Update machine status to available
        rental.machine.status = 'available'
        rental.machine.save(update_fields=['status', 'updated_at'])
        
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
                f'✅ IN-KIND settlement completed for {rental.machine.name}. '
                f'Rice delivered: {rental.organization_share_received} sacks. '
                f'Reference: {rental.settlement_reference}. Rental is now completed.'
            ),
            related_object_id=rental.id
        )
        messages.success(
            request, 
            f'✅ Rice delivery confirmed ({rental.organization_share_received} sacks). '
            f'Settlement marked as PAID (IN-KIND). Rental automatically completed. '
            f'Machine {rental.machine.name} is now available.'
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
                f'IN-KIND settlement confirmed for {rental.machine.name}. '
                f'Reference: {rental.settlement_reference}.'
            ),
            related_object_id=rental.id
        )
        messages.success(request, 'Rice delivery confirmed and settlement marked as PAID (IN-KIND).')
    
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
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )

    if request.method == 'POST':
        form = AdminRentalApprovalForm(request.POST, instance=rental)
        if form.is_valid():
            rental = form.save(commit=False)

            if rental.status == 'approved':
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
                    success_message = (
                        f'Rental approved for {rental.user.get_full_name()} - {rental.machine.name}. '
                        'Harvest settlement will be completed after operation and rice delivery.'
                    )
                elif rental.payment_method == 'face_to_face':
                    rental.payment_status = 'pending'
                    success_message = (
                        f'Rental approved for {rental.user.get_full_name()} - {rental.machine.name}. '
                        'Waiting for face-to-face payment recording.'
                    )
                else:
                    rental.payment_status = 'pending'
                    success_message = (
                        f'Rental approved for {rental.user.get_full_name()} - {rental.machine.name}. '
                        'Waiting for online payment.'
                    )

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
                messages.success(request, success_message)

            elif rental.status == 'completed':
                _complete_rental_after_payment(rental, request.user)
                UserNotification.objects.create(
                    user=rental.user,
                    notification_type='rental_completed',
                    message=f'Your rental for {rental.machine.name} has been marked as completed.',
                    related_object_id=rental.id
                )
                messages.success(
                    request,
                    f'Rental marked as completed for {rental.user.get_full_name()} - {rental.machine.name}.'
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
                    f'Rental rejected for {rental.user.get_full_name()} - {rental.machine.name}'
                )

            elif rental.status == 'cancelled':
                rental.workflow_state = 'cancelled'
                rental.save()
                rental.sync_machine_status()
                messages.info(
                    request,
                    f'Rental cancelled for {rental.user.get_full_name()} - {rental.machine.name}'
                )

            return redirect('machines:rental_list')
    else:
        form = AdminRentalApprovalForm(instance=rental)

    is_available, conflicts = Rental.check_availability_for_approval(
        machine=rental.machine,
        start_date=rental.start_date,
        end_date=rental.end_date,
        exclude_rental_id=rental.id
    )

    context = {
        'rental': rental,
        'form': form,
        'face_to_face_form': FaceToFacePaymentForm(instance=rental),
        'operator_candidates': User.objects.filter(is_active=True, is_staff=True, is_superuser=False).order_by('first_name', 'last_name', 'username'),
        'has_conflicts': not is_available,
        'conflicts': conflicts if not is_available else None,
    }
    return render(request, 'machines/admin/rental_approval.html', context)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def start_equipment_operation(request, rental_id):
    """Move an approved in-kind rental into active operation."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if rental.workflow_state != 'approved':
        messages.error(request, 'Only approved IN-KIND rentals can be started.')
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
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def submit_harvest_report(request, rental_id):
    """Record the harvest for an in-kind rental and compute settlement shares."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Harvest reporting applies only to IN-KIND rentals.')
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
        f'✅ Harvest recorded. Total harvest: {rental.total_harvest_sacks} sacks. '
        f'BUFIA share: {rental.bufia_share} sacks. Member share: {rental.member_share} sacks.'
    )
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def confirm_rice_received(request, rental_id):
    """Record rice delivery and automatically complete a settled in-kind rental."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )
    if rental.payment_type != 'in_kind':
        messages.error(request, 'Rice confirmation applies only to IN-KIND rentals.')
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
        rental.payment_status = 'pending'
        rental.settlement_status = 'waiting_for_delivery'
        rental.save(update_fields=['payment_status', 'settlement_status', 'updated_at'])
        messages.warning(
            request,
            f'Rice delivery recorded. {remaining} sack(s) still need to be delivered before completion.'
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
    rental.actual_completion_time = timezone.now()
    rental.save(update_fields=[
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
        'actual_completion_time',
        'updated_at',
    ])
    rental.sync_machine_status()

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'IN-KIND settlement completed for {rental.machine.name}. '
            f'Transaction: {rental.transaction_reference}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, 'Rice delivery confirmed. Rental automatically marked as completed.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def verify_online_payment(request, rental_id):
    """Verify a completed online payment and complete the rental."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if rental.payment_method != 'online':
        messages.error(request, 'This action only applies to online payments.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if not rental.payment_date and not rental.stripe_session_id:
        messages.error(request, 'No online payment record was found for this rental.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    payment = _ensure_rental_payment_record(
        rental,
        status='completed',
        amount=rental.payment_amount,
        paid_at=rental.payment_date or timezone.now(),
    )
    _complete_rental_after_payment(rental, request.user)

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'Your online payment for {rental.machine.name} has been verified. '
            f'Transaction ID: {payment.internal_transaction_id}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, 'Online payment verified. Rental marked as completed.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def record_face_to_face_payment(request, rental_id):
    """Record a face-to-face payment and complete the rental."""
    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )

    if rental.payment_method != 'face_to_face':
        messages.error(request, 'This action only applies to face-to-face payments.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

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
    )
    _complete_rental_after_payment(rental, request.user)

    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_payment_completed',
        message=(
            f'Your face-to-face payment for {rental.machine.name} has been recorded. '
            f'Receipt No.: {rental.receipt_number}. Transaction ID: {payment.internal_transaction_id}.'
        ),
        related_object_id=rental.id
    )
    messages.success(request, 'Face-to-face payment recorded. Rental marked as completed.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@user_passes_test(_is_admin)
def verify_payment_ajax(request, rental_id):
    """AJAX endpoint to verify online payments from the dashboard."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)

    try:
        rental = Rental.objects.get(pk=rental_id)
        if rental.payment_method != 'online':
            return JsonResponse({'success': False, 'message': 'Only online payments can be verified here.'}, status=400)
        if not rental.payment_date and not rental.stripe_session_id:
            return JsonResponse({'success': False, 'message': 'No online payment record found.'}, status=400)

        payment = _ensure_rental_payment_record(
            rental,
            status='completed',
            amount=rental.payment_amount,
            paid_at=rental.payment_date or timezone.now(),
        )
        _complete_rental_after_payment(rental, request.user)

        return JsonResponse({
            'success': True,
            'verified': True,
            'transaction_id': payment.internal_transaction_id,
            'message': 'Payment verified and rental completed.',
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
    
    # Find overlapping approved rentals (should not exist but check anyway)
    all_approved = Rental.objects.filter(
        status='approved',
        end_date__gte=today
    ).select_related('machine', 'user').order_by('start_date')
    
    conflicts = []
    for rental in all_approved:
        overlapping = Rental.objects.filter(
            machine=rental.machine,
            status='approved',
            start_date__lt=rental.end_date,
            end_date__gt=rental.start_date
        ).exclude(pk=rental.pk)
        
        if overlapping.exists():
            conflicts.append({
                'rental': rental,
                'conflicts_with': list(overlapping)
            })
    
    # Find pending rentals that would conflict if approved
    pending_conflicts = []
    pending_rentals = Rental.objects.filter(
        status='pending',
        payment_verified=True
    ).select_related('machine', 'user')
    
    for rental in pending_rentals:
        is_available, conf = Rental.check_availability_for_approval(
            rental.machine,
            rental.start_date,
            rental.end_date,
            exclude_rental_id=rental.id
        )
        
        if not is_available:
            pending_conflicts.append({
                'rental': rental,
                'conflicts_with': list(conf)
            })
    
    # Popular machines
    popular_machines = Machine.objects.annotate(
        booking_count=Count('rentals', filter=Q(
            rentals__status='approved',
            rentals__start_date__gte=today - timedelta(days=30)
        ))
    ).filter(booking_count__gt=0).order_by('-booking_count')[:10]
    
    context = {
        'conflicts': conflicts,
        'pending_conflicts': pending_conflicts,
        'popular_machines': popular_machines,
        'total_conflicts': len(conflicts),
        'total_pending_conflicts': len(pending_conflicts),
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
                    message=f'✅ Your rental for {rental.machine.name} has been approved!',
                    related_object_id=rental.id
                )
                
                approved_count += 1
                
        except Exception as e:
            messages.error(request, f'Error approving Rental #{rental_id}: {str(e)}')
            failed_count += 1
    
    if approved_count > 0:
        messages.success(request, f'✅ Successfully approved {approved_count} rental(s)')
    
    if failed_count > 0:
        messages.warning(request, f'⚠️ Failed to approve {failed_count} rental(s)')
    
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
        messages.success(request, f'✅ Successfully deleted {deleted_count} rental(s)')
    
    if failed_count > 0:
        messages.warning(request, f'⚠️ Failed to delete {failed_count} rental(s)')
    
    return redirect('machines:rental_list')



# IN-KIND Workflow Admin Views

@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_in_kind_dashboard(request):
    """
    Admin dashboard for IN-KIND rental workflow management
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
    Approve an IN-KIND rental request (transition requested → pending_approval → approved)
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
            f'✅ Rental approved for {rental.user.get_full_name()} - {rental.machine.name}'
        )
    except Exception as e:
        messages.error(request, f'Error approving rental: {str(e)}')
    
    return redirect('machines:admin_in_kind_dashboard')


@login_required
@user_passes_test(_is_admin)
@transaction.atomic
def admin_reject_in_kind_rental(request, rental_id):
    """
    Reject an IN-KIND rental request (transition to cancelled)
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
            f'Rental rejected for {rental.user.get_full_name()} - {rental.machine.name}'
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
            f'✅ Equipment operation started for {rental.machine.name}'
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
                f'✅ Harvest report recorded: {total_sacks} sacks. '
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
                f'✅ Harvest report verified and settlement created. '
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
                f'✅ Rental completed early. Machine {rental.machine.name} '
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
    """Block manual completion for IN-KIND rentals."""
    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user'),
        pk=rental_id,
        payment_type='in_kind'
    )
    messages.error(
        request,
        'IN-KIND rentals are completed automatically after the required rice share is recorded.'
    )
    return redirect('machines:admin_approve_rental', rental_id=rental.id)



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
    
    # Get recent assignments for each operator
    for operator in operators:
        operator.recent_rentals = operator.operator_rentals.select_related(
            'machine', 'user'
        ).filter(
            status__in=['approved', 'in_progress']
        ).order_by('-start_date')[:5]
        
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
    
    context = {
        'operators': operators,
        'total_operators': total_operators,
        'available_operators': available_operators,
        'busy_operators': busy_operators,
    }
    
    return render(request, 'machines/admin/operator_overview.html', context)
