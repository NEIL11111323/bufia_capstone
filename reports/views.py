from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.contrib.auth import get_user_model
from machines.models import Rental, Machine, Maintenance
from users.models import MembershipApplication
from bufia.models import Payment
import csv
from datetime import datetime, timedelta

User = get_user_model()

def is_admin(user):
    """Check if user is admin or staff"""
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_admin)
def index(request):
    """Reports overview page."""
    total_rentals = Rental.objects.count()
    in_kind_rentals = Rental.objects.filter(payment_type='in_kind').count()
    completed_payments = Payment.objects.filter(status='completed').count()
    verified_members = User.objects.filter(is_verified=True).count()
    active_machines = Machine.objects.filter(status='available').count()

    context = {
        'overview_stats': {
            'total_rentals': total_rentals,
            'in_kind_rentals': in_kind_rentals,
            'completed_payments': completed_payments,
            'verified_members': verified_members,
            'active_machines': active_machines,
        }
    }
    return render(request, 'reports/index.html', context)

@login_required
@user_passes_test(is_admin)
def rental_report(request):
    """Generate rental transactions report with filters"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    machine_id = request.GET.get('machine')
    member_id = request.GET.get('member')
    status = request.GET.get('status')
    
    # Base query
    rentals = Rental.objects.select_related('machine', 'user').all()
    
    # Apply filters
    if start_date:
        rentals = rentals.filter(start_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    if machine_id:
        rentals = rentals.filter(machine_id=machine_id)
    if member_id:
        rentals = rentals.filter(user_id=member_id)
    if status:
        rentals = rentals.filter(status=status)
    
    # Calculate statistics
    stats = {
        'total': rentals.count(),
        'completed': rentals.filter(status='completed').count(),
        'active': rentals.filter(status='approved').count(),
        'pending': rentals.filter(status='pending').count(),
        'revenue': rentals.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    }
    
    context = {
        'rentals': rentals.order_by('-created_at'),
        'stats': stats,
        'machines': Machine.objects.all(),
        'members': User.objects.filter(is_verified=True),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'machine': machine_id,
            'member': member_id,
            'status': status
        }
    }
    return render(request, 'reports/rental_report.html', context)

@login_required
@user_passes_test(is_admin)
def harvest_report(request):
    """Generate harvest and BUFIA share report for IN-KIND rentals"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get IN-KIND rentals only
    rentals = Rental.objects.filter(
        payment_type='in_kind',
        status='completed'
    ).select_related('machine', 'user')
    
    if start_date:
        rentals = rentals.filter(end_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    
    # Calculate shares for each rental
    harvest_data = []
    total_harvested = 0
    total_bufia = 0
    total_member = 0
    outstanding = 0
    
    for rental in rentals:
        if rental.total_harvest_sacks:
            # BUFIA share = floor(total_sacks / 9)
            bufia_share = int(rental.total_harvest_sacks // 9)
            member_share = rental.total_harvest_sacks - bufia_share
            
            harvest_data.append({
                'rental': rental,
                'transaction_id': f'BUFIA-HRV-{rental.id:05d}',
                'bufia_share': bufia_share,
                'member_share': member_share,
                'collected': rental.organization_share_received or 0,
                'outstanding': bufia_share - (rental.organization_share_received or 0)
            })
            
            total_harvested += rental.total_harvest_sacks
            total_bufia += bufia_share
            total_member += member_share
            outstanding += bufia_share - (rental.organization_share_received or 0)
    
    context = {
        'harvest_data': harvest_data,
        'total_harvested': total_harvested,
        'total_bufia': total_bufia,
        'total_member': total_member,
        'outstanding': outstanding,
        'filters': {
            'start_date': start_date,
            'end_date': end_date
        }
    }
    return render(request, 'reports/harvest_report.html', context)

@login_required
@user_passes_test(is_admin)
def financial_summary(request):
    """Generate financial summary report"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get payments
    payments = Payment.objects.select_related('user').filter(status='completed')
    
    if start_date:
        payments = payments.filter(created_at__gte=start_date)
    if end_date:
        payments = payments.filter(created_at__lte=end_date)
    
    # Calculate income by type
    rental_income = payments.filter(payment_type='rental').aggregate(
        Sum('amount'))['amount__sum'] or 0
    
    # Membership income (₱500 per paid membership)
    membership_query = MembershipApplication.objects.filter(payment_status='paid')
    if start_date:
        membership_query = membership_query.filter(payment_date__gte=start_date)
    if end_date:
        membership_query = membership_query.filter(payment_date__lte=end_date)
    
    membership_count = membership_query.count()
    membership_income = membership_count * 500
    
    # Outstanding payments
    outstanding_query = Rental.objects.filter(
        payment_status__in=['pending', 'to_be_determined'],
        payment_type='cash'
    )
    if start_date:
        outstanding_query = outstanding_query.filter(created_at__gte=start_date)
    if end_date:
        outstanding_query = outstanding_query.filter(created_at__lte=end_date)
    
    outstanding = outstanding_query.aggregate(
        Sum('payment_amount'))['payment_amount__sum'] or 0
    
    stats = {
        'rental_income': rental_income,
        'membership_income': membership_income,
        'membership_count': membership_count,
        'total_revenue': rental_income + membership_income,
        'outstanding': outstanding
    }
    
    # Payment method distribution
    online_payments = payments.filter(stripe_session_id__isnull=False).count()
    face_to_face = payments.count() - online_payments
    
    context = {
        'payments': payments.order_by('-created_at'),
        'stats': stats,
        'online_payments': online_payments,
        'face_to_face': face_to_face,
        'filters': {
            'start_date': start_date,
            'end_date': end_date
        }
    }
    return render(request, 'reports/financial_summary.html', context)

@login_required
@user_passes_test(is_admin)
def machine_usage_report(request):
    """Generate machine usage and utilization report"""
    machine_id = request.GET.get('machine')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get machines
    machines = Machine.objects.all()
    if machine_id:
        machines = machines.filter(id=machine_id)
    
    usage_data = []
    for machine in machines:
        # Get rentals for this machine
        rentals = Rental.objects.filter(machine=machine)
        if start_date:
            rentals = rentals.filter(start_date__gte=start_date)
        if end_date:
            rentals = rentals.filter(end_date__lte=end_date)
        
        # Calculate usage
        total_rentals = rentals.count()
        total_days = sum(r.get_duration_days() for r in rentals)
        revenue = rentals.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
        
        # Get maintenance records
        maintenance = Maintenance.objects.filter(machine=machine)
        if start_date:
            maintenance = maintenance.filter(start_date__gte=start_date)
        if end_date:
            maintenance = maintenance.filter(end_date__lte=end_date)
        
        maintenance_count = maintenance.count()
        
        # Calculate utilization rate (simplified)
        if start_date and end_date:
            date_range = (datetime.strptime(end_date, '%Y-%m-%d') - 
                         datetime.strptime(start_date, '%Y-%m-%d')).days
            utilization_rate = (total_days / date_range * 100) if date_range > 0 else 0
        else:
            utilization_rate = 0
        
        usage_data.append({
            'machine': machine,
            'rental_count': total_rentals,
            'total_days': total_days,
            'revenue': revenue,
            'maintenance_count': maintenance_count,
            'utilization_rate': round(utilization_rate, 2)
        })
    
    # Sort by rental count (most used first)
    usage_data.sort(key=lambda x: x['rental_count'], reverse=True)

    usage_stats = {
        'machines': len(usage_data),
        'total_rentals': sum(item['rental_count'] for item in usage_data),
        'total_days': sum(item['total_days'] for item in usage_data),
        'total_revenue': sum(item['revenue'] for item in usage_data),
        'maintenance_count': sum(item['maintenance_count'] for item in usage_data),
    }
    
    context = {
        'usage_data': usage_data,
        'stats': usage_stats,
        'machines': Machine.objects.all(),
        'filters': {
            'machine': machine_id,
            'start_date': start_date,
            'end_date': end_date
        }
    }
    return render(request, 'reports/machine_usage_report.html', context)

@login_required
@user_passes_test(is_admin)
def membership_report(request):
    """Generate membership status report"""
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base query
    members = User.objects.all()
    
    # Apply status filter
    if filter_type == 'active':
        members = members.filter(is_verified=True)
    elif filter_type == 'pending':
        members = members.filter(membership_form_submitted=True, is_verified=False)
    elif filter_type == 'expired':
        members = members.filter(is_verified=False, membership_form_submitted=False)
    
    # Apply date filter
    if start_date:
        members = members.filter(date_joined__gte=start_date)
    if end_date:
        members = members.filter(date_joined__lte=end_date)
    
    # Calculate statistics
    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_verified=True).count(),
        'pending': User.objects.filter(
            membership_form_submitted=True, 
            is_verified=False
        ).count(),
        'new_members': members.count() if start_date else 0
    }
    
    context = {
        'members': members.order_by('-date_joined'),
        'stats': stats,
        'filter_type': filter_type,
        'filters': {
            'start_date': start_date,
            'end_date': end_date
        }
    }
    return render(request, 'reports/membership_report.html', context)

# Export Functions

@login_required
@user_passes_test(is_admin)
def export_rental_report(request):
    """Export rental report to CSV"""
    # Apply same filters as rental_report
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    machine_id = request.GET.get('machine')
    status = request.GET.get('status')
    
    rentals = Rental.objects.select_related('machine', 'user').all()
    
    if start_date:
        rentals = rentals.filter(start_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    if machine_id:
        rentals = rentals.filter(machine_id=machine_id)
    if status:
        rentals = rentals.filter(status=status)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rental_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Member Name', 'Machine', 'Start Date', 
        'End Date', 'Duration (days)', 'Area (ha)', 'Amount', 
        'Payment Status', 'Rental Status'
    ])
    
    for rental in rentals:
        transaction_id = rental.transaction_id or f'RENTAL-{rental.id:05d}'
        writer.writerow([
            transaction_id,
            rental.user.get_full_name(),
            rental.machine.name,
            rental.start_date,
            rental.end_date,
            rental.get_duration_days(),
            rental.area or 'N/A',
            rental.payment_amount or 0,
            rental.payment_status,
            rental.status
        ])
    
    return response

@login_required
@user_passes_test(is_admin)
def export_harvest_report(request):
    """Export harvest report to CSV"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    rentals = Rental.objects.filter(
        payment_type='in_kind',
        status='completed'
    ).select_related('machine', 'user')
    
    if start_date:
        rentals = rentals.filter(end_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="harvest_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Member Name', 'Machine', 'Harvest Date',
        'Total Sacks', 'BUFIA Share (1/9)', 'Member Share (8/9)',
        'Collected', 'Outstanding'
    ])
    
    for rental in rentals:
        if rental.total_harvest_sacks:
            bufia_share = int(rental.total_harvest_sacks // 9)
            member_share = rental.total_harvest_sacks - bufia_share
            collected = rental.organization_share_received or 0
            outstanding = bufia_share - collected
            
            writer.writerow([
                f'BUFIA-HRV-{rental.id:05d}',
                rental.user.get_full_name(),
                rental.machine.name,
                rental.end_date,
                rental.total_harvest_sacks,
                bufia_share,
                member_share,
                collected,
                outstanding
            ])
    
    return response

@login_required
@user_passes_test(is_admin)
def export_financial_report(request):
    """Export financial summary to CSV"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    payments = Payment.objects.select_related('user').filter(status='completed')
    
    if start_date:
        payments = payments.filter(created_at__gte=start_date)
    if end_date:
        payments = payments.filter(created_at__lte=end_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="financial_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Transaction ID', 'Member Name', 'Payment Type',
        'Amount', 'Payment Method', 'Status'
    ])
    
    for payment in payments:
        payment_method = 'Online' if payment.stripe_session_id else 'Face-to-Face'
        writer.writerow([
            payment.created_at.strftime('%Y-%m-%d'),
            payment.internal_transaction_id or 'N/A',
            payment.user.get_full_name(),
            payment.get_payment_type_display(),
            payment.amount,
            payment_method,
            payment.get_status_display()
        ])
    
    return response


# ============================================================================
# PHASE 6: SECTOR REPORTS
# ============================================================================

@login_required
@user_passes_test(is_admin)
def sector_member_list_report(request, pk):
    """Generate printable sector member list report"""
    from users.models import Sector
    
    sector = Sector.objects.get(pk=pk)
    
    # Get all approved members in this sector
    members = MembershipApplication.objects.select_related(
        'user'
    ).filter(
        assigned_sector=sector,
        is_approved=True
    ).order_by('user__last_name', 'user__first_name')
    
    context = {
        'sector': sector,
        'members': members,
        'total_members': members.count(),
        'report_date': timezone.now(),
        'report_title': f'Sector {sector.sector_number} - {sector.name} Member List',
    }
    
    return render(request, 'reports/sector_member_list.html', context)


@login_required
@user_passes_test(is_admin)
def sector_summary_report(request, pk):
    """Generate comprehensive sector summary report with statistics"""
    from users.models import Sector
    from django.db.models import Avg, Count, Sum
    
    sector = Sector.objects.get(pk=pk)
    
    # Get all approved members in this sector
    members = MembershipApplication.objects.filter(
        assigned_sector=sector,
        is_approved=True
    )
    
    # Member statistics
    total_members = members.count()
    verified_members = members.filter(user__is_verified=True).count()
    pending_members = members.filter(user__is_verified=False).count()
    
    # Gender distribution
    male_members = members.filter(gender='male').count()
    female_members = members.filter(gender='female').count()
    
    # Farm statistics
    total_farm_area = members.aggregate(Sum('farm_size'))['farm_size__sum'] or 0
    avg_farm_size = members.aggregate(Avg('farm_size'))['farm_size__avg'] or 0
    
    # Ownership distribution
    owner_count = members.filter(ownership_type='owner').count()
    tenant_count = members.filter(ownership_type='tenant').count()
    lessee_count = members.filter(ownership_type='lessee').count()
    
    # Payment statistics
    paid_members = members.filter(payment_status='paid').count()
    pending_payment = members.filter(payment_status='pending').count()
    payment_compliance_rate = (paid_members / total_members * 100) if total_members > 0 else 0
    
    # Equipment usage (rentals by members in this sector)
    equipment_usage = Rental.objects.filter(
        user__membershipapplication__assigned_sector=sector,
        user__membershipapplication__is_approved=True
    ).count()
    
    context = {
        'sector': sector,
        'total_members': total_members,
        'verified_members': verified_members,
        'pending_members': pending_members,
        'male_members': male_members,
        'female_members': female_members,
        'total_farm_area': round(total_farm_area, 2),
        'avg_farm_size': round(avg_farm_size, 2),
        'owner_count': owner_count,
        'tenant_count': tenant_count,
        'lessee_count': lessee_count,
        'paid_members': paid_members,
        'pending_payment': pending_payment,
        'payment_compliance_rate': round(payment_compliance_rate, 1),
        'equipment_usage': equipment_usage,
        'report_date': timezone.now(),
    }
    
    return render(request, 'reports/sector_summary.html', context)


@login_required
@user_passes_test(is_admin)
def sector_comparison_report(request):
    """Generate comparison report across all sectors"""
    from users.models import Sector
    from django.db.models import Avg, Count
    
    # Get all active sectors with statistics
    sectors = Sector.objects.filter(is_active=True).order_by('sector_number')
    
    sector_data = []
    for sector in sectors:
        members = MembershipApplication.objects.filter(
            assigned_sector=sector,
            is_approved=True
        )
        
        total_members = members.count()
        verified_members = members.filter(user__is_verified=True).count()
        avg_farm_size = members.aggregate(Avg('farm_size'))['farm_size__avg'] or 0
        paid_members = members.filter(payment_status='paid').count()
        payment_compliance = (paid_members / total_members * 100) if total_members > 0 else 0
        
        # Equipment usage
        equipment_usage = Rental.objects.filter(
            user__membershipapplication__assigned_sector=sector,
            user__membershipapplication__is_approved=True
        ).count()
        
        sector_data.append({
            'sector': sector,
            'total_members': total_members,
            'verified_members': verified_members,
            'avg_farm_size': round(avg_farm_size, 2),
            'payment_compliance': round(payment_compliance, 1),
            'equipment_usage': equipment_usage,
        })
    
    # Calculate totals
    total_members_all = sum(s['total_members'] for s in sector_data)
    total_verified_all = sum(s['verified_members'] for s in sector_data)
    avg_farm_size_all = sum(s['avg_farm_size'] * s['total_members'] for s in sector_data) / total_members_all if total_members_all > 0 else 0
    
    context = {
        'sector_data': sector_data,
        'total_members_all': total_members_all,
        'total_verified_all': total_verified_all,
        'avg_farm_size_all': round(avg_farm_size_all, 2),
        'report_date': timezone.now(),
    }
    
    return render(request, 'reports/sector_comparison.html', context)
