"""
Diesel Consumption Tracking Views
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from machines.models import Rental, Machine


def _is_operator(user):
    """Restrict diesel tracking to operator accounts only."""
    return user.is_authenticated and user.role == 'operator'


def _completed_diesel_queryset():
    """Rentals with diesel records that should count as completed fuel usage."""
    return Rental.objects.filter(
        diesel_cost__isnull=False,
        diesel_cost__gt=0,
    ).filter(
        Q(status__in=['completed', 'finalized']) |
        Q(workflow_state='completed') |
        Q(operator_status__in=['completed', 'harvest_reported']) |
        Q(settlement_status='paid')
    )


def _get_diesel_data(request):
    """Shared function to get diesel consumption data with filters"""
    # Get filter parameters
    date_filter = request.GET.get('date_filter', '30')
    machine_filter = request.GET.get('machine', '')
    machine_type_filter = request.GET.get('machine_type', '')
    operator_filter = request.GET.get('operator', '')
    
    # Base queryset
    rentals = _completed_diesel_queryset().select_related('machine', 'assigned_operator', 'user')
    
    # Apply date filter
    if date_filter == '7':
        start_date = timezone.now() - timedelta(days=7)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 7 Days'
    elif date_filter == '30':
        start_date = timezone.now() - timedelta(days=30)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 30 Days'
    elif date_filter == '90':
        start_date = timezone.now() - timedelta(days=90)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 90 Days'
    else:
        date_label = 'All Time'
    
    # Apply filters
    if machine_filter:
        rentals = rentals.filter(machine_id=machine_filter)
    if machine_type_filter:
        rentals = rentals.filter(machine__machine_type=machine_type_filter)
    if operator_filter:
        rentals = rentals.filter(assigned_operator_id=operator_filter)
    
    # If user is operator, show only their data
    if request.user.role == 'operator':
        rentals = rentals.filter(assigned_operator=request.user)
    
    # Calculate statistics
    total_diesel_cost = rentals.aggregate(total=Sum('diesel_cost'))['total'] or Decimal('0')
    total_jobs = rentals.count()
    avg_diesel_cost = rentals.aggregate(avg=Avg('diesel_cost'))['avg'] or Decimal('0')
    
    # Diesel by machine
    diesel_by_machine = rentals.values(
        'machine__name', 'machine__id'
    ).annotate(
        total_cost=Sum('diesel_cost'),
        job_count=Count('id'),
        avg_cost=Avg('diesel_cost')
    ).order_by('-total_cost')[:10]
    
    # Diesel by operator (admin only)
    diesel_by_operator = None
    if request.user.is_staff or request.user.is_superuser:
        diesel_by_operator = rentals.values(
            'assigned_operator__first_name',
            'assigned_operator__last_name',
            'assigned_operator__id'
        ).annotate(
            total_cost=Sum('diesel_cost'),
            job_count=Count('id'),
            avg_cost=Avg('diesel_cost')
        ).order_by('-total_cost')[:10]
    
    # Recent records
    recent_records = rentals.order_by('-actual_completion_time')[:20]
    
    return {
        'rentals': rentals,
        'total_diesel_cost': total_diesel_cost,
        'total_jobs': total_jobs,
        'avg_diesel_cost': avg_diesel_cost,
        'diesel_by_machine': diesel_by_machine,
        'diesel_by_operator': diesel_by_operator,
        'recent_records': recent_records,
        'date_label': date_label,
        'date_filter': date_filter,
        'machine_filter': machine_filter,
        'machine_type_filter': machine_type_filter,
        'operator_filter': operator_filter,
    }


@login_required
@user_passes_test(_is_operator)
def diesel_consumption_report(request):
    """
    Diesel cost tracking and reporting page
    """
    # Get filter parameters
    date_filter = request.GET.get('date_filter', '30')  # Default to last 30 days
    machine_filter = request.GET.get('machine', '')
    machine_type_filter = request.GET.get('machine_type', '')
    operator_filter = request.GET.get('operator', '')
    
    # Base queryset - only completed rentals with diesel data
    rentals = _completed_diesel_queryset().select_related('machine', 'assigned_operator', 'user')
    
    # Apply date filter
    if date_filter == '7':
        start_date = timezone.now() - timedelta(days=7)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 7 Days'
    elif date_filter == '30':
        start_date = timezone.now() - timedelta(days=30)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 30 Days'
    elif date_filter == '90':
        start_date = timezone.now() - timedelta(days=90)
        rentals = rentals.filter(actual_completion_time__gte=start_date)
        date_label = 'Last 90 Days'
    else:
        date_label = 'All Time'
    
    # Apply machine filter
    if machine_filter:
        rentals = rentals.filter(machine_id=machine_filter)
    
    # Apply machine type filter
    if machine_type_filter:
        rentals = rentals.filter(machine__machine_type=machine_type_filter)
    
    # Apply operator filter
    if operator_filter:
        rentals = rentals.filter(assigned_operator_id=operator_filter)
        date_label = 'Last 90 Days'
    else:
        date_label = 'All Time'
    
    # Apply machine filter
    if machine_filter:
        rentals = rentals.filter(machine_id=machine_filter)
    
    # Apply operator filter
    if operator_filter:
        rentals = rentals.filter(assigned_operator_id=operator_filter)
    
    # If user is operator, show only their data
    if request.user.role == 'operator':
        rentals = rentals.filter(assigned_operator=request.user)
    
    # Calculate summary statistics
    total_diesel_cost = rentals.aggregate(total=Sum('diesel_cost'))['total'] or Decimal('0')
    total_jobs = rentals.count()
    avg_diesel_cost = rentals.aggregate(avg=Avg('diesel_cost'))['avg'] or Decimal('0')
    
    # Diesel by machine
    diesel_by_machine = rentals.values(
        'machine__name',
        'machine__id'
    ).annotate(
        total_cost=Sum('diesel_cost'),
        job_count=Count('id'),
        avg_cost=Avg('diesel_cost')
    ).order_by('-total_cost')[:10]
    
    diesel_by_operator = None
    
    # Recent diesel consumption records
    recent_records = rentals.order_by('-actual_completion_time')[:20]
    
    # Get filter options
    machines = Machine.objects.filter(
        rentals__diesel_cost__isnull=False
    ).distinct().order_by('name')
    
    # Get machine types that have diesel records
    machine_types = Machine.objects.filter(
        rentals__diesel_cost__isnull=False
    ).values_list('machine_type', flat=True).distinct().order_by('machine_type')
    
    operators = None
    
    context = {
        'total_diesel_cost': total_diesel_cost,
        'total_jobs': total_jobs,
        'avg_diesel_cost': avg_diesel_cost,
        'diesel_by_machine': diesel_by_machine,
        'diesel_by_operator': diesel_by_operator,
        'recent_records': recent_records,
        'machines': machines,
        'machine_types': machine_types,
        'operators': operators,
        'date_filter': date_filter,
        'date_label': date_label,
        'machine_filter': machine_filter,
        'machine_type_filter': machine_type_filter,
        'operator_filter': operator_filter,
        'is_operator': True,
    }
    
    return render(request, 'machines/operator/diesel_consumption_report.html', context)


@login_required
@user_passes_test(_is_operator)
def diesel_consumption_print(request):
    """
    Print view for diesel consumption report
    """
    # Get diesel data with same filters
    data = _get_diesel_data(request)
    
    context = {
        **data,
        'is_operator': True,
        'now': timezone.now(),
    }
    
    return render(request, 'machines/operator/diesel_consumption_print.html', context)
