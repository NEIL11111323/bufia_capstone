import csv
from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from bufia.models import Payment
from machines.models import Machine, Maintenance, Rental
from users.models import MembershipApplication

User = get_user_model()


def is_admin(user):
    """Check if user is admin or staff."""
    return user.is_superuser or user.is_staff


RENTAL_COMPLETED_STATUSES = ['completed', 'finalized']
RENTAL_ACTIVE_STATUSES = ['approved', 'assigned', 'ongoing']


def _date_value(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _completed_harvest_rentals():
    return Rental.objects.filter(
        payment_type='in_kind',
        total_harvest_sacks__isnull=False,
    ).filter(
        Q(status__in=RENTAL_COMPLETED_STATUSES)
        | Q(workflow_state__in=['harvest_report_submitted', 'share_confirmed', 'completed'])
    ).select_related('machine', 'user')


def _harvest_row(rental):
    bufia_share = rental.required_bufia_share or Decimal('0.00')
    member_share = rental.member_share
    if member_share is None:
        _, member_share = rental.calculate_harvest_shares(rental.total_harvest_sacks)
    collected = rental.rice_delivered or Decimal('0.00')
    outstanding = max(bufia_share - collected, Decimal('0.00'))
    harvest_date = rental.operator_reported_at or rental.settlement_date or rental.actual_completion_time or rental.end_date

    return {
        'rental': rental,
        'transaction_id': rental.transaction_id or f'BUFIA-HRV-{rental.id:05d}',
        'bufia_share': bufia_share,
        'member_share': member_share or Decimal('0.00'),
        'collected': collected,
        'outstanding': outstanding,
        'harvest_date': harvest_date,
    }


@login_required
@user_passes_test(is_admin)
def index(request):
    """Reports overview page."""
    total_rentals = Rental.objects.count()
    in_kind_rentals = Rental.objects.filter(payment_type='in_kind').count()
    completed_payments = Payment.objects.filter(status='completed').count()
    verified_members = User.objects.filter(role=User.REGULAR_USER, is_verified=True).count()
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
    """Generate rental transactions report with filters."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    machine_id = request.GET.get('machine')
    member_id = request.GET.get('member')
    status = request.GET.get('status')

    rentals = Rental.objects.select_related('machine', 'user').all()

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

    stats = {
        'total': rentals.count(),
        'completed': rentals.filter(status__in=RENTAL_COMPLETED_STATUSES).count(),
        'active': rentals.filter(status__in=RENTAL_ACTIVE_STATUSES).count(),
        'pending': rentals.filter(status='pending').count(),
        'revenue': rentals.exclude(payment_type='in_kind').aggregate(
            Sum('payment_amount')
        )['payment_amount__sum'] or 0,
    }

    context = {
        'rentals': rentals.order_by('-created_at'),
        'stats': stats,
        'machines': Machine.objects.order_by('name'),
        'members': User.objects.filter(role=User.REGULAR_USER).order_by('last_name', 'first_name', 'username'),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'machine': machine_id,
            'member': member_id,
            'status': status,
        }
    }
    return render(request, 'reports/rental_report.html', context)


@login_required
@user_passes_test(is_admin)
def harvest_report(request):
    """Generate harvest and BUFIA share report for in-kind rentals."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    rentals = _completed_harvest_rentals()
    start_date_value = _date_value(start_date)
    end_date_value = _date_value(end_date)

    if start_date_value:
        rentals = rentals.filter(operator_reported_at__date__gte=start_date_value)
    if end_date_value:
        rentals = rentals.filter(operator_reported_at__date__lte=end_date_value)

    harvest_data = [_harvest_row(rental) for rental in rentals.order_by('-operator_reported_at', '-created_at')]
    total_harvested = sum((row['rental'].total_harvest_sacks or Decimal('0.00')) for row in harvest_data)
    total_bufia = sum((row['bufia_share'] or Decimal('0.00')) for row in harvest_data)
    total_member = sum((row['member_share'] or Decimal('0.00')) for row in harvest_data)
    outstanding = sum((row['outstanding'] or Decimal('0.00')) for row in harvest_data)

    context = {
        'harvest_data': harvest_data,
        'total_harvested': total_harvested,
        'total_bufia': total_bufia,
        'total_member': total_member,
        'outstanding': outstanding,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    return render(request, 'reports/harvest_report.html', context)


@login_required
@user_passes_test(is_admin)
def financial_summary(request):
    """Generate financial summary report."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    payments = Payment.objects.select_related('user').filter(status='completed')
    start_date_value = _date_value(start_date)
    end_date_value = _date_value(end_date)

    if start_date_value:
        payments = payments.filter(created_at__date__gte=start_date_value)
    if end_date_value:
        payments = payments.filter(created_at__date__lte=end_date_value)

    rental_income_query = Rental.objects.exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=True) | Q(payment_status='paid')
    )
    if start_date_value:
        rental_income_query = rental_income_query.filter(created_at__date__gte=start_date_value)
    if end_date_value:
        rental_income_query = rental_income_query.filter(created_at__date__lte=end_date_value)
    rental_income = rental_income_query.aggregate(
        Sum('payment_amount')
    )['payment_amount__sum'] or 0

    membership_query = MembershipApplication.objects.filter(payment_status='paid')
    if start_date_value:
        membership_query = membership_query.filter(payment_date__date__gte=start_date_value)
    if end_date_value:
        membership_query = membership_query.filter(payment_date__date__lte=end_date_value)
    membership_count = membership_query.count()
    membership_income = membership_count * 500

    outstanding_query = Rental.objects.exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=False) | Q(payment_status__in=['pending', 'to_be_determined'])
    ).exclude(status__in=['cancelled', 'rejected'])
    if start_date_value:
        outstanding_query = outstanding_query.filter(created_at__date__gte=start_date_value)
    if end_date_value:
        outstanding_query = outstanding_query.filter(created_at__date__lte=end_date_value)
    outstanding = outstanding_query.aggregate(
        Sum('payment_amount')
    )['payment_amount__sum'] or 0

    stats = {
        'rental_income': rental_income,
        'membership_income': membership_income,
        'membership_count': membership_count,
        'total_revenue': rental_income + membership_income,
        'outstanding': outstanding,
    }

    online_payments = payments.filter(stripe_session_id__isnull=False).count()
    face_to_face = payments.count() - online_payments

    context = {
        'payments': payments.order_by('-created_at'),
        'stats': stats,
        'online_payments': online_payments,
        'face_to_face': face_to_face,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    return render(request, 'reports/financial_summary.html', context)


@login_required
@user_passes_test(is_admin)
def machine_usage_report(request):
    """Generate machine usage and utilization report."""
    machine_id = request.GET.get('machine')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    machines = Machine.objects.all()
    if machine_id:
        machines = machines.filter(id=machine_id)

    usage_data = []
    for machine in machines:
        rentals = Rental.objects.filter(machine=machine)
        if start_date:
            rentals = rentals.filter(start_date__gte=start_date)
        if end_date:
            rentals = rentals.filter(end_date__lte=end_date)

        total_rentals = rentals.count()
        total_days = sum(r.get_duration_days() for r in rentals)
        revenue = rentals.exclude(payment_type='in_kind').aggregate(
            Sum('payment_amount')
        )['payment_amount__sum'] or 0

        maintenance = Maintenance.objects.filter(machine=machine)
        if start_date:
            maintenance = maintenance.filter(start_date__gte=start_date)
        if end_date:
            maintenance = maintenance.filter(end_date__lte=end_date)
        maintenance_count = maintenance.count()

        if start_date and end_date:
            date_range = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
            utilization_rate = (total_days / date_range * 100) if date_range > 0 else 0
        else:
            utilization_rate = 0

        usage_data.append({
            'machine': machine,
            'rental_count': total_rentals,
            'total_days': total_days,
            'revenue': revenue,
            'maintenance_count': maintenance_count,
            'utilization_rate': round(utilization_rate, 2),
        })

    usage_data.sort(key=lambda item: item['rental_count'], reverse=True)
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
            'end_date': end_date,
        }
    }
    return render(request, 'reports/machine_usage_report.html', context)


@login_required
@user_passes_test(is_admin)
def membership_report(request):
    """Generate membership status report."""
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    members = User.objects.filter(role=User.REGULAR_USER)
    if filter_type == 'active':
        members = members.filter(is_verified=True)
    elif filter_type == 'pending':
        members = members.filter(membership_form_submitted=True, is_verified=False)
    elif filter_type == 'expired':
        members = members.filter(is_verified=False, membership_form_submitted=False)

    if start_date:
        members = members.filter(date_joined__date__gte=start_date)
    if end_date:
        members = members.filter(date_joined__date__lte=end_date)

    member_base = User.objects.filter(role=User.REGULAR_USER)
    stats = {
        'total': member_base.count(),
        'active': member_base.filter(is_verified=True).count(),
        'pending': member_base.filter(membership_form_submitted=True, is_verified=False).count(),
        'new_members': members.count() if start_date or end_date else 0,
    }

    context = {
        'members': members.order_by('-date_joined'),
        'stats': stats,
        'filter_type': filter_type,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    return render(request, 'reports/membership_report.html', context)


@login_required
@user_passes_test(is_admin)
def export_rental_report(request):
    """Export rental report to CSV."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    machine_id = request.GET.get('machine')
    status = request.GET.get('status')
    member_id = request.GET.get('member')

    rentals = Rental.objects.select_related('machine', 'user').all()
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

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rental_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Member Name', 'Machine', 'Start Date',
        'End Date', 'Duration (days)', 'Area (ha)', 'Amount',
        'Payment Type', 'Payment Status', 'Rental Status',
    ])

    for rental in rentals.order_by('-created_at'):
        writer.writerow([
            rental.transaction_id or f'RENTAL-{rental.id:05d}',
            rental.user.get_full_name(),
            rental.machine.name,
            rental.start_date,
            rental.end_date,
            rental.get_duration_days(),
            rental.area or 'N/A',
            rental.payment_amount or 0,
            rental.workflow_payment_type_display(),
            rental.payment_status,
            rental.status,
        ])

    return response


@login_required
@user_passes_test(is_admin)
def export_harvest_report(request):
    """Export harvest report to CSV."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    rentals = _completed_harvest_rentals()
    start_date_value = _date_value(start_date)
    end_date_value = _date_value(end_date)
    if start_date_value:
        rentals = rentals.filter(operator_reported_at__date__gte=start_date_value)
    if end_date_value:
        rentals = rentals.filter(operator_reported_at__date__lte=end_date_value)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="harvest_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Member Name', 'Machine', 'Harvest Date',
        'Total Sacks', 'BUFIA Share', 'Member Share',
        'Delivered To BUFIA', 'Outstanding',
    ])

    for rental in rentals.order_by('-operator_reported_at', '-created_at'):
        row = _harvest_row(rental)
        writer.writerow([
            row['transaction_id'],
            rental.user.get_full_name(),
            rental.machine.name,
            row['harvest_date'],
            rental.total_harvest_sacks or 0,
            row['bufia_share'],
            row['member_share'],
            row['collected'],
            row['outstanding'],
        ])

    return response


@login_required
@user_passes_test(is_admin)
def export_financial_report(request):
    """Export financial summary to CSV."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    payments = Payment.objects.select_related('user').filter(status='completed')
    start_date_value = _date_value(start_date)
    end_date_value = _date_value(end_date)
    if start_date_value:
        payments = payments.filter(created_at__date__gte=start_date_value)
    if end_date_value:
        payments = payments.filter(created_at__date__lte=end_date_value)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="financial_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Transaction ID', 'Member Name', 'Payment Type',
        'Amount', 'Payment Method', 'Status',
    ])

    for payment in payments.order_by('-created_at'):
        writer.writerow([
            payment.created_at.strftime('%Y-%m-%d'),
            payment.internal_transaction_id or 'N/A',
            payment.user.get_full_name(),
            payment.get_payment_type_display(),
            payment.amount,
            'Online' if payment.stripe_session_id else 'Face-to-Face',
            payment.get_status_display(),
        ])

    return response


@login_required
@user_passes_test(is_admin)
def sector_member_list_report(request, pk):
    """Generate printable sector member list report."""
    from users.models import Sector

    sector = Sector.objects.get(pk=pk)
    members = MembershipApplication.objects.select_related('user').filter(
        assigned_sector=sector,
        is_approved=True,
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
    """Generate comprehensive sector summary report with statistics."""
    from users.models import Sector

    sector = Sector.objects.get(pk=pk)
    members = MembershipApplication.objects.filter(
        assigned_sector=sector,
        is_approved=True,
    )

    total_members = members.count()
    verified_members = members.filter(user__is_verified=True).count()
    pending_members = members.filter(user__is_verified=False).count()
    male_members = members.filter(gender='male').count()
    female_members = members.filter(gender='female').count()
    total_farm_area = members.aggregate(Sum('farm_size'))['farm_size__sum'] or 0
    avg_farm_size = members.aggregate(Avg('farm_size'))['farm_size__avg'] or 0
    owner_count = members.filter(ownership_type='owner').count()
    tenant_count = members.filter(ownership_type='tenant').count()
    lessee_count = members.filter(ownership_type='lessee').count()
    paid_members = members.filter(payment_status='paid').count()
    pending_payment = members.filter(payment_status='pending').count()
    payment_compliance_rate = (paid_members / total_members * 100) if total_members > 0 else 0
    equipment_usage = Rental.objects.filter(
        user__membership_application__assigned_sector=sector,
        user__membership_application__is_approved=True,
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
    """Generate comparison report across all sectors."""
    from users.models import Sector

    sectors = Sector.objects.filter(is_active=True).order_by('sector_number')
    sector_data = []

    for sector in sectors:
        members = MembershipApplication.objects.filter(
            assigned_sector=sector,
            is_approved=True,
        )
        total_members = members.count()
        verified_members = members.filter(user__is_verified=True).count()
        avg_farm_size = members.aggregate(Avg('farm_size'))['farm_size__avg'] or 0
        paid_members = members.filter(payment_status='paid').count()
        payment_compliance = (paid_members / total_members * 100) if total_members > 0 else 0
        equipment_usage = Rental.objects.filter(
            user__membership_application__assigned_sector=sector,
            user__membership_application__is_approved=True,
        ).count()

        sector_data.append({
            'sector': sector,
            'total_members': total_members,
            'verified_members': verified_members,
            'avg_farm_size': round(avg_farm_size, 2),
            'payment_compliance': round(payment_compliance, 1),
            'equipment_usage': equipment_usage,
        })

    total_members_all = sum(item['total_members'] for item in sector_data)
    total_verified_all = sum(item['verified_members'] for item in sector_data)
    avg_farm_size_all = (
        sum(item['avg_farm_size'] * item['total_members'] for item in sector_data) / total_members_all
        if total_members_all > 0 else 0
    )

    context = {
        'sector_data': sector_data,
        'total_members_all': total_members_all,
        'total_verified_all': total_verified_all,
        'avg_farm_size_all': round(avg_farm_size_all, 2),
        'report_date': timezone.now(),
    }
    return render(request, 'reports/sector_comparison.html', context)
