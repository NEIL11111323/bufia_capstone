from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CroppingSeasonForm,
    IrrigationPaymentConfirmationForm,
    IrrigationSeasonAssignmentForm,
)
from .models import CroppingSeason, IrrigationSeasonRecord


def is_admin_or_president(user):
    return user.is_superuser or user.is_staff


def _sync_irrigation_seasons():
    for season in CroppingSeason.objects.exclude(status=CroppingSeason.STATUS_CLOSED):
        season.sync_status()


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

    return render(request, 'irrigation/admin_request_list.html', {
        'seasons': seasons,
        'records': records[:12],
        'planned_count': seasons.filter(status=CroppingSeason.STATUS_PLANNED).count(),
        'active_count': seasons.filter(status=CroppingSeason.STATUS_ACTIVE).count(),
        'harvested_count': seasons.filter(status=CroppingSeason.STATUS_HARVESTED).count(),
        'paid_count': seasons.filter(status=CroppingSeason.STATUS_PAID).count(),
        'closed_count': seasons.filter(status=CroppingSeason.STATUS_CLOSED).count(),
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
    assignment_form = IrrigationSeasonAssignmentForm(season=season)

    return render(request, 'irrigation/admin_request_detail.html', {
        'season': season,
        'assignment_form': assignment_form,
        'records': season.records.select_related('farmer', 'sector', 'membership').all(),
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_assign_farmers(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method != 'POST':
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
    if request.method != 'POST':
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if record.status not in [IrrigationSeasonRecord.STATUS_HARVESTED, IrrigationSeasonRecord.STATUS_PAID]:
        messages.error(request, 'Cash payment can only be confirmed after billing has been generated.')
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
def admin_irrigation_close_season(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    if request.method == 'POST':
        season.status = CroppingSeason.STATUS_CLOSED
        season.closed_at = timezone.now()
        season.save(update_fields=['status', 'closed_at', 'updated_at'])
        season.records.exclude(status=IrrigationSeasonRecord.STATUS_PAID).update(status=IrrigationSeasonRecord.STATUS_CLOSED)
        season.records.filter(status=IrrigationSeasonRecord.STATUS_PAID).update(status=IrrigationSeasonRecord.STATUS_CLOSED)
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
