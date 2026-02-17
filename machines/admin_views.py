"""
Admin views for rental approval and payment verification
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Count
from datetime import timedelta

from .models import Rental, Machine, Maintenance
from .forms_enhanced import AdminRentalApprovalForm
from notifications.models import UserNotification


def _is_admin(user):
    """Check if user is admin or staff"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(_is_admin)
def admin_rental_dashboard(request):
    """
    Main admin dashboard showing pending rentals with payment verification
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    rentals = Rental.objects.select_related('machine', 'user').all()
    
    # Apply filters
    if status_filter and status_filter != 'all':
        rentals = rentals.filter(status=status_filter)
    
    if payment_filter == 'verified':
        rentals = rentals.filter(payment_verified=True)
    elif payment_filter == 'unverified':
        rentals = rentals.filter(payment_verified=False)
    elif payment_filter == 'with_proof':
        rentals = rentals.exclude(payment_slip='')
    
    if search_query:
        rentals = rentals.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(machine__name__icontains=search_query)
        )
    
    # Order by priority: pending first (with paid pending at top), then approved, then by date
    from django.db.models import Case, When, Value, IntegerField
    
    rentals = rentals.annotate(
        status_priority=Case(
            When(status='pending', payment_verified=True, then=Value(1)),
            When(status='pending', payment_verified=False, then=Value(2)),
            When(status='approved', then=Value(3)),
            When(status='rejected', then=Value(4)),
            When(status='cancelled', then=Value(5)),
            default=Value(6),
            output_field=IntegerField()
        )
    ).order_by('status_priority', '-created_at')
    
    # Get statistics
    stats = {
        'total_pending': Rental.objects.filter(status='pending').count(),
        'paid_pending': Rental.objects.filter(
            status='pending',
            payment_verified=True
        ).count(),
        'unpaid_pending': Rental.objects.filter(
            status='pending',
            payment_verified=False
        ).count(),
        'with_payment_proof': Rental.objects.filter(
            status='pending'
        ).exclude(payment_slip='').count(),
        'confirmed_requests': Rental.objects.filter(status='approved').count(),
        'total_requests': Rental.objects.all().count(),
    }
    
    # Paginate
    from django.core.paginator import Paginator
    paginator = Paginator(rentals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'search_query': search_query,
        'today': timezone.now().date(),
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
            rental.save()
            
            # Create notifications based on status
            if rental.status == 'approved':
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
        else:
            rental.verification_date = None
            rental.verified_by = None
        
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
    
    approved_count = 0
    failed_count = 0
    
    for rental_id in rental_ids:
        try:
            with transaction.atomic():
                rental = Rental.objects.select_for_update().get(pk=rental_id)
                
                # Check if can be approved
                if not rental.payment_verified:
                    messages.warning(
                        request,
                        f'Skipped Rental #{rental_id}: Payment not verified'
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
                
                # Approve
                rental.status = 'approved'
                rental.verified_by = request.user
                rental.save()
                
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
    
    return redirect('machines:rental_list')


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
