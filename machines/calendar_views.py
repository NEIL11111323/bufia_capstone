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
        
        # Get approved rentals (these block the machine)
        approved_rentals = Rental.objects.filter(
            machine=machine,
            status='approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('user')
        
        for rental in approved_rentals:
            events.append({
                'id': f'rental-{rental.id}',
                'title': f'Rented by {rental.user.get_full_name()}',
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),  # FullCalendar end is exclusive
                'backgroundColor': '#dc3545',  # Red for approved
                'borderColor': '#dc3545',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'approved',
                    'rentalId': rental.id,
                    'userName': rental.user.get_full_name(),
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
                'title': f'Pending: {rental.user.get_full_name()}',
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': '#ffc107',  # Yellow for pending
                'borderColor': '#ffc107',
                'textColor': '#000000',
                'extendedProps': {
                    'type': 'rental',
                    'status': 'pending',
                    'rentalId': rental.id,
                    'userName': rental.user.get_full_name(),
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
        
        # Get all approved rentals
        rentals = Rental.objects.filter(
            status='approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('user', 'machine')
        
        for rental in rentals:
            events.append({
                'id': f'rental-{rental.id}',
                'title': f'{rental.machine.name} - {rental.user.get_full_name()}',
                'start': rental.start_date.isoformat(),
                'end': (rental.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': '#dc3545',
                'borderColor': '#dc3545',
                'textColor': '#ffffff',
                'extendedProps': {
                    'type': 'rental',
                    'machineId': rental.machine.id,
                    'machineName': rental.machine.name,
                    'rentalId': rental.id,
                    'userName': rental.user.get_full_name(),
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
        
        # Check availability using the model method
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
                'conflict': {
                    'start_date': conflict.start_date.isoformat(),
                    'end_date': conflict.end_date.isoformat(),
                    'status': conflict.status,
                }
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
                'message': 'Machine has scheduled maintenance during this period',
                'maintenance': {
                    'start_date': maintenance.start_date.date().isoformat(),
                    'end_date': maintenance.end_date.date().isoformat() if maintenance.end_date else None,
                }
            })
        
        return JsonResponse({
            'available': True,
            'message': f'✅ Machine is available from {start_date} to {end_date}',
            'rental_days': (end_date - start_date).days + 1
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
