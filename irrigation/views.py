from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CroppingSeasonForm,
    IrrigationPaymentConfirmationForm,
    IrrigationSeasonRecordAdminForm,
    IrrigationSeasonAssignmentForm,
)
from .models import CroppingSeason, IrrigationSeasonRecord


def is_admin_or_president(user):
    return user.is_superuser or user.is_staff


def _sync_irrigation_seasons():
    for season in CroppingSeason.objects.exclude(status=CroppingSeason.STATUS_CLOSED):
        season.sync_status()


def _normalize_irrigation_record_status(record):
    """Repair stale irrigation record statuses so payment/admin screens stay usable."""
    if not record:
        return record

    season_status = getattr(record.season, 'status', None)
    billing_locked = bool(getattr(record.season, 'billing_generated_at', None)) or season_status in [
        CroppingSeason.STATUS_HARVESTED,
        CroppingSeason.STATUS_PAID,
        CroppingSeason.STATUS_CLOSED,
    ]

    if (record.total_fee or 0) > 0 and record.balance_due > 0 and billing_locked and record.status in [
        IrrigationSeasonRecord.STATUS_PLANNED,
        IrrigationSeasonRecord.STATUS_ACTIVE,
        IrrigationSeasonRecord.STATUS_CLOSED,
    ]:
        record.status = IrrigationSeasonRecord.STATUS_HARVESTED
        record.save(update_fields=['status', 'updated_at'])
    elif record.balance_due <= 0 and record.status not in [
        IrrigationSeasonRecord.STATUS_PAID,
        IrrigationSeasonRecord.STATUS_CLOSED,
    ]:
        record.status = IrrigationSeasonRecord.STATUS_PAID
        record.save(update_fields=['status', 'updated_at'])

    return record


@login_required
def irrigation_request_create(request):
    messages.info(
        request,
        'Irrigation is now managed by cropping season. Farmers cannot manually request irrigation. '
        'You can view your assigned season and billing below.'
    )
    return redirect('irrigation:irrigation_request_list')


@login_required
def irrigation_request_list(request):
    if request.user.is_superuser or request.user.is_staff:
        return redirect('irrigation:admin_irrigation_request_list')
    _sync_irrigation_seasons()
    records = IrrigationSeasonRecord.objects.filter(
        farmer=request.user
    ).select_related('season', 'sector').order_by('-season__planting_date', '-created_at')

    active_records = records.exclude(
        status__in=[IrrigationSeasonRecord.STATUS_PAID, IrrigationSeasonRecord.STATUS_CLOSED]
    )
    closed_records = records.filter(
        status__in=[IrrigationSeasonRecord.STATUS_PAID, IrrigationSeasonRecord.STATUS_CLOSED]
    )

    total_due = sum((record.total_fee for record in records), start=0)
    total_paid = sum((record.amount_paid for record in records), start=0)

    return render(request, 'irrigation/request_list.html', {
        'records': records,
        'active_records': active_records,
        'closed_records': closed_records,
        'total_due': total_due,
        'total_paid': total_paid,
    })


@login_required
def irrigation_request_detail(request, pk):
    if request.user.is_superuser or request.user.is_staff:
        return redirect('irrigation:admin_irrigation_request_list')
    _sync_irrigation_seasons()
    record = get_object_or_404(
        IrrigationSeasonRecord.objects.select_related('season', 'sector', 'payment_confirmed_by'),
        pk=pk,
        farmer=request.user
    )
    return render(request, 'irrigation/request_detail.html', {'record': record})


@login_required
def irrigation_request_cancel(request, pk):
    messages.info(request, 'Irrigation assignments are season-based and cannot be cancelled by farmers.')
    return redirect('irrigation:irrigation_request_detail', pk=pk)


@login_required
def water_tender_irrigation_request_list(request):
    messages.info(request, 'Irrigation scheduling is now handled by admin-managed cropping seasons.')
    return redirect('irrigation:irrigation_request_list')


@login_required
def water_tender_irrigation_request_detail(request, pk):
    messages.info(request, 'Irrigation scheduling is now handled by admin-managed cropping seasons.')
    return redirect('irrigation:irrigation_request_list')


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_list(request):
    _sync_irrigation_seasons()
    seasons = CroppingSeason.objects.prefetch_related('records__farmer').order_by('-planting_date', '-created_at')
    records = IrrigationSeasonRecord.objects.select_related('season', 'farmer', 'sector').order_by(
        '-season__planting_date', 'farmer__last_name'
    )
    for record in records:
        _normalize_irrigation_record_status(record)
    outstanding_records = records.filter(
        total_fee__gt=0,
        amount_paid__lt=F('total_fee'),
        status__in=[
            IrrigationSeasonRecord.STATUS_HARVESTED,
            IrrigationSeasonRecord.STATUS_ACTIVE,
            IrrigationSeasonRecord.STATUS_PLANNED,
        ],
    ).order_by('-season__planting_date', 'farmer__last_name')
    irrigation_totals = records.aggregate(
        total_billed=Sum('total_fee'),
        total_collected=Sum('amount_paid'),
    )
    outstanding_totals = outstanding_records.aggregate(
        total_billed=Sum('total_fee'),
        total_collected=Sum('amount_paid'),
    )
    total_billed = irrigation_totals['total_billed'] or 0
    total_collected = irrigation_totals['total_collected'] or 0
    total_outstanding = (outstanding_totals['total_billed'] or 0) - (outstanding_totals['total_collected'] or 0)

    return render(request, 'irrigation/admin_request_list.html', {
        'seasons': seasons,
        'records': records[:12],
        'planned_count': seasons.filter(status=CroppingSeason.STATUS_PLANNED).count(),
        'active_count': seasons.filter(status=CroppingSeason.STATUS_ACTIVE).count(),
        'harvested_count': seasons.filter(status=CroppingSeason.STATUS_HARVESTED).count(),
        'paid_count': seasons.filter(status=CroppingSeason.STATUS_PAID).count(),
        'closed_count': seasons.filter(status=CroppingSeason.STATUS_CLOSED).count(),
        'total_billed': total_billed,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'paid_records_count': records.filter(amount_paid__gt=0).count(),
        'outstanding_records': outstanding_records[:12],
        'outstanding_users_count': outstanding_records.count(),
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_create(request):
    if request.method == 'POST':
        form = CroppingSeasonForm(request.POST)
        if form.is_valid():
            season = form.save(commit=False)
            season.created_by = request.user
            season.save()
            messages.success(request, 'Cropping season created. You can now assign farmers.')
            return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)
        messages.error(request, 'Please correct the irrigation season form errors below.')
    else:
        form = CroppingSeasonForm()

    return render(request, 'irrigation/admin_request_create.html', {'form': form})


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_edit(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method == 'POST':
        form = CroppingSeasonForm(request.POST, instance=season)
        if form.is_valid():
            season = form.save()
            season.sync_status()
            messages.success(request, 'Cropping season details updated.')
            return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)
        messages.error(request, 'Please correct the irrigation season form errors below.')
    else:
        form = CroppingSeasonForm(instance=season)

    return render(request, 'irrigation/admin_request_create.html', {
        'form': form,
        'season': season,
        'is_edit_mode': True,
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_detail(request, pk):
    _sync_irrigation_seasons()
    season = get_object_or_404(CroppingSeason.objects.prefetch_related('records__farmer', 'records__sector'), pk=pk)
    records = season.records.select_related('farmer', 'sector', 'membership').all()
    for record in records:
        _normalize_irrigation_record_status(record)
    season_outstanding_amount = season.total_billed_amount - season.total_paid_amount
    can_assign_farmers = season.status in [CroppingSeason.STATUS_PLANNED, CroppingSeason.STATUS_ACTIVE] and not season.billing_generated_at
    can_generate_billing = (
        season.status != CroppingSeason.STATUS_CLOSED
        and not season.billing_generated_at
        and season.is_harvest_due
        and records.exists()
    )
    can_close_season = season.status == CroppingSeason.STATUS_PAID or not records.exists()
    assignment_form = IrrigationSeasonAssignmentForm(season=season) if can_assign_farmers else None

    return render(request, 'irrigation/admin_request_detail.html', {
        'season': season,
        'assignment_form': assignment_form,
        'records': records,
        'season_outstanding_amount': season_outstanding_amount,
        'can_assign_farmers': can_assign_farmers,
        'can_generate_billing': can_generate_billing,
        'can_close_season': can_close_season,
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_assign_farmers(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method != 'POST':
        return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)
    if season.status not in [CroppingSeason.STATUS_PLANNED, CroppingSeason.STATUS_ACTIVE] or season.billing_generated_at:
        messages.error(request, 'Farmers can only be assigned before irrigation billing has been generated.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)

    form = IrrigationSeasonAssignmentForm(request.POST, season=season)
    if not form.is_valid():
        messages.error(request, 'Please choose at least one farmer to assign.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)

    created_count = 0
    for farmer in form.cleaned_data['farmers']:
        membership = getattr(farmer, 'membership_application', None)
        record, created = IrrigationSeasonRecord.objects.get_or_create(
            season=season,
            farmer=farmer,
            defaults={
                'membership': membership,
                'sector': getattr(membership, 'assigned_sector', None) or getattr(membership, 'sector', None),
                'farm_area': getattr(membership, 'farm_size', 0) or 0,
                'irrigation_rate': season.irrigation_rate_per_hectare,
                'status': IrrigationSeasonRecord.STATUS_PLANNED,
            }
        )
        if created:
            record.total_fee = record.calculate_total_fee()
            record.save(update_fields=['total_fee', 'updated_at'])
            created_count += 1

    if created_count:
        messages.success(request, f'{created_count} farmer(s) assigned to {season.name}.')
    else:
        messages.info(request, 'No new farmers were assigned.')
    return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_generate_billing(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method == 'POST':
        if season.status == CroppingSeason.STATUS_CLOSED:
            messages.error(request, 'Closed seasons cannot generate new irrigation billing.')
        elif not season.records.exists():
            messages.error(request, 'Assign at least one farmer before generating irrigation billing.')
        elif season.billing_generated_at or season.status in [CroppingSeason.STATUS_HARVESTED, CroppingSeason.STATUS_PAID]:
            messages.info(request, 'Irrigation billing has already been generated for this season.')
        elif timezone.localdate() < season.harvest_date:
            messages.error(request, 'Billing can only be generated on or after the harvest date.')
        else:
            season.generate_billing()
            messages.success(request, 'Harvest date reached. Irrigation billing was generated automatically based on farm area.')
    return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_confirm_payment(request, pk):
    record = get_object_or_404(IrrigationSeasonRecord.objects.select_related('season'), pk=pk)
    _normalize_irrigation_record_status(record)
    if request.method != 'POST':
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if (record.total_fee or 0) <= 0 or record.balance_due <= 0:
        messages.error(request, 'This irrigation record has no remaining billed balance to confirm.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    form = IrrigationPaymentConfirmationForm(request.POST, instance=record)
    if form.is_valid():
        record = form.save(commit=False)
        record.mark_paid(confirmed_by=request.user, amount=form.cleaned_data['amount_paid'])
        if record.season.all_records_paid and record.season.status != CroppingSeason.STATUS_CLOSED:
            record.season.status = CroppingSeason.STATUS_PAID
            record.season.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Cash payment confirmed for {record.farmer.get_full_name() or record.farmer.username}.')
    else:
        messages.error(request, 'Unable to confirm payment. Please check the payment amount.')
    return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_record_edit(request, pk):
    record = get_object_or_404(
        IrrigationSeasonRecord.objects.select_related('season', 'farmer', 'sector'),
        pk=pk,
    )
    _normalize_irrigation_record_status(record)

    if request.method == 'POST':
        payment_form = IrrigationPaymentConfirmationForm(request.POST, instance=record)

        if (record.total_fee or 0) <= 0 or record.balance_due <= 0:
            messages.error(request, 'This irrigation record has no remaining billed balance to confirm.')
        elif payment_form.is_valid():
            record.mark_paid(
                confirmed_by=request.user,
                amount=payment_form.cleaned_data['amount_paid']
            )
            if record.season.all_records_paid and record.season.status != CroppingSeason.STATUS_CLOSED:
                record.season.status = CroppingSeason.STATUS_PAID
                record.season.save(update_fields=['status', 'updated_at'])
            messages.success(
                request,
                f'Cash payment confirmed for {record.farmer.get_full_name() or record.farmer.username}.'
            )
            return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)
        else:
            messages.error(request, 'Unable to confirm payment. Please check the payment amount.')
    else:
        payment_form = IrrigationPaymentConfirmationForm(instance=record)

    return render(request, 'irrigation/admin_record_edit.html', {
        'record': record,
        'payment_form': payment_form,
        'can_mark_paid': (record.total_fee or 0) > 0 and record.balance_due > 0,
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_close_season(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method == 'POST':
        has_records = season.records.exists()
        if has_records and not season.all_records_paid:
            messages.error(request, 'This season still has unpaid irrigation records. Confirm all payments before closing the season.')
        else:
            season.status = CroppingSeason.STATUS_CLOSED
            season.closed_at = timezone.now()
            season.save(update_fields=['status', 'closed_at', 'updated_at'])
            season.records.update(status=IrrigationSeasonRecord.STATUS_CLOSED)
            messages.success(request, f'{season.name} has been closed.')
    return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_history(request):
    _sync_irrigation_seasons()
    records = IrrigationSeasonRecord.objects.select_related('season', 'farmer', 'sector', 'payment_confirmed_by').order_by(
        '-season__planting_date', 'farmer__last_name'
    )
    return render(request, 'irrigation/admin_request_history.html', {'records': records})


@login_required
def user_irrigation_request_history(request):
    _sync_irrigation_seasons()
    records = IrrigationSeasonRecord.objects.filter(farmer=request.user).select_related(
        'season', 'sector', 'payment_confirmed_by'
    ).order_by('-season__planting_date')
    return render(request, 'irrigation/user_request_history.html', {'records': records})
