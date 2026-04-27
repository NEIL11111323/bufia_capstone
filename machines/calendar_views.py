"""
Calendar views for machine rental availability
Provides JSON endpoints for FullCalendar integration
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Machine, Rental, Maintenance


def _calendar_rental_title(rental):
    if (rental.purpose or '').startswith('Package:'):
        return 'Package Reserve'
    return 'Approved Booking' if rental.status == 'approved' else 'Pending Request'


def _calendar_user_can_view_private_statuses(request, rental):
    return (
        request.user.is_staff or
        request.user.is_superuser or
        rental.user_id == request.user.id
    )


def _get_schedule_blocking_rentals(*, machine=None, start_date=None, end_date=None):
    rentals = Rental.objects.filter(status='approved').exclude(
        workflow_state__in=['completed', 'cancelled']
    ).select_related('user', 'machine')

    if machine is not None:
        rentals = rentals.filter(machine=machine)
    if end_date is not None:
        rentals = rentals.filter(start_date__lte=end_date)

    if start_date is None or end_date is None:
        return [rental for rental in rentals if rental.is_schedule_blocking]

    return [
        rental for rental in rentals
        if rental.is_schedule_blocking and rental.overlaps_schedule(start_date, end_date)
    ]


@login_required
@require_http_methods(["GET"])
def machine_calendar_events(request, machine_id):
    """
    Get all calendar events (rentals and maintenance) for a specific machine
    Returns data in FullCalendar event format
    """
    try:
        machine = Machine.objects.get(pk=machine_id)
        
        # Get date range from query params (FullCalendar sends these)
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        if start_str and end_str:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
        else:
            # Default to 3 months range
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=90)
        
        events = []
        
        approved_rentals = _get_schedule_blocking_rentals(
            machine=machine,
            start_date=start_date,
            end_date=end_date,
        )

        for rental in approved_rentals:
            events.append({
                'id': f'rental-{rental.id}',
                'title': _calendar_rental_title(rental),
                'start': rental.start_date.isoformat(),
                'end': ((rental.effective_end_date or rental.end_date) + timedelta(days=1)).isoformat(),  # FullCalendar end is exclusive
                'backgroundColor': '#16a34a',
                'borderColor': '#16a34a',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'approved',
                    'rentalId': rental.id,
                    'userName': rental.customer_display_name,
                    'visibility': 'shared',
                }
            })
        
        # Get pending rentals (shown differently)
        pending_rentals = Rental.objects.filter(
            machine=machine,
            status='pending',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('user')

        for rental in pending_rentals:
            events.append({
                'id': f'rental-pending-{rental.id}',
                'title': _calendar_rental_title(rental),
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': '#facc15',
                'borderColor': '#eab308',
                'textColor': '#422006',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'pending',
                    'rentalId': rental.id,
                    'userName': rental.customer_display_name,
                    'visibility': 'shared',
                }
            })

        private_status_rentals = Rental.objects.filter(
            machine=machine,
            status__in=['rejected', 'cancelled'],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('user')

        for rental in private_status_rentals:
            if not _calendar_user_can_view_private_statuses(request, rental):
                continue

            is_rejected = rental.status == 'rejected'
            events.append({
                'id': f'rental-private-{rental.id}',
                'title': 'Rejected Request' if is_rejected else 'Cancelled Request',
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': '#ef4444' if is_rejected else '#94a3b8',
                'borderColor': '#dc2626' if is_rejected else '#64748b',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'rental',
                    'status': rental.status,
                    'rentalId': rental.id,
                    'userName': rental.customer_display_name,
                    'visibility': 'private',
                }
            })
        
        # Get maintenance schedules
        maintenances = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        )
        
        for maintenance in maintenances:
            events.append({
                'id': f'maintenance-{maintenance.id}',
                'title': f'Maintenance: {maintenance.get_maintenance_type_display()}',
                'start': maintenance.start_date.date().isoformat(),
                'end': (maintenance.end_date.date() + timedelta(days=1)).isoformat() if maintenance.end_date else None,
                'backgroundColor': '#fd7e14',  # Orange for maintenance
                'borderColor': '#fd7e14',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'maintenance',
                    'maintenanceId': maintenance.id,
                    'maintenanceType': maintenance.maintenance_type,
                }
            })
        
        return JsonResponse(events, safe=False)
        
    except Machine.DoesNotExist:
        return JsonResponse({'error': 'Machine not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def all_machines_calendar_events(request):
    """
    Get calendar events for all machines
    Useful for admin dashboard showing all rentals
    """
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        if start_str and end_str:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
        else:
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=90)
        
        events = []
        
        approved_rentals = _get_schedule_blocking_rentals(
            start_date=start_date,
            end_date=end_date,
        )
        pending_rentals = Rental.objects.filter(
            status='pending',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('user', 'machine')

        for rental in approved_rentals:
            events.append({
                'id': f'rental-{rental.id}',
                'title': f'{rental.machine.name} - {_calendar_rental_title(rental)}',
                'start': rental.start_date.isoformat(),
                'end': ((rental.effective_end_date or rental.end_date) + timedelta(days=1)).isoformat(),
                'backgroundColor': '#16a34a',
                'borderColor': '#16a34a',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'approved',
                    'machineId': rental.machine.id,
                    'machineName': rental.machine.name,
                    'rentalId': rental.id,
                    'userName': rental.customer_display_name,
                }
            })

        for rental in pending_rentals:
            events.append({
                'id': f'rental-pending-{rental.id}',
                'title': f'{rental.machine.name} - {_calendar_rental_title(rental)}',
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': '#facc15',
                'borderColor': '#eab308',
                'textColor': '#422006',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'pending',
                    'machineId': rental.machine.id,
                    'machineName': rental.machine.name,
                    'rentalId': rental.id,
                    'userName': rental.customer_display_name,
                }
            })
        
        return JsonResponse(events, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def check_date_availability(request):
    """
    Check if a machine is available for specific dates
    Used for real-time validation as user selects dates
    """
    import json
    
    try:
        data = json.loads(request.body)
        machine_id = data.get('machine_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not all([machine_id, start_date_str, end_date_str]):
            return JsonResponse({
                'available': False,
                'message': 'Missing required parameters'
            }, status=400)
        
        machine = Machine.objects.get(pk=machine_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Validate dates
        today = timezone.now().date()
        if start_date < today:
            return JsonResponse({
                'available': False,
                'message': 'Start date cannot be in the past'
            })
        
        if end_date < start_date:
            return JsonResponse({
                'available': False,
                'message': 'End date must be after start date'
            })
        
        exclude_rental_id = data.get('exclude_rental_id')
        if exclude_rental_id not in [None, '']:
            try:
                exclude_rental_id = int(exclude_rental_id)
            except (TypeError, ValueError):
                return JsonResponse({
                    'available': False,
                    'message': 'Invalid exclude_rental_id'
                }, status=400)
        else:
            exclude_rental_id = None

        is_available, approved_conflicts = Rental.check_availability(
            machine=machine,
            start_date=start_date,
            end_date=end_date,
            exclude_rental_id=exclude_rental_id,
        )

        if not is_available:
            conflict = approved_conflicts.first()
            conflict_end = conflict.effective_end_date or conflict.end_date
            return JsonResponse({
                'available': False,
                'message': f'Machine is already booked from {conflict.start_date} to {conflict_end}',
                'conflict': {
                    'start_date': conflict.start_date.isoformat(),
                    'end_date': conflict_end.isoformat(),
                    'status': 'approved',
                    'title': _calendar_rental_title(conflict),
                }
            })

        pending_conflicts = Rental.get_pending_overlaps(
            machine=machine,
            start_date=start_date,
            end_date=end_date,
            exclude_rental_id=exclude_rental_id,
        )
        
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
                'message': 'Machine has scheduled maintenance during this period',
                'maintenance': {
                    'start_date': maintenance.start_date.date().isoformat(),
                    'end_date': maintenance.end_date.date().isoformat() if maintenance.end_date else None,
                }
            })
        
        return JsonResponse({
            'available': True,
            'message': f'Machine is available from {start_date} to {end_date}',
            'rental_days': (end_date - start_date).days + 1,
            'warning': (
                'This date has a pending request. It may not be available.'
                if pending_conflicts.exists() else ''
            ),
            'pending_conflict_count': pending_conflicts.count(),
        })
        
    except Machine.DoesNotExist:
        return JsonResponse({
            'available': False,
            'message': 'Machine not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'available': False,
            'message': f'Error: {str(e)}'
        }, status=500)
