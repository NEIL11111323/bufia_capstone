from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from decimal import Decimal

from .forms import (
    CroppingSeasonForm,
    IrrigationPaymentConfirmationForm,
    IrrigationSeasonRecordAdminForm,
    IrrigationSeasonAssignmentForm,
)
from .models import CroppingSeason, IrrigationSeasonRecord
from users.activity import log_activity


def is_admin_or_president(user):
    return user.is_superuser or user.is_staff


def _sync_irrigation_seasons():
    for season in CroppingSeason.objects.exclude(status=CroppingSeason.STATUS_CLOSED):
        season.sync_status()


def _normalize_irrigation_record_status(record):
    """Repair stale irrigation record statuses so payment/admin screens stay usable."""
    if not record:
        return record

    original_status = record.status
    target_status = record.sync_status_from_financials(save=False)
    if target_status != original_status:
        record.save(update_fields=['status', 'updated_at'])

    return record


def _can_confirm_irrigation_payment(record):
    """Only allow cash confirmation after harvest billing is ready for the specific record."""
    if not record:
        return False

    season = getattr(record, 'season', None)
    if not season or season.status == CroppingSeason.STATUS_CLOSED:
        return False

    billing_ready = bool(season.billing_generated_at) or bool(getattr(record, 'billed_at', None))
    return (
        billing_ready
        and record.status == IrrigationSeasonRecord.STATUS_HARVESTED
        and (record.total_fee or 0) > 0
        and record.balance_due > 0
    )


def _can_record_irrigation_walk_in_payment(record):
    if not record:
        return False

    season = getattr(record, 'season', None)
    return (
        bool(season)
        and season.status != CroppingSeason.STATUS_CLOSED
        and record.status != IrrigationSeasonRecord.STATUS_CLOSED
        and (record.total_fee or 0) > 0
        and record.balance_due > 0
    )


def _can_choose_irrigation_payment_method(record):
    return (
        bool(record)
        and record.status == IrrigationSeasonRecord.STATUS_HARVESTED
        and (record.total_fee or 0) > 0
        and record.balance_due > 0
    )


def _get_irrigation_payment(record):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(IrrigationSeasonRecord)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=record.id,
    ).first()


def _append_irrigation_record_note(record, note_text, *, label='Payment note'):
    note_text = (note_text or '').strip()
    if not note_text:
        return

    timestamp = timezone.localtime().strftime('%b %d, %Y %I:%M %p')
    note_entry = f'{label} ({timestamp}): {note_text}'
    record.notes = f'{record.notes}\n{note_entry}'.strip() if record.notes else note_entry
    record.save(update_fields=['notes', 'updated_at'])


def _sync_irrigation_payment_record(record, payment_method):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(IrrigationSeasonRecord)
    amount_due = record.balance_due or record.total_fee or 0
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=record.id,
        defaults={
            'user': record.farmer,
            'payment_type': 'irrigation',
            'amount': amount_due,
            'currency': 'PHP',
            'status': 'pending',
        }
    )

    update_fields = []
    if not created and payment.user_id != record.farmer_id:
        payment.user = record.farmer
        update_fields.append('user')
    if payment.payment_type != 'irrigation':
        payment.payment_type = 'irrigation'
        update_fields.append('payment_type')
    if payment.amount != amount_due:
        payment.amount = amount_due
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != 'pending':
        payment.status = 'pending'
        update_fields.append('status')
    target_provider = (
        'paymongo'
        if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        else 'manual' if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
        else None
    )
    if payment.payment_provider != target_provider:
        payment.payment_provider = target_provider
        update_fields.append('payment_provider')
    if payment.paid_at is not None:
        payment.paid_at = None
        update_fields.append('paid_at')

    if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE:
        if payment.stripe_session_id is not None:
            payment.stripe_session_id = None
            update_fields.append('stripe_session_id')
        if payment.stripe_payment_intent_id is not None:
            payment.stripe_payment_intent_id = None
            update_fields.append('stripe_payment_intent_id')
        if payment.stripe_charge_id is not None:
            payment.stripe_charge_id = None
            update_fields.append('stripe_charge_id')

    if update_fields:
        payment.save(update_fields=update_fields)

    return payment


def _finalize_irrigation_payment_record(record, payment_method, *, session_id=None, payment_intent_id=None):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(IrrigationSeasonRecord)
    paid_amount = record.amount_paid or record.total_fee or 0
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=record.id,
        defaults={
            'user': record.farmer,
            'payment_type': 'irrigation',
            'amount': paid_amount,
            'currency': 'PHP',
            'status': 'completed',
            'payment_provider': 'paymongo' if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE else 'manual',
            'paid_at': record.paid_at or timezone.now(),
            'stripe_session_id': session_id,
            'stripe_payment_intent_id': payment_intent_id,
        }
    )

    update_fields = []
    if not created and payment.user_id != record.farmer_id:
        payment.user = record.farmer
        update_fields.append('user')
    if payment.payment_type != 'irrigation':
        payment.payment_type = 'irrigation'
        update_fields.append('payment_type')
    if payment.amount != paid_amount:
        payment.amount = paid_amount
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != 'completed':
        payment.status = 'completed'
        update_fields.append('status')
    target_provider = 'paymongo' if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE else 'manual'
    if payment.payment_provider != target_provider:
        payment.payment_provider = target_provider
        update_fields.append('payment_provider')
    if payment.paid_at != (record.paid_at or payment.paid_at):
        payment.paid_at = record.paid_at or payment.paid_at or timezone.now()
        update_fields.append('paid_at')

    if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE:
        if payment.stripe_session_id != session_id:
            payment.stripe_session_id = session_id
            update_fields.append('stripe_session_id')
        if payment.stripe_payment_intent_id != payment_intent_id:
            payment.stripe_payment_intent_id = payment_intent_id
            update_fields.append('stripe_payment_intent_id')
    else:
        if payment.stripe_session_id is not None:
            payment.stripe_session_id = None
            update_fields.append('stripe_session_id')
        if payment.stripe_payment_intent_id is not None:
            payment.stripe_payment_intent_id = None
            update_fields.append('stripe_payment_intent_id')
        if payment.stripe_charge_id is not None:
            payment.stripe_charge_id = None
            update_fields.append('stripe_charge_id')

    if update_fields:
        payment.save(update_fields=update_fields)

    record.season.sync_status()

    return payment


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
    records = list(IrrigationSeasonRecord.objects.filter(
        farmer=request.user
    ).select_related('season', 'sector').order_by('-season__planting_date', '-created_at'))

    for record in records:
        _normalize_irrigation_record_status(record)
        record.payment_record = _get_irrigation_payment(record)

    active_records = [
        record for record in records
        if record.season.status != CroppingSeason.STATUS_CLOSED
        and record.status != IrrigationSeasonRecord.STATUS_CLOSED
    ]
    closed_records = [
        record for record in records
        if record.season.status == CroppingSeason.STATUS_CLOSED
        or record.status == IrrigationSeasonRecord.STATUS_CLOSED
    ]

    total_due = sum((record.total_fee for record in records), start=Decimal('0.00'))
    total_paid = sum((record.amount_paid for record in records), start=Decimal('0.00'))
    total_remaining = sum((record.balance_due for record in records), start=Decimal('0.00'))
    billed_records_count = sum(1 for record in records if (record.total_fee or 0) > 0)

    return render(request, 'irrigation/request_list.html', {
        'records': records,
        'active_records': active_records,
        'closed_records': closed_records,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'billed_records_count': billed_records_count,
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
    record = _normalize_irrigation_record_status(record)
    payment_record = _get_irrigation_payment(record)
    can_choose_payment_method = _can_choose_irrigation_payment_method(record) and not (
        payment_record and payment_record.status == 'completed'
    )
    can_launch_online_payment = (
        _can_choose_irrigation_payment_method(record)
        and record.payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        and not (payment_record and payment_record.status == 'completed')
    )
    waiting_for_online_confirmation = (
        record.payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        and payment_record
        and payment_record.status == 'completed'
        and record.status == IrrigationSeasonRecord.STATUS_HARVESTED
    )
    show_payment_section = (
        (record.total_fee or 0) > 0
        and record.status in [
            IrrigationSeasonRecord.STATUS_HARVESTED,
            IrrigationSeasonRecord.STATUS_PAID,
            IrrigationSeasonRecord.STATUS_CLOSED,
        ]
    )
    return render(request, 'irrigation/request_detail.html', {
        'record': record,
        'payment_record': payment_record,
        'show_payment_section': show_payment_section,
        'can_choose_payment_method': can_choose_payment_method,
        'can_launch_online_payment': can_launch_online_payment,
        'waiting_for_online_confirmation': waiting_for_online_confirmation,
    })


@login_required
def select_irrigation_payment_method(request, pk):
    record = get_object_or_404(
        IrrigationSeasonRecord.objects.select_related('season'),
        pk=pk,
        farmer=request.user,
    )
    _normalize_irrigation_record_status(record)

    next_url = request.POST.get('next') or request.GET.get('next')
    redirect_target = reverse('irrigation:irrigation_request_detail', kwargs={'pk': record.pk})
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        redirect_target = next_url

    if request.method != 'POST':
        return redirect(redirect_target)

    if not _can_choose_irrigation_payment_method(record):
        messages.info(request, 'Payment method can only be selected after irrigation billing is generated and while the balance is still unpaid.')
        return redirect(redirect_target)

    payment_record = _get_irrigation_payment(record)
    if payment_record and payment_record.status == 'completed':
        messages.info(request, 'Your Gcash payment is already on file and is waiting for staff confirmation.')
        return redirect(redirect_target)

    payment_method = request.POST.get('payment_method')
    if payment_method not in [
        IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
        IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
    ]:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect(redirect_target)

    record.payment_method = payment_method
    record.save(update_fields=['payment_method', 'updated_at'])
    _sync_irrigation_payment_record(record, payment_method)
    messages.success(
        request,
        'Gcash payment selected. You can now proceed to payment.'
        if payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        else 'Over-the-counter payment selected. Please pay at the BUFIA office so staff can confirm the transaction.'
    )
    return redirect(redirect_target)


@login_required
def irrigation_receipt(request, pk):
    _sync_irrigation_seasons()
    record = get_object_or_404(
        IrrigationSeasonRecord.objects.select_related('season', 'sector', 'farmer', 'payment_confirmed_by'),
        pk=pk,
    )

    if record.farmer != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('irrigation:irrigation_request_list')

    if (record.amount_paid or 0) <= 0 and record.status not in [
        IrrigationSeasonRecord.STATUS_PAID,
        IrrigationSeasonRecord.STATUS_CLOSED,
    ]:
        messages.info(request, 'Irrigation receipt becomes available after payment is confirmed.')
        return redirect('irrigation:irrigation_request_detail', pk=record.pk)

    next_url = request.GET.get('next')
    if record.farmer == request.user:
        back_url = reverse('my_receipts')
        back_label = 'Back to My Receipts'
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            back_url = next_url
            if next_url == reverse('irrigation:irrigation_request_list'):
                back_label = 'Back to Water Irrigation'
            elif next_url == reverse('irrigation:irrigation_request_detail', kwargs={'pk': record.pk}):
                back_label = 'Back to Record'
            else:
                back_label = 'Back'
    else:
        back_url = reverse('irrigation:admin_irrigation_request_detail', kwargs={'pk': record.season.pk})
        back_label = 'Back to Season'

    return render(request, 'irrigation/receipt.html', {
        'record': record,
        'payment_record': _get_irrigation_payment(record),
        'transaction_id': record.get_transaction_id(),
        'back_url': back_url,
        'back_label': back_label,
    })


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
        season__billing_generated_at__isnull=False,
        status=IrrigationSeasonRecord.STATUS_HARVESTED,
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
    if season.status == CroppingSeason.STATUS_CLOSED:
        messages.info(request, 'Closed seasons are locked for editing. You can still open the printable season report.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)
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
        record.payment_record = _get_irrigation_payment(record)
    season_outstanding_amount = season.total_billed_amount - season.total_paid_amount
    can_assign_farmers = season.status in [CroppingSeason.STATUS_PLANNED, CroppingSeason.STATUS_ACTIVE] and not season.billing_generated_at
    can_generate_billing = (
        season.status != CroppingSeason.STATUS_CLOSED
        and not season.billing_generated_at
        and season.is_harvest_due
        and records.exists()
    )
    can_close_season = season.status == CroppingSeason.STATUS_PAID or not records.exists()
    can_edit_season = season.status != CroppingSeason.STATUS_CLOSED
    can_edit_records = season.status != CroppingSeason.STATUS_CLOSED
    assignment_sector = request.GET.get('sector')
    assignment_form = (
        IrrigationSeasonAssignmentForm(season=season, selected_sector=assignment_sector)
        if can_assign_farmers else None
    )
    show_report = request.GET.get('report') == '1'

    return render(request, 'irrigation/admin_request_detail.html', {
        'season': season,
        'assignment_form': assignment_form,
        'records': records,
        'season_outstanding_amount': season_outstanding_amount,
        'can_assign_farmers': can_assign_farmers,
        'can_generate_billing': can_generate_billing,
        'can_close_season': can_close_season,
        'can_edit_season': can_edit_season,
        'can_edit_records': can_edit_records,
        'show_report': show_report,
    })


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_assign_farmers(request, pk):
    season = get_object_or_404(CroppingSeason, pk=pk)
    assignment_sector = request.POST.get('sector')
    redirect_target = reverse('irrigation:admin_irrigation_request_detail', args=[season.pk])
    if assignment_sector:
        redirect_target = f'{redirect_target}?sector={assignment_sector}#assign-farmers'
    else:
        redirect_target = f'{redirect_target}#assign-farmers'
    if request.method != 'POST':
        return redirect(redirect_target)
    if season.status not in [CroppingSeason.STATUS_PLANNED, CroppingSeason.STATUS_ACTIVE] or season.billing_generated_at:
        messages.error(request, 'Farmers can only be assigned before irrigation billing has been generated.')
        return redirect(redirect_target)

    form = IrrigationSeasonAssignmentForm(request.POST, season=season)
    if not form.is_valid():
        error_message = ' '.join(
            error
            for errors in form.errors.values()
            for error in errors
        ) or 'Please choose a sector and at least one farmer to assign.'
        messages.error(request, error_message)
        return redirect(redirect_target)

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
    return redirect(redirect_target)


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
            billed_timestamp = season.billing_generated_at or timezone.now()
            for billed_record in season.records.select_related('farmer'):
                if (billed_record.total_fee or 0) <= 0:
                    continue
                log_activity(
                    activity_type='billing',
                    actor=request.user,
                    subject_user=billed_record.farmer,
                    title=f'Irrigation billing generated for {billed_record.farmer.get_full_name() or billed_record.farmer.username}',
                    description=f'{season.name}: PHP {billed_record.total_fee} billed for {billed_record.farm_area} ha.',
                    related_object=billed_record,
                    created_at=billed_record.billed_at or billed_timestamp,
                )
            messages.success(request, 'Harvest date reached. Irrigation billing was generated automatically based on farm area.')
    return redirect('irrigation:admin_irrigation_request_detail', pk=season.pk)


@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_confirm_payment(request, pk):
    record = get_object_or_404(IrrigationSeasonRecord.objects.select_related('season'), pk=pk)
    _normalize_irrigation_record_status(record)
    payment = _get_irrigation_payment(record)
    if request.method != 'POST':
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if not _can_confirm_irrigation_payment(record):
        messages.error(
            request,
            f'Cash payment can only be confirmed after irrigation billing is generated on or after the harvest date ({record.season.harvest_date:%b %d, %Y}).'
        )
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if (record.total_fee or 0) <= 0 or record.balance_due <= 0:
        messages.error(request, 'This irrigation record has no remaining billed balance to confirm.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    requested_payment_method = (request.POST.get('payment_method') or '').strip()
    if (
        not record.payment_method
        and requested_payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
    ):
        record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
        record.save(update_fields=['payment_method', 'updated_at'])
        _sync_irrigation_payment_record(
            record,
            IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
        )
        payment = _get_irrigation_payment(record)

    if record.payment_method not in [
        IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
        IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
    ]:
        messages.error(request, 'Payment method has not been selected yet.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if record.payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE:
        if not payment or payment.status != 'completed':
            messages.error(request, 'Gcash payment has not been completed yet.')
            return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

        record.mark_paid(
            confirmed_by=request.user,
            amount=payment.amount or record.total_fee,
            payment_method=IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
        )
        _finalize_irrigation_payment_record(
            record,
            IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
            session_id=payment.stripe_session_id,
            payment_intent_id=payment.stripe_payment_intent_id,
        )
        log_activity(
            activity_type='payment',
            actor=request.user,
            subject_user=record.farmer,
            title=f'Online irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}',
            description=f'{record.season.name}: PHP {record.amount_paid} confirmed.',
            related_object=record,
            created_at=record.paid_at,
        )
        messages.success(request, f'Online irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    form = IrrigationPaymentConfirmationForm(request.POST, instance=record)
    if form.is_valid():
        payment_amount = form.cleaned_data['amount_paid']
        record.refresh_from_db(fields=['amount_paid', 'payment_method', 'status', 'paid_at', 'payment_confirmed_by'])
        record.record_payment(
            confirmed_by=request.user,
            amount=payment_amount,
            payment_method=IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
        )
        _append_irrigation_record_note(record, form.cleaned_data.get('notes'))
        if record.balance_due > 0:
            _sync_irrigation_payment_record(
                record,
                IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
            )
        else:
            _finalize_irrigation_payment_record(
                record,
                IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
            )
        log_activity(
            activity_type='payment',
            actor=request.user,
            subject_user=record.farmer,
            title=(
                f'Partial over-the-counter irrigation payment recorded for {record.farmer.get_full_name() or record.farmer.username}'
                if record.balance_due > 0
                else f'Over-the-counter irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}'
            ),
            description=(
                f'{record.season.name}: PHP {payment_amount} received, PHP {record.balance_due} remaining.'
                if record.balance_due > 0
                else f'{record.season.name}: PHP {record.amount_paid} confirmed.'
            ),
            related_object=record,
            created_at=record.paid_at,
        )
        if record.balance_due > 0:
            messages.success(
                request,
                f'Partial cash payment recorded for {record.farmer.get_full_name() or record.farmer.username}. Remaining balance: PHP {record.balance_due:.2f}.'
            )
        else:
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
    record = _normalize_irrigation_record_status(record)
    if record.season.status == CroppingSeason.STATUS_CLOSED or record.status == IrrigationSeasonRecord.STATUS_CLOSED:
        messages.info(request, 'Closed seasons are locked for editing. You can still print the season report.')
        return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_record':
            messages.info(request, 'Record details are view-only on this page.')
            return redirect('irrigation:admin_irrigation_record_edit', pk=record.pk)
        elif action == 'confirm_payment':
            record_form = IrrigationSeasonRecordAdminForm(instance=record)
            payment_form = IrrigationPaymentConfirmationForm(request.POST, instance=record)
            payment_record = _get_irrigation_payment(record)
            can_confirm_harvest_payment = _can_confirm_irrigation_payment(record)
            can_record_walk_in_payment = _can_record_irrigation_walk_in_payment(record)

            if not can_confirm_harvest_payment and not can_record_walk_in_payment:
                messages.error(request, 'This irrigation record cannot accept another payment right now.')
            elif (
                can_confirm_harvest_payment
                and record.payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
                and payment_record
                and payment_record.status == 'completed'
            ):
                record.mark_paid(
                    confirmed_by=request.user,
                    amount=payment_record.amount or record.total_fee,
                    payment_method=IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
                )
                _finalize_irrigation_payment_record(
                    record,
                    IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE,
                    session_id=payment_record.stripe_session_id,
                    payment_intent_id=payment_record.stripe_payment_intent_id,
                )
                log_activity(
                    activity_type='payment',
                    actor=request.user,
                    subject_user=record.farmer,
                    title=f'Gcash irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}',
                    description=f'{record.season.name}: PHP {record.amount_paid} confirmed.',
                    related_object=record,
                    created_at=record.paid_at,
                )
                messages.success(
                    request,
                    f'Gcash irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}.'
                )
                return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)
            elif payment_form.is_valid() and can_record_walk_in_payment:
                payment_label = (
                    'Advance payment note'
                    if not can_confirm_harvest_payment
                    else 'Payment note'
                )
                payment_amount = payment_form.cleaned_data['amount_paid']
                record.refresh_from_db(fields=['amount_paid', 'payment_method', 'status', 'paid_at', 'payment_confirmed_by'])
                record.record_payment(
                    confirmed_by=request.user,
                    amount=payment_amount,
                    payment_method=IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
                )
                _append_irrigation_record_note(
                    record,
                    payment_form.cleaned_data.get('notes'),
                    label=payment_label,
                )
                if record.balance_due > 0:
                    _sync_irrigation_payment_record(
                        record,
                        IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
                    )
                else:
                    _finalize_irrigation_payment_record(
                        record,
                        IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
                    )
                log_activity(
                    activity_type='payment',
                    actor=request.user,
                    subject_user=record.farmer,
                    title=(
                        f'Walk-in irrigation advance payment recorded for {record.farmer.get_full_name() or record.farmer.username}'
                        if not can_confirm_harvest_payment
                        else (
                            f'Partial over-the-counter irrigation payment recorded for {record.farmer.get_full_name() or record.farmer.username}'
                            if record.balance_due > 0
                            else f'Over-the-counter irrigation payment confirmed for {record.farmer.get_full_name() or record.farmer.username}'
                        )
                    ),
                    description=(
                        f'{record.season.name}: PHP {payment_amount} received, PHP {record.balance_due} remaining.'
                        if record.balance_due > 0
                        else f'{record.season.name}: PHP {record.amount_paid} settled.'
                    ),
                    related_object=record,
                    created_at=record.paid_at,
                )
                messages.success(
                    request,
                    (
                        f'Walk-in advance payment recorded for {record.farmer.get_full_name() or record.farmer.username}. Remaining balance: PHP {record.balance_due:.2f}.'
                        if not can_confirm_harvest_payment
                        else (
                            f'Partial cash payment recorded for {record.farmer.get_full_name() or record.farmer.username}. Remaining balance: PHP {record.balance_due:.2f}.'
                            if record.balance_due > 0
                            else f'Cash payment confirmed for {record.farmer.get_full_name() or record.farmer.username}.'
                        )
                    )
                )
                return redirect('irrigation:admin_irrigation_request_detail', pk=record.season.pk)
            else:
                messages.error(request, 'Unable to confirm payment. Please check the payment amount.')
        else:
            record_form = IrrigationSeasonRecordAdminForm(instance=record)
            payment_form = IrrigationPaymentConfirmationForm(instance=record)
            messages.info(
                request,
                'Choose an irrigation record action to continue.'
            )
    else:
        record_form = IrrigationSeasonRecordAdminForm(instance=record)
        payment_form = IrrigationPaymentConfirmationForm(instance=record)

    payment_record = _get_irrigation_payment(record)
    can_mark_paid = _can_confirm_irrigation_payment(record)
    can_record_walk_in_payment = _can_record_irrigation_walk_in_payment(record)
    has_completed_online_payment = bool(
        payment_record
        and payment_record.status == 'completed'
        and record.payment_method == IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
    )

    return render(request, 'irrigation/admin_record_edit.html', {
        'record': record,
        'record_form': record_form,
        'payment_form': payment_form,
        'payment_record': payment_record,
        'can_mark_paid': can_mark_paid,
        'can_record_walk_in_payment': can_record_walk_in_payment,
        'has_completed_online_payment': has_completed_online_payment,
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
def user_irrigation_request_history(request):
    _sync_irrigation_seasons()
    records = list(IrrigationSeasonRecord.objects.filter(farmer=request.user).select_related(
        'season', 'sector', 'payment_confirmed_by'
    ).order_by('-season__planting_date'))
    for record in records:
        _normalize_irrigation_record_status(record)
    return render(request, 'irrigation/user_request_history.html', {'records': records})
