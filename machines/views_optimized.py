"""
Optimized views for machine rental system with proper transaction handling
and availability checking
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import json

from .models import Machine, Rental, Maintenance
from .forms import RentalForm
from notifications.models import UserNotification


@login_required
@transaction.atomic
def rental_create_optimized(request, machine_pk=None):
    """
    Optimized rental creation view with transaction safety and proper validation
    """
    if request.method == 'POST':
        form = RentalForm(request.POST)
        
        if form.is_valid():
            try:
                # Use select_for_update to lock the machine row
                machine = Machine.objects.select_for_update().get(
                    pk=form.cleaned_data['machine'].pk
                )
                
                # Double-check availability within transaction
                is_available, conflicts = Rental.check_availability(
                    machine=machine,
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date']
                )
                
                if not is_available:
                    conflict = conflicts.first()
                    messages.error(
                        request,
                        f'Sorry, this machine was just booked by another user from '
                        f'{conflict.start_date} to {conflict.end_date}. '
                        f'Please select different dates.'
                    )
                    return render(request, 'machines/rental_form.html', {
                        'form': form,
                        'action': 'Create',
                        'available_machines': Machine.objects.filter(status='available'),
                        'all_machines': Machine.objects.all(),
                    })
                
                # Create rental
                rental = form.save(commit=False)
                rental.user = request.user
                rental.save()
                
                # Create notification for user
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='rental_submitted',
                    message=f'Your rental request for {machine.name} has been submitted and is pending approval.',
                    related_object_id=rental.id
                )
                
                # Notify admins
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='rental_new_request',
                        message=f'New rental request from {request.user.get_full_name()} for {machine.name}',
                        related_object_id=rental.id
                    )
                
                messages.success(
                    request,
                    f'✅ Rental request submitted successfully! '
                    f'Your request for {machine.name} is pending approval.'
                )
                
                # Redirect to payment
                return redirect('create_rental_payment', rental_id=rental.pk)
                
            except Machine.DoesNotExist:
                messages.error(request, 'Selected machine does not exist.')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                
        else:
            # Handle form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = RentalForm(initial=initial)
    
    # Get machine object if machine_pk is provided
    machine = None
    if machine_pk:
        try:
            machine = Machine.objects.get(pk=machine_pk)
        except Machine.DoesNotExist:
            pass
    
    return render(request, 'machines/rental_form.html', {
        'form': form,
        'action': 'Create',
        'available_machines': Machine.objects.filter(status='available').order_by('name'),
        'all_machines': Machine.objects.all().order_by('name'),
        'machine': machine,
    })


@login_required
@require_http_methods(["POST"])
def check_availability_ajax(request):
    """
    AJAX endpoint to check machine availability in real-time
    Returns JSON with availability status and blocked dates
    """
    try:
        data = json.loads(request.body)
        machine_id = data.get('machine_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        # Validate inputs
        if not all([machine_id, start_date_str, end_date_str]):
            return JsonResponse({
                'available': False,
                'message': 'Missing required parameters',
                'errors': ['machine_id, start_date, and end_date are required']
            }, status=400)
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'available': False,
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'errors': ['Invalid date format']
            }, status=400)
        
        # Get machine
        try:
            machine = Machine.objects.get(pk=machine_id)
        except Machine.DoesNotExist:
            return JsonResponse({
                'available': False,
                'message': 'Machine not found',
                'errors': ['Machine does not exist']
            }, status=404)
        
        # Validate dates
        today = timezone.now().date()
        errors = []
        
        if start_date < today:
            errors.append('Start date cannot be in the past')
        
        if end_date < start_date:
            errors.append('End date must be after start date')
        
        if (end_date - start_date).days > 30:
            errors.append('Rental period cannot exceed 30 days')
        
        if errors:
            return JsonResponse({
                'available': False,
                'message': 'Invalid date range',
                'errors': errors
            })
        
        # Check availability
        is_available, conflicts = Rental.check_availability(
            machine=machine,
            start_date=start_date,
            end_date=end_date
        )
        
        if not is_available:
            conflict = conflicts.first()
            return JsonResponse({
                'available': False,
                'message': f'Machine is already booked from {conflict.start_date} to {conflict.end_date}',
                'conflicts': [{
                    'start_date': conflict.start_date.isoformat(),
                    'end_date': conflict.end_date.isoformat(),
                    'status': conflict.status,
                    'user': conflict.user.get_full_name()
                } for conflict in conflicts]
            })
        
        # Check maintenance
        maintenance_conflicts = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        )
        
        if maintenance_conflicts.exists():
            maintenance = maintenance_conflicts.first()
            return JsonResponse({
                'available': False,
                'message': f'Machine has scheduled maintenance',
                'maintenance': {
                    'start_date': maintenance.start_date.date().isoformat(),
                    'end_date': maintenance.end_date.date().isoformat() if maintenance.end_date else None,
                    'type': maintenance.maintenance_type
                }
            })
        
        # Get blocked dates for calendar
        blocked_dates = get_blocked_dates(machine, start_date, end_date + timedelta(days=30))
        
        return JsonResponse({
            'available': True,
            'message': f'✅ Machine is available from {start_date} to {end_date}',
            'rental_days': (end_date - start_date).days + 1,
            'blocked_dates': blocked_dates
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'available': False,
            'message': 'Invalid JSON data',
            'errors': ['Request body must be valid JSON']
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'available': False,
            'message': f'Server error: {str(e)}',
            'errors': [str(e)]
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_machine_blocked_dates(request, machine_id):
    """
    Get all blocked dates for a machine (for calendar display)
    """
    try:
        machine = Machine.objects.get(pk=machine_id)
        
        # Get date range from query params
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=90)
        
        blocked_dates = get_blocked_dates(machine, start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'machine': {
                'id': machine.id,
                'name': machine.name,
                'status': machine.status
            },
            'blocked_dates': blocked_dates
        })
        
    except Machine.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Machine not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def get_blocked_dates(machine, start_date, end_date):
    """
    Helper function to get all blocked dates for a machine
    """
    blocked_dates = []
    
    # Get rentals
    rentals = Rental.objects.filter(
        machine=machine,
        status__in=['approved', 'pending'],
        start_date__lte=end_date,
        end_date__gte=start_date
    ).order_by('start_date')
    
    for rental in rentals:
        blocked_dates.append({
            'start': rental.start_date.isoformat(),
            'end': rental.end_date.isoformat(),
            'type': 'rental',
            'status': rental.status,
            'title': f'Rented ({rental.get_status_display()})',
            'color': '#dc3545' if rental.status == 'approved' else '#ffc107'
        })
    
    # Get maintenance
    maintenances = Maintenance.objects.filter(
        machine=machine,
        status__in=['scheduled', 'in_progress'],
        start_date__date__lte=end_date,
        end_date__date__gte=start_date
    ).order_by('start_date')
    
    for maintenance in maintenances:
        blocked_dates.append({
            'start': maintenance.start_date.date().isoformat(),
            'end': maintenance.end_date.date().isoformat() if maintenance.end_date else maintenance.start_date.date().isoformat(),
            'type': 'maintenance',
            'status': maintenance.status,
            'title': f'Maintenance ({maintenance.get_maintenance_type_display()})',
            'color': '#fd7e14'
        })
    
    return blocked_dates


@login_required
def admin_approve_rental(request, rental_id):
    """
    Admin view to approve a rental with conflict checking
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to approve rentals.")
        return redirect('machines:rental_list')
    
    rental = get_object_or_404(Rental, pk=rental_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Lock the rental and machine
            rental = Rental.objects.select_for_update().get(pk=rental_id)
            machine = Machine.objects.select_for_update().get(pk=rental.machine_id)
            
            # Final availability check
            is_available, conflicts = Rental.check_availability(
                machine=machine,
                start_date=rental.start_date,
                end_date=rental.end_date,
                exclude_rental_id=rental.id
            )
            
            if not is_available:
                messages.error(
                    request,
                    f'Cannot approve: Machine has conflicting rental from '
                    f'{conflicts.first().start_date} to {conflicts.first().end_date}'
                )
                return redirect('machines:rental_detail', pk=rental_id)
            
            # Approve rental
            rental.status = 'approved'
            rental.save()
            
            # Update machine status if rental starts today or earlier
            today = timezone.now().date()
            if rental.start_date <= today <= rental.end_date:
                machine.status = 'rented'
                machine.save()
            
            # Notify user
            UserNotification.objects.create(
                user=rental.user,
                notification_type='rental_approved',
                message=f'Your rental request for {machine.name} has been approved!',
                related_object_id=rental.id
            )
            
            messages.success(
                request,
                f'✅ Rental approved for {rental.user.get_full_name()} - {machine.name}'
            )
            
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_approve.html', {'rental': rental})
