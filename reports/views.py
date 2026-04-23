import csv
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
import re
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Avg, F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bufia.models import Payment, Refund
from reports.forms import RiceOrderPaymentForm, RicePurchaseForm, RiceSaleSettingForm
from reports.export_utils import build_pdf_bytes, build_xlsx_bytes
from machines.models import DryerRental, Machine, Maintenance, RiceMillAppointment, Rental
from reports.models import RiceSale, RiceSaleSetting
from users.forms import MembershipProofUploadForm
from users.models import MembershipApplication
from users.views import _append_membership_application_proofs, _sync_membership_application_proofs

User = get_user_model()


def is_admin(user):
    """Check if user is admin or staff."""
    return user.is_superuser or user.is_staff


RENTAL_COMPLETED_STATUSES = ['completed', 'finalized']
RENTAL_ACTIVE_STATUSES = ['approved', 'assigned', 'ongoing']
DATE_RANGE_CHOICES = [
    ('all', 'All Dates'),
    ('1_week', '1 Week'),
    ('1_month', '1 Month'),
    ('1_year', '1 Year'),
    ('custom', 'Custom Range'),
]
DATE_RANGE_PRESET_DAYS = {
    '1_week': 6,
    '1_month': 29,
    '1_year': 364,
}

SERVICE_REVENUE_STATUSES = ['paid', 'confirmed', 'completed']
MAINTENANCE_COST_STATUSES = ['completed']
MILLED_RICE_KG_PER_SACK = Decimal('50.00')


def _date_value(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _transaction_datetime(dt_value, fallback_date=None):
    if dt_value is not None:
        return dt_value
    if fallback_date is not None:
        return timezone.make_aware(datetime.combine(fallback_date, datetime.min.time()))
    return timezone.now()


def _transaction_row(
    *,
    user,
    created_at,
    internal_transaction_id,
    amount,
    payment_type_display,
    payment_channel_display,
    status,
    status_display,
    processed_by=None,
    total_refunded=Decimal('0.00'),
):
    return SimpleNamespace(
        user=user,
        created_at=created_at,
        internal_transaction_id=internal_transaction_id,
        amount=amount,
        payment_type_display=payment_type_display,
        payment_channel_display=payment_channel_display,
        status=status,
        status_display=status_display,
        processed_by=processed_by,
        processed_by_id=getattr(processed_by, 'pk', None),
        total_refunded=total_refunded,
    )


def _resolve_date_filters(request):
    date_range = (request.GET.get('date_range') or '').strip()
    start_date = (request.GET.get('start_date') or '').strip()
    end_date = (request.GET.get('end_date') or '').strip()

    if date_range in DATE_RANGE_PRESET_DAYS:
        end_value = timezone.localdate()
        start_value = end_value - timedelta(days=DATE_RANGE_PRESET_DAYS[date_range])
        start_date = start_value.isoformat()
        end_date = end_value.isoformat()
    else:
        start_value = _date_value(start_date)
        end_value = _date_value(end_date)
        if start_date or end_date:
            date_range = 'custom'
        else:
            date_range = 'all'

    return {
        'date_range': date_range,
        'date_range_label': _date_range_label(date_range, start_value, end_value),
        'start_date': start_date,
        'end_date': end_date,
        'start_value': start_value,
        'end_value': end_value,
    }


def _machine_service_revenue(machine, date_filters):
    rental_query = Rental.objects.filter(machine=machine).exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=True) | Q(payment_status='paid')
    )
    if date_filters['start_value']:
        rental_query = rental_query.filter(start_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rental_query = rental_query.filter(end_date__lte=date_filters['end_value'])
    rental_revenue = rental_query.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')

    rice_query = RiceMillAppointment.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    )
    if date_filters['start_value']:
        rice_query = rice_query.filter(appointment_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rice_query = rice_query.filter(appointment_date__lte=date_filters['end_value'])
    rice_revenue = rice_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    dryer_query = DryerRental.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    )
    if date_filters['start_value']:
        dryer_query = dryer_query.filter(rental_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        dryer_query = dryer_query.filter(rental_date__lte=date_filters['end_value'])
    dryer_revenue = dryer_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return rental_revenue + rice_revenue + dryer_revenue


def _machine_revenue_breakdown(machine, date_filters):
    rental_query = Rental.objects.filter(machine=machine).exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=True) | Q(payment_status='paid')
    )
    if date_filters['start_value']:
        rental_query = rental_query.filter(start_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rental_query = rental_query.filter(end_date__lte=date_filters['end_value'])
    rental_revenue = rental_query.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0.00')

    rice_query = RiceMillAppointment.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    )
    if date_filters['start_value']:
        rice_query = rice_query.filter(appointment_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rice_query = rice_query.filter(appointment_date__lte=date_filters['end_value'])
    rice_revenue = rice_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    dryer_query = DryerRental.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    )
    if date_filters['start_value']:
        dryer_query = dryer_query.filter(rental_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        dryer_query = dryer_query.filter(rental_date__lte=date_filters['end_value'])
    dryer_revenue = dryer_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Harvester revenue from rice sales
    # For harvesters, revenue comes from selling the rice that was harvested
    harvester_revenue = Decimal('0.00')
    rice_sale_count = 0
    if machine.machine_type == 'harvester':
        rice_sale_query = RiceSale.objects.filter(
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
        )
        if date_filters['start_value']:
            rice_sale_query = rice_sale_query.filter(paid_at__date__gte=date_filters['start_value'])
        if date_filters['end_value']:
            rice_sale_query = rice_sale_query.filter(paid_at__date__lte=date_filters['end_value'])
        
        # Calculate total revenue from rice sales
        rice_sale_revenue = rice_sale_query.aggregate(
            total=Sum(F('sacks') * F('price_per_sack'))
        )['total'] or Decimal('0.00')
        
        harvester_revenue = rice_sale_revenue
        rice_sale_count = rice_sale_query.count()

    total_revenue = rental_revenue + rice_revenue + dryer_revenue + harvester_revenue
    return {
        'rental_revenue': rental_revenue,
        'rice_revenue': rice_revenue,
        'dryer_revenue': dryer_revenue,
        'harvester_revenue': harvester_revenue,
        'total_revenue': total_revenue,
        'rental_count': rental_query.count(),
        'rice_count': rice_query.count(),
        'dryer_count': dryer_query.count(),
        'rice_sale_count': rice_sale_count,
    }


def _machine_maintenance_queryset(machine, date_filters):
    maintenance = Maintenance.objects.filter(
        machine=machine,
    ).exclude(
        status='cancelled',
    ).prefetch_related('parts_used').order_by('-start_date')

    if date_filters['start_value']:
        maintenance = maintenance.filter(
            Q(actual_completion_date__date__gte=date_filters['start_value']) |
            Q(actual_completion_date__isnull=True, start_date__date__gte=date_filters['start_value'])
        )
    if date_filters['end_value']:
        maintenance = maintenance.filter(
            Q(actual_completion_date__date__lte=date_filters['end_value']) |
            Q(actual_completion_date__isnull=True, start_date__date__lte=date_filters['end_value'])
        )
    return maintenance


def _machine_maintenance_breakdown(machine, date_filters):
    maintenance_records = _machine_maintenance_queryset(machine, date_filters)
    cost_records = [record for record in maintenance_records if record.status in MAINTENANCE_COST_STATUSES]

    parts_cost = sum((record.parts_total for record in cost_records), Decimal('0.00'))
    labor_cost = sum((record.labor_cost or Decimal('0.00') for record in cost_records), Decimal('0.00'))
    other_cost = sum((record.other_cost or Decimal('0.00') for record in cost_records), Decimal('0.00'))
    maintenance_total = parts_cost + labor_cost + other_cost

    return {
        'records': maintenance_records,
        'maintenance_count': maintenance_records.count(),
        'completed_maintenance_count': len(cost_records),
        'parts_cost': parts_cost,
        'labor_cost': labor_cost,
        'other_cost': other_cost,
        'maintenance_total': maintenance_total,
    }


def _maintenance_record_downtime_days(record):
    start_dt = record.start_date
    end_dt = record.actual_completion_date or record.end_date or timezone.now()
    if not start_dt or not end_dt:
        return 0
    start_date = timezone.localtime(start_dt).date() if timezone.is_aware(start_dt) else start_dt.date()
    end_date = timezone.localtime(end_dt).date() if timezone.is_aware(end_dt) else end_dt.date()
    return max((end_date - start_date).days + 1, 1)


def _normalize_issue_signature(text):
    cleaned = re.sub(r'[^a-z0-9\s]+', ' ', (text or '').lower())
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _machine_maintenance_timeline(machine):
    records = list(
        Maintenance.objects.filter(machine=machine)
        .exclude(status='cancelled')
        .order_by('-start_date')
        .prefetch_related('parts_used')
    )
    timeline_rows = []
    total_downtime_days = 0
    maintenance_type_counts = Counter()
    issue_counts = Counter()

    for record in records:
        downtime_days = _maintenance_record_downtime_days(record)
        total_downtime_days += downtime_days
        maintenance_type_counts[record.maintenance_type] += 1

        issue_signature = _normalize_issue_signature(record.description)
        if issue_signature:
            issue_counts[issue_signature] += 1

        timeline_rows.append({
            'record': record,
            'downtime_days': downtime_days,
        })

    recurring_alerts = []
    for maintenance_type, count in maintenance_type_counts.items():
        if count >= 2 and maintenance_type in {'corrective', 'emergency', 'overhaul'}:
            recurring_alerts.append(
                f'{dict(Maintenance.MAINTENANCE_TYPE_CHOICES).get(maintenance_type, maintenance_type)} happened {count} times.'
            )

    for issue_signature, count in issue_counts.items():
        if count >= 2 and len(issue_signature) >= 8:
            recurring_alerts.append(f'Repeated issue noted {count} times: {issue_signature.title()}.')

    latest_record = timeline_rows[0] if timeline_rows else None
    return {
        'records': timeline_rows,
        'total_downtime_days': total_downtime_days,
        'latest_record': latest_record,
        'recurring_alerts': recurring_alerts,
    }


def _machine_profitability_snapshot(machine, date_filters):
    revenue = _machine_revenue_breakdown(machine, date_filters)
    maintenance = _machine_maintenance_breakdown(machine, date_filters)
    acquisition_amount = machine.acquisition_amount or Decimal('0.00')
    operating_expenses = maintenance['maintenance_total']
    net_profit = revenue['total_revenue'] - operating_expenses
    roi_percent = None
    payback_progress_amount = None
    payback_progress_percent = None
    if acquisition_amount > 0:
        roi_percent = (net_profit / acquisition_amount) * Decimal('100.00')
        payback_progress_amount = min(max(net_profit, Decimal('0.00')), acquisition_amount)
        payback_progress_percent = (payback_progress_amount / acquisition_amount) * Decimal('100.00')
    payback_remaining = None
    if acquisition_amount > 0:
        payback_remaining = max(acquisition_amount - (payback_progress_amount or Decimal('0.00')), Decimal('0.00'))

    today = date_filters['end_value'] or timezone.localdate()
    observed_start = machine.acquisition_date or date_filters['start_value']
    estimated_payback_months = None
    average_monthly_profit = None
    if observed_start:
        observed_days = max((today - observed_start).days + 1, 1)
        observed_months = Decimal(str(observed_days)) / Decimal('30.0')
        if observed_months > 0:
            average_monthly_profit = net_profit / observed_months
            if average_monthly_profit > 0 and payback_remaining is not None:
                estimated_payback_months = payback_remaining / average_monthly_profit

    if acquisition_amount <= 0:
        recovery_status = {
            'label': 'No cost basis',
            'tone': 'secondary',
        }
    elif net_profit < 0:
        recovery_status = {
            'label': 'Loss',
            'tone': 'danger',
        }
    elif payback_remaining and payback_remaining > 0:
        recovery_status = {
            'label': 'Recovering',
            'tone': 'warning',
        }
    else:
        recovery_status = {
            'label': 'Profitable',
            'tone': 'success',
        }

    warnings = []
    if acquisition_amount <= 0:
        warnings.append('Acquisition cost is missing, so ROI and payback are incomplete.')
    if not machine.acquisition_date:
        warnings.append('Acquisition date is missing, so lifecycle timing is incomplete.')
    if maintenance['completed_maintenance_count'] == 0:
        warnings.append('No operating expenses are recorded yet, so profit may be overstated.')
    if revenue['total_revenue'] <= 0:
        warnings.append('No revenue has been recorded for this machine yet.')

    return {
        'revenue': revenue,
        'maintenance': maintenance,
        'acquisition_amount': acquisition_amount,
        'operating_expenses': operating_expenses,
        'net_profit': net_profit,
        'roi_percent': roi_percent,
        'payback_progress_amount': payback_progress_amount,
        'payback_progress_percent': payback_progress_percent,
        'payback_remaining': payback_remaining,
        'average_monthly_profit': average_monthly_profit,
        'estimated_payback_months': estimated_payback_months,
        'recovery_status': recovery_status,
        'warnings': warnings,
    }


def _date_range_label(date_range, start_value, end_value):
    preset_labels = {
        'all': 'All Dates',
        '1_week': '1 Week',
        '1_month': '1 Month',
        '1_year': '1 Year',
        'custom': 'Custom Range',
    }
    label = preset_labels.get(date_range, 'Custom Range')
    if start_value and end_value:
        return f'{label} ({start_value:%b %d, %Y} to {end_value:%b %d, %Y})'
    if start_value:
        return f'{label} (From {start_value:%b %d, %Y})'
    if end_value:
        return f'{label} (Until {end_value:%b %d, %Y})'
    return label


def _user_display_label(user):
    full_name = user.get_full_name().strip() if hasattr(user, 'get_full_name') else ''
    return full_name or user.username


def _filename(prefix, extension):
    return f'{prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{extension}'


def _xlsx_response(prefix, title, filter_details, headers, rows, column_widths=None, sheet_name='Report'):
    response = HttpResponse(
        build_xlsx_bytes(
            title=title,
            filter_details=filter_details,
            headers=headers,
            rows=rows,
            column_widths=column_widths,
            sheet_name=sheet_name,
        ),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{_filename(prefix, "xlsx")}"'
    return response


def _wants_pdf_preview(request) -> bool:
    return (request.GET.get('preview') or '').strip().lower() in {'1', 'true', 'yes'}


def _pdf_response(prefix, title, filter_details, headers, rows, column_widths=None, *, inline=False):
    response = HttpResponse(
        build_pdf_bytes(
            title=title,
            filter_details=filter_details,
            headers=headers,
            rows=rows,
            column_widths=column_widths,
        ),
        content_type='application/pdf',
    )
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{_filename(prefix, "pdf")}"'
    return response


def _rental_report_context(request):
    date_filters = _resolve_date_filters(request)
    machine_id = request.GET.get('machine')
    member_id = request.GET.get('member')
    status = request.GET.get('status')

    rentals = Rental.objects.select_related('machine', 'user').all()

    if date_filters['start_value']:
        rentals = rentals.filter(start_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rentals = rentals.filter(end_date__lte=date_filters['end_value'])
    if machine_id:
        rentals = rentals.filter(machine_id=machine_id)
    if member_id:
        rentals = rentals.filter(user_id=member_id)
    if status:
        rentals = rentals.filter(status=status)

    machines = Machine.objects.order_by('name')
    members = User.objects.filter(role=User.REGULAR_USER).order_by('last_name', 'first_name', 'username')
    machine_label = machines.filter(id=machine_id).values_list('name', flat=True).first() if machine_id else 'All Machines'
    selected_member = members.filter(id=member_id).first() if member_id else None
    member_label = _user_display_label(selected_member) if selected_member else 'All Members'
    status_label = dict(Rental.STATUS_CHOICES).get(status, 'All Statuses') if status else 'All Statuses'

    stats = {
        'total': rentals.count(),
        'completed': rentals.filter(status__in=RENTAL_COMPLETED_STATUSES).count(),
        'active': rentals.filter(status__in=RENTAL_ACTIVE_STATUSES).count(),
        'pending': rentals.filter(status='pending').count(),
        'revenue': rentals.exclude(payment_type='in_kind').aggregate(
            Sum('payment_amount')
        )['payment_amount__sum'] or 0,
    }

    ordered_rentals = rentals.order_by('-created_at')
    rental_content_type = ContentType.objects.get_for_model(Rental)
    payment_map = {
        payment.object_id: payment
        for payment in Payment.objects.filter(
            content_type=rental_content_type,
            object_id__in=ordered_rentals.values_list('id', flat=True),
        ).select_related('processed_by')
    }
    for rental in ordered_rentals:
        rental.payment_record = payment_map.get(rental.id)

    return {
        'rentals': ordered_rentals,
        'stats': stats,
        'machines': machines,
        'members': members,
        'date_range_options': DATE_RANGE_CHOICES,
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
            'machine': machine_id,
            'machine_label': machine_label,
            'member': member_id,
            'member_label': member_label,
            'status': status,
            'status_label': status_label,
        }
    }


def _harvest_report_context(request):
    date_filters = _resolve_date_filters(request)
    rentals = _completed_harvest_rentals()
    member_id = (request.GET.get('member') or '').strip()
    delivery_status = (request.GET.get('delivery_status') or '').strip()

    if date_filters['start_value']:
        rentals = rentals.filter(operator_reported_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rentals = rentals.filter(operator_reported_at__date__lte=date_filters['end_value'])
    if member_id:
        rentals = rentals.filter(user_id=member_id)
    if delivery_status == 'delivered':
        rentals = rentals.filter(organization_share_received__gt=0)
    elif delivery_status == 'outstanding':
        rentals = rentals.filter(
            Q(organization_share_received__isnull=True)
            | Q(organization_share_received__lt=F('organization_share_required'))
        )
    elif delivery_status == 'settled':
        rentals = rentals.filter(
            organization_share_received__isnull=False,
            organization_share_required__isnull=False,
            organization_share_received__gte=F('organization_share_required'),
        )

    harvest_data = [_harvest_row(rental) for rental in rentals.order_by('-operator_reported_at', '-created_at')]
    total_harvested = sum((row['rental'].total_harvest_sacks or Decimal('0.00')) for row in harvest_data)
    total_bufia = sum((row['bufia_share'] or Decimal('0.00')) for row in harvest_data)
    total_member = sum((row['member_share'] or Decimal('0.00')) for row in harvest_data)
    outstanding = sum((row['outstanding'] or Decimal('0.00')) for row in harvest_data)
    bufia_milling = _bufia_harvest_milling_snapshot()
    members = User.objects.filter(
        id__in=_completed_harvest_rentals().values_list('user_id', flat=True)
    ).order_by('first_name', 'last_name', 'username')
    selected_member = members.filter(id=member_id).first() if member_id else None
    member_label = _user_display_label(selected_member) if selected_member else 'All Members'
    delivery_labels = {
        '': 'All Delivery Status',
        'delivered': 'Delivered',
        'outstanding': 'Outstanding',
        'settled': 'Settled',
    }

    return {
        'harvest_data': harvest_data,
        'total_harvested': total_harvested,
        'total_bufia': total_bufia,
        'total_member': total_member,
        'outstanding': outstanding,
        'bufia_milling': bufia_milling,
        'members': members,
        'date_range_options': DATE_RANGE_CHOICES,
        'delivery_status_options': [
            ('', 'All Delivery Status'),
            ('delivered', 'Delivered'),
            ('outstanding', 'Outstanding'),
            ('settled', 'Settled'),
        ],
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
            'member': member_id,
            'member_label': member_label,
            'delivery_status': delivery_status,
            'delivery_status_label': delivery_labels.get(delivery_status, 'All Delivery Status'),
        }
    }


def _rice_sales_report_context():
    rice_sale_settings = _rice_sale_setting()
    rice_inventory = _rice_inventory_snapshot()
    bufia_milling = _bufia_harvest_milling_snapshot()
    orders = list(RiceSale.objects.select_related('buyer', 'processed_by').order_by('pickup_date', '-created_at', '-id'))
    for order in orders:
        order.effective_pickup_date = (
            order.pickup_date
            or (timezone.localtime(order.claimed_at).date() if order.claimed_at else None)
            or timezone.localtime(order.created_at).date()
        )

    waiting_pickup_orders = [
        order for order in orders
        if order.order_status not in [RiceSale.ORDER_STATUS_CLAIMED, RiceSale.ORDER_STATUS_CANCELLED]
    ]
    remaining_stock_value = (
        rice_inventory['available_sacks'] * Decimal(str(rice_sale_settings.current_price_per_sack or '0.00'))
    ).quantize(Decimal('0.01'))

    return {
        'rice_inventory': rice_inventory,
        'bufia_milling': bufia_milling,
        'rice_sale_settings': rice_sale_settings,
        'rice_sale_settings_form': RiceSaleSettingForm(instance=rice_sale_settings),
        'sales_transactions': orders,
        'pickup_orders': waiting_pickup_orders,
        'stock_movements': _rice_stock_movement_rows(),
        'remaining_stock_value': remaining_stock_value,
        'queue_stats': {
            'reserved': sum(1 for order in waiting_pickup_orders if order.order_status == RiceSale.ORDER_STATUS_RESERVED),
            'ready': sum(1 for order in waiting_pickup_orders if order.order_status == RiceSale.ORDER_STATUS_READY),
            'claimed': sum(1 for order in orders if order.order_status == RiceSale.ORDER_STATUS_CLAIMED),
            'pending_payment': sum(1 for order in waiting_pickup_orders if order.payment_status == RiceSale.PAYMENT_STATUS_PENDING),
        },
    }


def _financial_summary_context(request):
    date_filters = _resolve_date_filters(request)
    payment_queryset = Payment.objects.select_related('user', 'processed_by').prefetch_related('refunds').filter(
        status__in=['completed', 'refunded']
    )

    if date_filters['start_value']:
        payment_queryset = payment_queryset.filter(created_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        payment_queryset = payment_queryset.filter(created_at__date__lte=date_filters['end_value'])

    refunds = Refund.objects.select_related('payment').filter(status='refunded')
    if date_filters['start_value']:
        refunds = refunds.filter(refunded_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        refunds = refunds.filter(refunded_at__date__lte=date_filters['end_value'])

    rental_income_query = Rental.objects.exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=True) | Q(payment_status='paid')
    )
    if date_filters['start_value']:
        rental_income_query = rental_income_query.filter(created_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rental_income_query = rental_income_query.filter(created_at__date__lte=date_filters['end_value'])
    rental_income = rental_income_query.aggregate(
        Sum('payment_amount')
    )['payment_amount__sum'] or 0

    membership_content_type = ContentType.objects.get_for_model(MembershipApplication)
    membership_payment_queryset = payment_queryset.filter(
        payment_type='membership',
        content_type=membership_content_type,
    )
    membership_payment_ids = set(membership_payment_queryset.values_list('object_id', flat=True))

    legacy_membership_query = MembershipApplication.objects.select_related('user').filter(
        payment_status='paid',
    ).exclude(pk__in=membership_payment_ids)
    if date_filters['start_value']:
        legacy_membership_query = legacy_membership_query.filter(payment_date__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        legacy_membership_query = legacy_membership_query.filter(payment_date__date__lte=date_filters['end_value'])

    membership_income = (
        membership_payment_queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    ) + (Decimal('500.00') * legacy_membership_query.count())
    membership_count = membership_payment_queryset.count() + legacy_membership_query.count()

    rice_sales_query = RiceSale.objects.select_related('buyer', 'processed_by').filter(
        payment_status=RiceSale.PAYMENT_STATUS_PAID,
    )
    if date_filters['start_value']:
        rice_sales_query = rice_sales_query.filter(paid_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        rice_sales_query = rice_sales_query.filter(paid_at__date__lte=date_filters['end_value'])
    rice_sales_income = rice_sales_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    outstanding_query = Rental.objects.exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=False) | Q(payment_status__in=['pending', 'to_be_determined'])
    ).exclude(status__in=['cancelled', 'rejected'])
    if date_filters['start_value']:
        outstanding_query = outstanding_query.filter(created_at__date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        outstanding_query = outstanding_query.filter(created_at__date__lte=date_filters['end_value'])
    outstanding = outstanding_query.aggregate(
        Sum('payment_amount')
    )['payment_amount__sum'] or 0

    profitability_snapshots = [
        _machine_profitability_snapshot(machine, date_filters)
        for machine in Machine.objects.all()
    ]
    machine_revenue = sum((item['revenue']['total_revenue'] for item in profitability_snapshots), Decimal('0.00'))
    machine_acquisition_cost = sum((item['acquisition_amount'] for item in profitability_snapshots), Decimal('0.00'))
    machine_operating_cost = sum((item['maintenance']['maintenance_total'] for item in profitability_snapshots), Decimal('0.00'))
    machine_total_cost = machine_acquisition_cost + machine_operating_cost
    machine_net_earnings = machine_revenue - machine_operating_cost

    stats = {
        'rental_income': rental_income,
        'membership_income': membership_income,
        'membership_count': membership_count,
        'rice_sales_income': rice_sales_income,
        'total_revenue': rental_income + membership_income + rice_sales_income,
        'outstanding': outstanding,
        'machine_revenue': machine_revenue,
        'machine_acquisition_cost': machine_acquisition_cost,
        'machine_operating_cost': machine_operating_cost,
        'machine_total_cost': machine_total_cost,
        'machine_net_earnings': machine_net_earnings,
    }

    ordered_payments = list(payment_queryset.order_by('-created_at'))
    service_income = payment_queryset.filter(payment_type__in=['appointment', 'dryer', 'irrigation']).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    total_refunded = refunds.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    gross_revenue = stats['rental_income'] + stats['membership_income'] + stats['rice_sales_income'] + service_income
    net_revenue = gross_revenue - total_refunded

    transactions = [
        _transaction_row(
            user=payment.user,
            created_at=payment.created_at,
            internal_transaction_id=payment.internal_transaction_id or 'Pending',
            amount=payment.amount,
            payment_type_display=payment.get_payment_type_display(),
            payment_channel_display=payment.payment_channel_display,
            status=payment.status,
            status_display=payment.get_status_display(),
            processed_by=payment.processed_by,
            total_refunded=payment.total_refunded,
        )
        for payment in ordered_payments
    ]
    transactions.extend(
        _transaction_row(
            user=application.user,
            created_at=_transaction_datetime(application.payment_date, application.submission_date),
            internal_transaction_id=f'BUFIA-MEM-{application.pk:05d}',
            amount=Decimal('500.00'),
            payment_type_display='Membership Fee',
            payment_channel_display='Over the Counter' if application.payment_method == 'face_to_face' else 'Office / Manual',
            status='completed',
            status_display='Completed',
        )
        for application in legacy_membership_query
    )
    transactions.extend(
        _transaction_row(
            user=order.buyer,
            created_at=_transaction_datetime(order.paid_at, order.created_at.date()),
            internal_transaction_id=order.reference_number or f'BUFIA-RICE-{order.pk:05d}',
            amount=order.total_amount,
            payment_type_display='Rice Sale',
            payment_channel_display=order.get_payment_method_display(),
            status='completed',
            status_display='Completed',
            processed_by=order.processed_by,
        )
        for order in rice_sales_query
    )
    transactions.sort(
        key=lambda item: (item.created_at, item.internal_transaction_id or ''),
        reverse=True,
    )

    online_payments = sum(1 for item in transactions if item.payment_channel_display == 'Gcash Payment')
    over_counter_payments = sum(
        1 for item in transactions if item.payment_channel_display in {'Over the Counter', 'Office / Manual'}
    )
    face_to_face = len(transactions) - online_payments

    return {
        'payments': transactions,
        'stats': stats,
        'online_payments': online_payments,
        'face_to_face': face_to_face,
        'over_counter_payments': over_counter_payments,
        'service_income': service_income,
        'gross_revenue': gross_revenue,
        'total_refunded': total_refunded,
        'net_revenue': net_revenue,
        'refund_count': refunds.count(),
        'date_range_options': DATE_RANGE_CHOICES,
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
        }
    }


def _machine_usage_report_context(request):
    date_filters = _resolve_date_filters(request)
    machine_id = request.GET.get('machine')

    machines = Machine.objects.all()
    if machine_id:
        machines = machines.filter(id=machine_id)

    usage_data = []
    for machine in machines:
        rentals = Rental.objects.filter(machine=machine)
        if date_filters['start_value']:
            rentals = rentals.filter(start_date__gte=date_filters['start_value'])
        if date_filters['end_value']:
            rentals = rentals.filter(end_date__lte=date_filters['end_value'])

        total_rentals = rentals.count()
        total_days = sum(r.get_duration_days() for r in rentals)
        profitability = _machine_profitability_snapshot(machine, date_filters)
        revenue = profitability['revenue']['total_revenue']
        acquisition_amount = profitability['acquisition_amount']
        maintenance = profitability['maintenance']
        maintenance_count = maintenance['maintenance_count']

        if date_filters['start_value'] and date_filters['end_value']:
            date_range_days = (date_filters['end_value'] - date_filters['start_value']).days + 1
            utilization_rate = (total_days / date_range_days * 100) if date_range_days > 0 else 0
        else:
            utilization_rate = 0

        usage_data.append({
            'machine': machine,
            'rental_count': total_rentals,
            'total_days': total_days,
            'revenue': revenue,
            'acquisition_amount': acquisition_amount,
            'parts_cost': maintenance['parts_cost'],
            'labor_cost': maintenance['labor_cost'],
            'other_cost': maintenance['other_cost'],
            'operating_cost': maintenance['maintenance_total'],
            'net_profit': profitability['net_profit'],
            'roi_percent': profitability['roi_percent'],
            'payback_progress_amount': profitability['payback_progress_amount'],
            'payback_progress_percent': profitability['payback_progress_percent'],
            'payback_remaining': profitability['payback_remaining'],
            'recovery_status': profitability['recovery_status'],
            'maintenance_count': maintenance_count,
            'utilization_rate': round(utilization_rate, 2),
        })

    usage_data.sort(key=lambda item: item['rental_count'], reverse=True)
    usage_stats = {
        'machines': len(usage_data),
        'total_rentals': sum(item['rental_count'] for item in usage_data),
        'total_days': sum(item['total_days'] for item in usage_data),
        'total_revenue': sum((item['revenue'] for item in usage_data), Decimal('0.00')),
        'total_acquisition_amount': sum((item['acquisition_amount'] for item in usage_data), Decimal('0.00')),
        'total_operating_cost': sum((item['operating_cost'] for item in usage_data), Decimal('0.00')),
        'total_net_profit': sum((item['net_profit'] for item in usage_data), Decimal('0.00')),
        'maintenance_count': sum(item['maintenance_count'] for item in usage_data),
    }

    all_machines = Machine.objects.all()
    machine_label = all_machines.filter(id=machine_id).values_list('name', flat=True).first() if machine_id else 'All Machines'

    return {
        'usage_data': usage_data,
        'stats': usage_stats,
        'machines': all_machines,
        'date_range_options': DATE_RANGE_CHOICES,
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'machine': machine_id,
            'machine_label': machine_label,
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
        }
    }


def _membership_report_context(request):
    filter_type = request.GET.get('filter', 'all')
    date_filters = _resolve_date_filters(request)

    members = User.objects.filter(role=User.REGULAR_USER).select_related(
        'membership_application__assigned_sector'
    ).prefetch_related('membership_application__proof_documents')
    if filter_type == 'active':
        members = members.filter(is_verified=True)
    elif filter_type == 'pending':
        members = members.filter(membership_form_submitted=True, is_verified=False)
    elif filter_type == 'expired':
        members = members.filter(is_verified=False, membership_form_submitted=False)
    elif filter_type == 'recent_approved':
        members = members.filter(
            is_verified=True,
            membership_approved_date__isnull=False,
        )

    if filter_type == 'recent_approved':
        if date_filters['start_value']:
            members = members.filter(membership_approved_date__gte=date_filters['start_value'])
        if date_filters['end_value']:
            members = members.filter(membership_approved_date__lte=date_filters['end_value'])
        members = members.order_by('-membership_approved_date', '-date_joined')
    else:
        if date_filters['start_value']:
            members = members.filter(date_joined__date__gte=date_filters['start_value'])
        if date_filters['end_value']:
            members = members.filter(date_joined__date__lte=date_filters['end_value'])
        members = members.order_by('-date_joined')

    member_base = User.objects.filter(role=User.REGULAR_USER)
    recent_approved_base = member_base.filter(
        is_verified=True,
        membership_approved_date__isnull=False,
    )
    if date_filters['start_value']:
        recent_approved_base = recent_approved_base.filter(membership_approved_date__gte=date_filters['start_value'])
    if date_filters['end_value']:
        recent_approved_base = recent_approved_base.filter(membership_approved_date__lte=date_filters['end_value'])

    stats = {
        'total': member_base.count(),
        'active': member_base.filter(is_verified=True).count(),
        'pending': member_base.filter(membership_form_submitted=True, is_verified=False).count(),
        'new_members': members.count() if date_filters['start_value'] or date_filters['end_value'] else 0,
        'recent_approved': recent_approved_base.count(),
    }
    filter_labels = {
        'all': 'All Members',
        'active': 'Active Only',
        'pending': 'Pending Only',
        'recent_approved': 'Recently Approved',
        'expired': 'Inactive / Not Submitted',
    }

    return {
        'members': members,
        'stats': stats,
        'filter_type': filter_type,
        'filter_heading': 'Recently Approved Members' if filter_type == 'recent_approved' else 'Membership Records',
        'filter_description': (
            'Newest approved members ordered by approval date.'
            if filter_type == 'recent_approved'
            else 'Review member verification, status, and registration activity.'
        ),
        'date_range_options': DATE_RANGE_CHOICES,
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
            'filter_type_label': filter_labels.get(filter_type, 'All Members'),
        }
    }

def _completed_harvest_rentals():
    return Rental.objects.filter(
        payment_type='in_kind',
        total_harvest_sacks__isnull=False,
    ).filter(
        Q(status__in=RENTAL_COMPLETED_STATUSES)
        | Q(workflow_state__in=['harvest_report_submitted', 'share_confirmed', 'completed'])
    ).select_related('machine', 'user')


def _rice_sale_setting():
    return RiceSaleSetting.get_solo()


def _bufia_harvest_milling_queryset():
    return RiceMillAppointment.objects.filter(
        booking_source=RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE,
        final_weight__isnull=False,
        total_amount__isnull=False,
        status__in=['paid', 'confirmed', 'completed'],
    ).select_related('user', 'machine')


def _bufia_harvest_milling_snapshot():
    appointments = _bufia_harvest_milling_queryset()
    total_milled_weight = appointments.aggregate(total=Sum('final_weight'))['total'] or Decimal('0.00')
    total_milling_cost = appointments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return {
        'source_label': 'BUFIA Rice Share',
        'total_milled_weight': Decimal(str(total_milled_weight)).quantize(Decimal('0.01')),
        'total_milling_cost': Decimal(str(total_milling_cost)).quantize(Decimal('0.01')),
        'completed_appointments': appointments.count(),
    }


def _rice_inventory_snapshot():
    bufia_milling = _bufia_harvest_milling_snapshot()
    milled_total_kg = bufia_milling['total_milled_weight']
    milled_total_sacks = (
        Decimal(str(milled_total_kg)) / MILLED_RICE_KG_PER_SACK
    ).quantize(Decimal('0.01'))
    active_orders = RiceSale.objects.exclude(order_status=RiceSale.ORDER_STATUS_CANCELLED)
    reserved_orders = active_orders.filter(
        order_status__in=[RiceSale.ORDER_STATUS_RESERVED, RiceSale.ORDER_STATUS_READY]
    )
    claimed_orders = active_orders.filter(order_status=RiceSale.ORDER_STATUS_CLAIMED)
    paid_orders = active_orders.filter(payment_status=RiceSale.PAYMENT_STATUS_PAID)
    paid_claimed_orders = claimed_orders.filter(payment_status=RiceSale.PAYMENT_STATUS_PAID)
    pending_otc_orders = active_orders.filter(
        payment_method=RiceSale.PAYMENT_METHOD_OTC,
        payment_status=RiceSale.PAYMENT_STATUS_PENDING,
    )

    reserved_sacks = reserved_orders.aggregate(total=Sum('sacks'))['total'] or Decimal('0.00')
    claimed_sacks = claimed_orders.aggregate(total=Sum('sacks'))['total'] or Decimal('0.00')
    paid_sacks = paid_orders.aggregate(total=Sum('sacks'))['total'] or Decimal('0.00')
    paid_sales_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    claimed_sales_revenue = paid_claimed_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    pending_otc_amount = pending_otc_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    available_sacks = max(
        Decimal(str(milled_total_sacks)) - Decimal(str(reserved_sacks)) - Decimal(str(claimed_sacks)),
        Decimal('0.00'),
    )
    if milled_total_sacks > 0:
        milling_cost_per_sack = (
            Decimal(str(bufia_milling['total_milling_cost'])) / Decimal(str(milled_total_sacks))
        ).quantize(Decimal('0.01'))
    else:
        milling_cost_per_sack = Decimal('0.00')
    cost_of_sold_rice = (Decimal(str(claimed_sacks)) * milling_cost_per_sack).quantize(Decimal('0.01'))
    net_income_from_sold_rice = (
        Decimal(str(claimed_sales_revenue)) - cost_of_sold_rice
    ).quantize(Decimal('0.01'))
    average_selling_price_per_sack = (
        (Decimal(str(paid_sales_revenue)) / Decimal(str(paid_sacks))).quantize(Decimal('0.01'))
        if Decimal(str(paid_sacks)) > 0 else Decimal('0.00')
    )

    return {
        'milled_total_kg': Decimal(str(milled_total_kg)).quantize(Decimal('0.01')),
        'milled_total_sacks': Decimal(str(milled_total_sacks)).quantize(Decimal('0.01')),
        'reserved_sacks': Decimal(str(reserved_sacks)).quantize(Decimal('0.01')),
        'sold_sacks': Decimal(str(claimed_sacks)).quantize(Decimal('0.01')),
        'claimed_orders_count': claimed_orders.count(),
        'paid_sacks': Decimal(str(paid_sacks)).quantize(Decimal('0.01')),
        'sales_revenue': Decimal(str(paid_sales_revenue)).quantize(Decimal('0.01')),
        'paid_orders_count': paid_orders.count(),
        'claimed_sales_revenue': Decimal(str(claimed_sales_revenue)).quantize(Decimal('0.01')),
        'available_sacks': available_sacks.quantize(Decimal('0.01')),
        'pending_otc_orders': pending_otc_orders.count(),
        'pending_otc_amount': Decimal(str(pending_otc_amount)).quantize(Decimal('0.01')),
        'milling_cost_per_sack': milling_cost_per_sack,
        'cost_of_sold_rice': cost_of_sold_rice,
        'net_income_from_sold_rice': net_income_from_sold_rice,
        'average_selling_price_per_sack': average_selling_price_per_sack,
    }


def _rice_stock_movement_rows():
    rows = []
    for appointment in _bufia_harvest_milling_queryset().order_by('updated_at', 'created_at', 'pk'):
        stock_in = (
            Decimal(str(appointment.final_weight or '0.00')) / MILLED_RICE_KG_PER_SACK
        ).quantize(Decimal('0.01'))
        appointment_event_at = timezone.make_aware(
            datetime.combine(appointment.appointment_date, datetime.min.time())
        )
        rows.append({
            'date': appointment_event_at,
            'type': 'stock_in',
            'type_label': 'Stock In',
            'source': f'{appointment.reference_number or appointment.get_transaction_id()} - Milling completed',
            'stock_in': stock_in,
            'stock_out': None,
            'sort_key': (appointment_event_at, 0, appointment.pk),
        })

    orders = RiceSale.objects.select_related('buyer').order_by('created_at', 'pk')
    for order in orders:
        rows.append({
            'date': order.created_at,
            'type': 'reserved',
            'type_label': 'Reserved',
            'source': f'{order.reference_number} - {order.buyer.get_full_name() or order.buyer.username}',
            'stock_in': None,
            'stock_out': None,
            'sort_key': (order.created_at, 1, order.pk),
            'reserved_change': Decimal(str(order.sacks)).quantize(Decimal('0.01')),
        })
        if order.order_status == RiceSale.ORDER_STATUS_CLAIMED and order.claimed_at:
            rows.append({
                'date': order.claimed_at,
                'type': 'stock_out',
                'type_label': 'Stock Out',
                'source': f'{order.reference_number} - Claimed by {order.buyer.get_full_name() or order.buyer.username}',
                'stock_in': None,
                'stock_out': Decimal(str(order.sacks)).quantize(Decimal('0.01')),
                'sort_key': (order.claimed_at, 3, order.pk),
                'reserved_change': Decimal(str(order.sacks)).quantize(Decimal('0.01')) * Decimal('-1'),
            })
        elif order.order_status == RiceSale.ORDER_STATUS_CANCELLED and order.cancelled_at:
            rows.append({
                'date': order.cancelled_at,
                'type': 'reservation_released',
                'type_label': 'Reservation Released',
                'source': f'{order.reference_number} - Reservation cancelled',
                'stock_in': None,
                'stock_out': None,
                'sort_key': (order.cancelled_at, 2, order.pk),
                'reserved_change': Decimal(str(order.sacks)).quantize(Decimal('0.01')) * Decimal('-1'),
            })

    rows.sort(key=lambda item: item['sort_key'])

    actual_balance = Decimal('0.00')
    reserved_balance = Decimal('0.00')
    for row in rows:
        if row['stock_in']:
            actual_balance += row['stock_in']
        if row['stock_out']:
            actual_balance -= row['stock_out']
        reserved_balance += row.get('reserved_change', Decimal('0.00'))
        row['actual_balance'] = actual_balance.quantize(Decimal('0.01'))
        row['reserved_balance'] = max(reserved_balance, Decimal('0.00')).quantize(Decimal('0.01'))
        row['available_balance'] = max(actual_balance - reserved_balance, Decimal('0.00')).quantize(Decimal('0.01'))
    return rows


def _record_rice_order_payment(order, amount_received, processed_by):
    amount_received = Decimal(str(amount_received)).quantize(Decimal('0.01'))
    if amount_received < order.total_amount:
        raise ValueError('Cash received cannot be less than the total amount due.')

    order.amount_paid = amount_received
    order.change_given = (amount_received - order.total_amount).quantize(Decimal('0.01'))
    order.payment_status = RiceSale.PAYMENT_STATUS_PAID
    order.order_status = RiceSale.ORDER_STATUS_CLAIMED
    order.paid_at = timezone.now()
    order.claimed_at = timezone.now()
    order.processed_by = processed_by
    order.save(update_fields=[
        'amount_paid',
        'change_given',
        'payment_status',
        'order_status',
        'paid_at',
        'claimed_at',
        'processed_by',
    ])


def _approved_member(user):
    return bool(
        user.is_authenticated
        and not user.is_staff
        and not user.is_superuser
        and user.is_verified
        and MembershipApplication.objects.filter(
            user=user,
            is_approved=True,
            is_rejected=False,
        ).exists()
    )


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
    membership_content_type = ContentType.objects.get_for_model(MembershipApplication)
    membership_payment_ids = set(
        Payment.objects.filter(
            status='completed',
            payment_type='membership',
            content_type=membership_content_type,
        ).values_list('object_id', flat=True)
    )
    completed_transactions = (
        Payment.objects.filter(status='completed').count()
        + RiceSale.objects.filter(payment_status=RiceSale.PAYMENT_STATUS_PAID).count()
        + MembershipApplication.objects.filter(payment_status='paid').exclude(pk__in=membership_payment_ids).count()
    )
    verified_members = User.objects.filter(role=User.REGULAR_USER, is_verified=True).count()
    active_machines = Machine.objects.filter(status='available').count()

    context = {
        'overview_stats': {
            'total_rentals': total_rentals,
            'in_kind_rentals': in_kind_rentals,
            'completed_transactions': completed_transactions,
            'verified_members': verified_members,
            'active_machines': active_machines,
        }
    }
    return render(request, 'reports/index.html', context)

@login_required
@user_passes_test(is_admin)
def rental_report(request):
    """Generate rental transactions report with filters."""
    return render(request, 'reports/rental_report.html', _rental_report_context(request))


@login_required
@user_passes_test(is_admin)
def harvest_report(request):
    """Generate harvest and BUFIA share report for in-kind rentals."""
    return render(request, 'reports/harvest_report.html', _harvest_report_context(request))


@login_required
@user_passes_test(is_admin)
def rice_sales_report(request):
    context = _rice_sales_report_context()
    settings_obj = context['rice_sale_settings']

    if request.method == 'POST':
        action = (request.POST.get('action') or 'update_settings').strip()
        if action == 'update_settings':
            form = RiceSaleSettingForm(request.POST, instance=settings_obj)
            if form.is_valid():
                settings_obj = form.save(commit=False)
                settings_obj.updated_by = request.user
                settings_obj.save()
                messages.success(request, 'Rice sale availability and pricing were updated.')
                return redirect('reports:rice_sales_report')
            context['rice_sale_settings_form'] = form
        else:
            order = get_object_or_404(RiceSale, pk=request.POST.get('order_id'))
            if action == 'mark_ready':
                if order.order_status == RiceSale.ORDER_STATUS_RESERVED:
                    order.order_status = RiceSale.ORDER_STATUS_READY
                    order.ready_at = timezone.now()
                    order.processed_by = request.user
                    order.save(update_fields=['order_status', 'ready_at', 'processed_by'])
                    messages.success(request, f'{order.reference_number} marked as ready for pickup.')
            elif action == 'mark_claimed':
                if order.payment_status != RiceSale.PAYMENT_STATUS_PAID:
                    messages.error(request, 'Record payment first before marking this order as claimed.')
                else:
                    order.order_status = RiceSale.ORDER_STATUS_CLAIMED
                    order.claimed_at = timezone.now()
                    order.processed_by = request.user
                    order.save(update_fields=['order_status', 'claimed_at', 'processed_by'])
                    messages.success(request, f'{order.reference_number} marked as claimed.')
            elif action == 'cancel_order':
                if order.order_status != RiceSale.ORDER_STATUS_CLAIMED:
                    order.order_status = RiceSale.ORDER_STATUS_CANCELLED
                    order.cancelled_at = timezone.now()
                    order.processed_by = request.user
                    order.save(update_fields=['order_status', 'cancelled_at', 'processed_by'])
                    messages.success(request, f'{order.reference_number} was cancelled and stock was released.')
                else:
                    messages.error(request, 'Claimed orders cannot be cancelled.')
            elif action == 'record_otc_payment':
                payment_form = RiceOrderPaymentForm(request.POST)
                if payment_form.is_valid():
                    try:
                        _record_rice_order_payment(
                            order,
                            payment_form.cleaned_data['amount_received'],
                            request.user,
                        )
                        messages.success(
                            request,
                            f'{order.reference_number} paid and claimed. Change given: PHP {order.change_given:.2f}.'
                        )
                    except ValueError as exc:
                        messages.error(request, str(exc))
                else:
                    messages.error(request, 'Enter a valid cash amount before recording OTC payment.')
            return redirect('reports:rice_sales_report')

    return render(request, 'reports/rice_sales_report.html', context)


@login_required
def rice_store(request):
    if not _approved_member(request.user):
        messages.error(request, 'Only approved members can buy BUFIA rice.')
        return redirect('dashboard')

    sale_settings = _rice_sale_setting()
    inventory = _rice_inventory_snapshot()
    purchase_form = RicePurchaseForm()

    if request.method == 'POST':
        purchase_form = RicePurchaseForm(request.POST)
        if not sale_settings.is_available_for_sale:
            messages.error(request, 'BUFIA rice is not currently available for sale.')
        elif sale_settings.current_price_per_sack <= 0:
            messages.error(request, 'Rice pricing is not set yet. Please try again later.')
        elif purchase_form.is_valid():
            sacks = purchase_form.cleaned_data['sacks']
            notes = purchase_form.cleaned_data.get('notes', '')
            pickup_date = purchase_form.cleaned_data['pickup_date']
            rice_type = purchase_form.cleaned_data.get('rice_type', '')
            payment_method = purchase_form.cleaned_data.get('payment_method') or RiceSale.PAYMENT_METHOD_OTC
            with transaction.atomic():
                inventory = _rice_inventory_snapshot()
                if sacks > inventory['available_sacks']:
                    purchase_form.add_error('sacks', f'Only {inventory["available_sacks"]:.2f} sacks are available right now.')
                else:
                    is_gcash = payment_method == RiceSale.PAYMENT_METHOD_GCASH
                    order = RiceSale.objects.create(
                        buyer=request.user,
                        rice_type=rice_type,
                        sacks=sacks,
                        price_per_sack=sale_settings.current_price_per_sack,
                        pickup_date=pickup_date,
                        payment_method=payment_method,
                        payment_status=RiceSale.PAYMENT_STATUS_PAID if is_gcash else RiceSale.PAYMENT_STATUS_PENDING,
                        amount_paid=(sacks * sale_settings.current_price_per_sack).quantize(Decimal('0.01')) if is_gcash else None,
                        paid_at=timezone.now() if is_gcash else None,
                        notes=notes,
                    )
                    messages.success(
                        request,
                        (
                            f'Rice order reserved for pickup on {pickup_date:%b %d, %Y}. '
                            + (
                                'Payment was recorded through Gcash. '
                                if is_gcash
                                else 'Payment will be collected at pickup. '
                            )
                            + f'Reference: {order.reference_number}.'
                        )
                    )
                    return redirect('reports:rice_store')

    member_sales = RiceSale.objects.filter(buyer=request.user).order_by('-created_at', '-id')
    context = {
        'rice_sale_settings': sale_settings,
        'rice_inventory': inventory,
        'purchase_form': purchase_form,
        'member_sales': member_sales,
    }
    return render(request, 'reports/rice_store.html', context)


@login_required
@user_passes_test(is_admin)
def financial_summary(request):
    """Generate financial summary report."""
    return render(request, 'reports/financial_summary.html', _financial_summary_context(request))


@login_required
@user_passes_test(is_admin)
def machine_usage_report(request):
    """Generate machine usage and utilization report."""
    return render(request, 'reports/machine_usage_report.html', _machine_usage_report_context(request))


@login_required
@user_passes_test(is_admin)
def machine_usage_detail(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    date_filters = _resolve_date_filters(request)
    profitability = _machine_profitability_snapshot(machine, date_filters)

    rental_history = Rental.objects.filter(machine=machine).exclude(payment_type='in_kind').filter(
        payment_amount__isnull=False,
    ).filter(
        Q(payment_verified=True) | Q(payment_status='paid')
    ).order_by('-start_date')[:10]
    rice_history = RiceMillAppointment.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    ).order_by('-appointment_date', '-created_at')[:10]
    dryer_history = DryerRental.objects.filter(
        machine=machine,
        total_amount__isnull=False,
        status__in=SERVICE_REVENUE_STATUSES,
    ).order_by('-rental_date', '-created_at')[:10]

    is_rice_mill = machine.is_rice_mill()
    is_dryer_service = machine.is_dryer_service()
    is_harvester = machine.machine_type == 'harvester'
    
    if is_harvester:
        # For harvesters, show rice sales as income
        rice_sales_query = RiceSale.objects.filter(
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
        )
        if date_filters['start_value']:
            rice_sales_query = rice_sales_query.filter(paid_at__date__gte=date_filters['start_value'])
        if date_filters['end_value']:
            rice_sales_query = rice_sales_query.filter(paid_at__date__lte=date_filters['end_value'])
        
        rice_sales = rice_sales_query.order_by('-paid_at')[:10]
        income_rows = [
            {
                'date': sale.paid_at.date() if sale.paid_at else sale.created_at.date(),
                'source': 'Rice Sale',
                'amount': sale.sacks * sale.price_per_sack,
                'reference': sale.reference_number,
                'customer': sale.buyer.get_full_name() or sale.buyer.username,
                'details': f'{sale.sacks} sacks @ PHP {sale.price_per_sack}/sack',
            }
            for sale in rice_sales
        ]
        income_section_title = 'Recent Rice Sales Income'
        income_section_meta = 'Revenue from rice harvested and sold to members.'
    elif is_rice_mill:
        income_rows = [
            {
                'date': appointment.appointment_date,
                'source': 'Rice Mill',
                'amount': appointment.total_amount,
                'reference': appointment.reference_number or appointment.transaction_id,
                'customer': appointment.customer_display_name,
            }
            for appointment in rice_history
        ]
        income_section_title = 'Recent Rice Mill Income Records'
        income_section_meta = 'Completed rice mill transactions tied to this machine.'
    elif is_dryer_service:
        income_rows = [
            {
                'date': dryer.rental_date,
                'source': 'Dryer',
                'amount': dryer.total_amount,
                'reference': dryer.reference_number or dryer.transaction_id,
                'customer': dryer.customer_display_name,
            }
            for dryer in dryer_history
        ]
        income_section_title = 'Recent Dryer Income Records'
        income_section_meta = 'Completed dryer service transactions tied to this machine.'
    else:
        income_rows = [
            {
                'date': rental.start_date,
                'source': 'Rental',
                'amount': rental.payment_amount,
                'reference': rental.transaction_id or rental.get_transaction_id,
                'customer': rental.user.get_full_name() or rental.user.username,
            }
            for rental in rental_history
        ]
        income_section_title = 'Recent Rental Income Records'
        income_section_meta = 'Completed rental transactions tied to this machine.'

    context = {
        'machine': machine,
        'profitability': profitability,
        'maintenance_timeline': _machine_maintenance_timeline(machine),
        'is_rice_mill': is_rice_mill,
        'is_dryer_service': is_dryer_service,
        'income_rows': income_rows,
        'income_section_title': income_section_title,
        'income_section_meta': income_section_meta,
        'rental_history': rental_history,
        'rice_history': rice_history,
        'dryer_history': dryer_history,
        'date_range_options': DATE_RANGE_CHOICES,
        'filters': {
            'date_range': date_filters['date_range'],
            'date_range_label': date_filters['date_range_label'],
            'start_date': date_filters['start_date'],
            'end_date': date_filters['end_date'],
        },
    }
    return render(request, 'reports/machine_usage_detail.html', context)


@login_required
@user_passes_test(is_admin)
def membership_report(request):
    """Generate membership status report."""
    return render(request, 'reports/membership_report.html', _membership_report_context(request))


@login_required
@user_passes_test(is_admin)
def membership_proof_detail(request, pk):
    """Show uploaded land ownership or tenancy proof from the membership reports module."""
    application = get_object_or_404(
        MembershipApplication.objects.select_related('user', 'assigned_sector', 'reviewed_by').prefetch_related('proof_documents'),
        pk=pk,
    )
    _sync_membership_application_proofs(application)

    proof_form = MembershipProofUploadForm(
        initial={'land_proof_notes': application.land_proof_notes},
        require_document=application.available_land_proof_count == 0,
        existing_count=application.available_land_proof_count,
    )

    if request.method == 'POST' and 'proof_upload_submit' in request.POST:
        proof_form = MembershipProofUploadForm(
            request.POST,
            request.FILES,
            require_document=application.available_land_proof_count == 0,
            existing_count=application.available_land_proof_count,
        )
        if proof_form.is_valid():
            application.land_proof_notes = proof_form.cleaned_data.get('land_proof_notes', '')
            application.save(update_fields=['land_proof_notes'])

            proof_files = proof_form.cleaned_data.get('land_proof_documents') or []
            if proof_files:
                _append_membership_application_proofs(application, proof_files)

            messages.success(request, 'Land ownership or tenancy proof saved successfully.')
            return redirect('reports:membership_proof_detail', pk=pk)

        messages.error(request, 'Please correct the proof upload form and try again.')

    return render(
        request,
        'reports/membership_proof_detail.html',
        {
            'application': application,
            'proof_form': proof_form,
        },
    )


@login_required
@user_passes_test(is_admin)
def export_rental_report(request):
    """Export rental report to CSV."""
    rentals = _rental_report_context(request)['rentals']

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
            rental.customer_display_name,
            rental.machine.name,
            rental.start_date,
            rental.end_date,
            rental.get_duration_days(),
            rental.area or 'N/A',
            rental.payment_amount or 0,
            rental.workflow_payment_type_display,
            rental.payment_status,
            rental.status,
        ])

    return response


@login_required
@user_passes_test(is_admin)
def export_rental_report_excel(request):
    context = _rental_report_context(request)
    filters = context['filters']
    headers = [
        'Transaction ID', 'Member', 'Machine', 'Start Date', 'End Date',
        'Duration (Days)', 'Area (Ha)', 'Amount', 'Payment Type', 'Payment Status', 'Rental Status',
    ]
    rows = [
        [
            rental.transaction_id or f'RENTAL-{rental.id:05d}',
            rental.customer_display_name,
            rental.machine.name,
            rental.start_date,
            rental.end_date,
            rental.get_duration_days(),
            rental.area or 'N/A',
            f'PHP {rental.payment_amount or 0:,.2f}' if rental.payment_amount is not None else 'PHP 0.00',
            rental.workflow_payment_type_display,
            rental.payment_status,
            rental.status,
        ]
        for rental in context['rentals']
    ]
    filter_details = [
        ('Date Range', filters['date_range_label']),
        ('Machine', filters['machine_label']),
        ('Member', filters['member_label']),
        ('Status', filters['status_label']),
    ]
    return _xlsx_response(
        prefix='rental_report',
        title='Rental Transactions Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[18, 24, 18, 13, 13, 12, 11, 14, 18, 16, 14],
        sheet_name='Rental Report',
    )


@login_required
@user_passes_test(is_admin)
def export_rental_report_pdf(request):
    context = _rental_report_context(request)
    filters = context['filters']
    headers = [
        'Transaction ID', 'Member', 'Machine', 'Start Date', 'End Date',
        'Days', 'Area', 'Amount', 'Payment Type', 'Payment Status', 'Rental Status',
    ]
    rows = [
        [
            rental.transaction_id or f'RENTAL-{rental.id:05d}',
            rental.customer_display_name,
            rental.machine.name,
            rental.start_date.strftime('%Y-%m-%d'),
            rental.end_date.strftime('%Y-%m-%d'),
            rental.get_duration_days(),
            rental.area or 'N/A',
            f'PHP {rental.payment_amount or 0:,.2f}' if rental.payment_amount is not None else 'PHP 0.00',
            rental.workflow_payment_type_display,
            rental.payment_status,
            rental.status,
        ]
        for rental in context['rentals']
    ]
    filter_details = [
        ('Date Range', filters['date_range_label']),
        ('Machine', filters['machine_label']),
        ('Member', filters['member_label']),
        ('Status', filters['status_label']),
    ]
    return _pdf_response(
        prefix='rental_report',
        title='Rental Transactions Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[18, 23, 16, 11, 11, 8, 8, 12, 15, 12, 12],
        inline=_wants_pdf_preview(request),
    )


@login_required
@user_passes_test(is_admin)
def export_harvest_report(request):
    """Export harvest report to CSV."""
    harvest_data = _harvest_report_context(request)['harvest_data']

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="harvest_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Member Name', 'Machine', 'Harvest Date',
        'Total Sacks', 'BUFIA Share', 'Member Share',
        'Delivered To BUFIA', 'Outstanding',
    ])

    for row in harvest_data:
        rental = row['rental']
        writer.writerow([
            row['transaction_id'],
            rental.customer_display_name,
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
def export_harvest_report_excel(request):
    context = _harvest_report_context(request)
    headers = [
        'Transaction ID', 'Member', 'Machine', 'Harvest Date',
        'Total Harvest', 'BUFIA Share', 'Member Share', 'Delivered', 'Outstanding',
    ]
    rows = [
        [
            item['transaction_id'],
            item['rental'].customer_display_name,
            item['rental'].machine.name,
            item['harvest_date'],
            f"{item['rental'].total_harvest_sacks or 0:.2f}",
            f"{item['bufia_share'] or 0:.2f}",
            f"{item['member_share'] or 0:.2f}",
            f"{item['collected'] or 0:.2f}",
            f"{item['outstanding'] or 0:.2f}",
        ]
        for item in context['harvest_data']
    ]
    return _xlsx_response(
        prefix='harvest_report',
        title='Harvest Share Filtered Report',
        filter_details=[('Date Range', context['filters']['date_range_label'])],
        headers=headers,
        rows=rows,
        column_widths=[18, 22, 18, 14, 14, 14, 14, 14, 14],
        sheet_name='Harvest Report',
    )


@login_required
@user_passes_test(is_admin)
def export_harvest_report_pdf(request):
    context = _harvest_report_context(request)
    headers = [
        'Transaction ID', 'Member', 'Machine', 'Harvest Date',
        'Total Harvest', 'BUFIA Share', 'Member Share', 'Delivered', 'Outstanding',
    ]
    rows = [
        [
            item['transaction_id'],
            item['rental'].customer_display_name,
            item['rental'].machine.name,
            item['harvest_date'].strftime('%Y-%m-%d') if item['harvest_date'] else '',
            f"{item['rental'].total_harvest_sacks or 0:.2f}",
            f"{item['bufia_share'] or 0:.2f}",
            f"{item['member_share'] or 0:.2f}",
            f"{item['collected'] or 0:.2f}",
            f"{item['outstanding'] or 0:.2f}",
        ]
        for item in context['harvest_data']
    ]
    return _pdf_response(
        prefix='harvest_report',
        title='Harvest Share Filtered Report',
        filter_details=[('Date Range', context['filters']['date_range_label'])],
        headers=headers,
        rows=rows,
        column_widths=[18, 20, 16, 12, 12, 12, 12, 12, 12],
        inline=_wants_pdf_preview(request),
    )


@login_required
@user_passes_test(is_admin)
def export_financial_report(request):
    """Export financial summary to CSV."""
    payments = _financial_summary_context(request)['payments']

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="financial_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Transaction ID', 'Member Name', 'Payment Type',
        'Amount Due', 'Payment Method', 'Processed By', 'Status',
    ])

    for payment in payments:
        writer.writerow([
            payment.created_at.strftime('%Y-%m-%d'),
            payment.internal_transaction_id or 'N/A',
            payment.user.get_full_name(),
            payment.payment_type_display,
            payment.amount,
            payment.payment_channel_display,
            _user_display_label(payment.processed_by) if payment.processed_by_id else '',
            payment.status_display,
        ])

    return response


@login_required
@user_passes_test(is_admin)
def export_financial_report_excel(request):
    context = _financial_summary_context(request)
    headers = ['Date', 'Transaction ID', 'Member', 'Payment Type', 'Amount Due', 'Payment Method', 'Processed By', 'Status']
    rows = [
        [
            payment.created_at.strftime('%Y-%m-%d'),
            payment.internal_transaction_id or 'N/A',
            _user_display_label(payment.user),
            payment.payment_type_display,
            f'PHP {payment.amount:,.2f}',
            payment.payment_channel_display,
            _user_display_label(payment.processed_by) if payment.processed_by_id else 'N/A',
            payment.status_display,
        ]
        for payment in context['payments']
    ]
    return _xlsx_response(
        prefix='financial_report',
        title='Financial Summary Filtered Report',
        filter_details=[('Date Range', context['filters']['date_range_label'])],
        headers=headers,
        rows=rows,
        column_widths=[14, 22, 24, 18, 14, 16, 18, 12],
        sheet_name='Financial Report',
    )


@login_required
@user_passes_test(is_admin)
def export_financial_report_pdf(request):
    context = _financial_summary_context(request)
    headers = ['Date', 'Transaction ID', 'Member', 'Payment Type', 'Amount Due', 'Payment Method', 'Processed By', 'Status']
    rows = [
        [
            payment.created_at.strftime('%Y-%m-%d'),
            payment.internal_transaction_id or 'N/A',
            _user_display_label(payment.user),
            payment.payment_type_display,
            f'PHP {payment.amount:,.2f}',
            payment.payment_channel_display,
            _user_display_label(payment.processed_by) if payment.processed_by_id else 'N/A',
            payment.status_display,
        ]
        for payment in context['payments']
    ]
    return _pdf_response(
        prefix='financial_report',
        title='Financial Summary Filtered Report',
        filter_details=[('Date Range', context['filters']['date_range_label'])],
        headers=headers,
        rows=rows,
        column_widths=[11, 18, 20, 15, 11, 13, 16, 10],
        inline=_wants_pdf_preview(request),
    )


@login_required
@user_passes_test(is_admin)
def export_machine_usage_report_excel(request):
    context = _machine_usage_report_context(request)
    headers = ['Machine', 'Type', 'Brand', 'Model', 'Year', 'Acquired', 'Acquisition Cost', 'Operating Cost', 'Recovery Remaining', 'Rental Count', 'Rental Days', 'Revenue', 'Net Profit', 'ROI %', 'Maintenance Records', 'Utilization %']
    rows = [
        [
            item['machine'].name,
            item['machine'].get_machine_type_display() if hasattr(item['machine'], 'get_machine_type_display') else item['machine'].machine_type,
            item['machine'].brand_name or 'Not recorded',
            item['machine'].model_name or 'Not recorded',
            item['machine'].model_year or 'Not recorded',
            item['machine'].acquisition_date.strftime('%Y-%m-%d') if item['machine'].acquisition_date else 'Not recorded',
            f'PHP {item["acquisition_amount"]:,.2f}',
            f'PHP {item["operating_cost"]:,.2f}',
            f'PHP {item["payback_remaining"]:,.2f}' if item['payback_remaining'] is not None else 'N/A',
            item['rental_count'],
            item['total_days'],
            f'PHP {item["revenue"]:,.2f}',
            f'PHP {item["net_profit"]:,.2f}',
            f'{item["roi_percent"]:.2f}%' if item['roi_percent'] is not None else 'N/A',
            item['maintenance_count'],
            f'{item["utilization_rate"]:.2f}%',
        ]
        for item in context['usage_data']
    ]
    filter_details = [
        ('Date Range', context['filters']['date_range_label']),
        ('Machine', context['filters']['machine_label']),
    ]
    return _xlsx_response(
        prefix='machine_usage_report',
        title='Machine Usage Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[22, 16, 14, 16, 9, 12, 14, 14, 14, 10, 10, 12, 12, 9, 14, 10],
        sheet_name='Machine Usage',
    )


@login_required
@user_passes_test(is_admin)
def export_machine_usage_report_pdf(request):
    context = _machine_usage_report_context(request)
    headers = ['Machine', 'Type', 'Brand', 'Model', 'Year', 'Acquired', 'Cost', 'Op. Cost', 'Recover', 'Rentals', 'Days', 'Revenue', 'Net', 'ROI', 'Maint.', 'Util. %']
    rows = [
        [
            item['machine'].name,
            item['machine'].get_machine_type_display() if hasattr(item['machine'], 'get_machine_type_display') else item['machine'].machine_type,
            item['machine'].brand_name or 'Not recorded',
            item['machine'].model_name or 'Not recorded',
            item['machine'].model_year or 'Not recorded',
            item['machine'].acquisition_date.strftime('%Y-%m-%d') if item['machine'].acquisition_date else 'Not recorded',
            f'PHP {item["acquisition_amount"]:,.2f}',
            f'PHP {item["operating_cost"]:,.2f}',
            f'PHP {item["payback_remaining"]:,.2f}' if item['payback_remaining'] is not None else 'N/A',
            item['rental_count'],
            item['total_days'],
            f'PHP {item["revenue"]:,.2f}',
            f'PHP {item["net_profit"]:,.2f}',
            f'{item["roi_percent"]:.2f}%' if item['roi_percent'] is not None else 'N/A',
            item['maintenance_count'],
            f'{item["utilization_rate"]:.2f}%',
        ]
        for item in context['usage_data']
    ]
    filter_details = [
        ('Date Range', context['filters']['date_range_label']),
        ('Machine', context['filters']['machine_label']),
    ]
    return _pdf_response(
        prefix='machine_usage_report',
        title='Machine Usage Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[16, 12, 10, 12, 7, 10, 10, 10, 10, 7, 7, 9, 9, 7, 7, 7],
        inline=_wants_pdf_preview(request),
    )


@login_required
@user_passes_test(is_admin)
def export_membership_report_excel(request):
    context = _membership_report_context(request)
    headers = ['Member', 'Username', 'Email', 'Phone', 'Sector', 'Joined', 'Approved', 'Status', 'Role']
    rows = [
        [
            _user_display_label(member),
            member.username,
            member.email or 'No email',
            member.phone_number or 'No phone',
            (
                member.membership_application.assigned_sector.name
                if getattr(member, 'membership_application', None) and member.membership_application and member.membership_application.assigned_sector
                else 'Unassigned'
            ),
            member.date_joined.strftime('%Y-%m-%d'),
            member.membership_approved_date.strftime('%Y-%m-%d') if member.membership_approved_date else 'N/A',
            'Verified' if member.is_verified else ('Pending' if member.membership_form_submitted else 'Not Submitted'),
            'Admin' if member.is_superuser else member.get_role_display(),
        ]
        for member in context['members']
    ]
    filter_details = [
        ('Date Range', context['filters']['date_range_label']),
        ('Member Status', context['filters']['filter_type_label']),
    ]
    return _xlsx_response(
        prefix='membership_report',
        title='Membership Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[22, 16, 26, 16, 18, 14, 14, 14, 14],
        sheet_name='Membership',
    )


@login_required
@user_passes_test(is_admin)
def export_membership_report_pdf(request):
    context = _membership_report_context(request)
    headers = ['Member', 'Username', 'Email', 'Phone', 'Sector', 'Joined', 'Approved', 'Status', 'Role']
    rows = [
        [
            _user_display_label(member),
            member.username,
            member.email or 'No email',
            member.phone_number or 'No phone',
            (
                member.membership_application.assigned_sector.name
                if getattr(member, 'membership_application', None) and member.membership_application and member.membership_application.assigned_sector
                else 'Unassigned'
            ),
            member.date_joined.strftime('%Y-%m-%d'),
            member.membership_approved_date.strftime('%Y-%m-%d') if member.membership_approved_date else 'N/A',
            'Verified' if member.is_verified else ('Pending' if member.membership_form_submitted else 'Not Submitted'),
            'Admin' if member.is_superuser else member.get_role_display(),
        ]
        for member in context['members']
    ]
    filter_details = [
        ('Date Range', context['filters']['date_range_label']),
        ('Member Status', context['filters']['filter_type_label']),
    ]
    return _pdf_response(
        prefix='membership_report',
        title='Membership Filtered Report',
        filter_details=filter_details,
        headers=headers,
        rows=rows,
        column_widths=[20, 12, 22, 13, 15, 11, 11, 11, 10],
        inline=_wants_pdf_preview(request),
    )


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
