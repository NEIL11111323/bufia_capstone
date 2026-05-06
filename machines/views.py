from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Exists, OuterRef, Prefetch, Case, When, IntegerField, F
from django.db import IntegrityError, transaction
from .models import (
    Machine,
    Rental,
    Maintenance,
    PriceHistory,
    MachineImage,
    RiceMillAppointment,
    DryerRental,
    RentalPackage,
    RentalPackageItem,
)
from .forms import (MachineForm, MachineImageForm, MachineImageFormSet, RentalForm, 
                   MaintenanceForm, MaintenanceCompletionForm, MaintenancePartFormSet,
                   PriceHistoryForm, RiceMillAppointmentForm, DryerRentalForm,
                   DryerRentalApprovalForm, AdminRentalForm, RentalPackageRequestForm,
                   RentalPackageItemScheduleFormSet)
import json
from django.utils.safestring import mark_safe
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import HttpResponse, HttpResponseForbidden, Http404, JsonResponse, HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
import os
from django.conf import settings
from django.utils.text import slugify
from notifications.models import UserNotification
from notifications.notification_helpers import create_notification as create_system_notification
from django.contrib.auth import get_user_model
from users.decorators import verified_member_required
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch
from django.contrib.auth import get_user_model

User = get_user_model()

# Simple notification function (temporary)
def create_notification(user, title, message, category, reference_object=None):
    """Create a user notification - temporary implementation until proper notification system is integrated"""
    # Log the notification details for debugging
    print(f"NOTIFICATION - User: {user}, Title: {title}, Message: {message}")
    # In a real implementation, this would save to a notifications model
    # For now, we'll just use Django messages
    return True


RICE_MILL_LOCKED_STATUSES = ['approved', 'paid', 'confirmed', 'ongoing']
DRYER_LOCKED_STATUSES = ['approved', 'in_progress', 'paid', 'confirmed', 'ongoing']
DRYER_VISIBLE_STATUSES = ['pending', 'waiting_confirmation', 'approved', 'in_progress', 'paid', 'confirmed', 'ongoing']
ACTIVE_MAINTENANCE_STATUSES = ['scheduled', 'in_progress']


def _maintenance_management_access(user):
    return bool(user and (user.is_staff or user.is_superuser))


def _package_management_access(user):
    return bool(user and (user.is_staff or user.is_superuser))


def _package_request_access(user):
    return bool(
        user and (
            getattr(user, 'is_verified', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'is_superuser', False)
            or user.has_perm('machines.can_rent_machine')
        )
    )


def _package_notification_action_url(package):
    return reverse('machines:rental_package_detail', kwargs={'pk': package.pk})


def _package_notification_title(package, label):
    return f'{label} - {package.package_name}'


def _package_notification_message(package, prefix):
    service_count = package.included_items_count
    return (
        f'{prefix} {package.package_name} for {package.farmer_name}. '
        f'Preferred start: {package.preferred_start_date.strftime("%B %d, %Y")}. '
        f'Services: {service_count}.'
    )


def _create_package_notification(user, package, notification_type, message, *, title=None, priority='important'):
    return create_system_notification(
        user=user,
        notification_type=notification_type,
        title=title or _package_notification_title(package, 'Rental Package Update'),
        message=message,
        category='rental',
        priority=priority,
        related_object_id=package.id,
        action_url=_package_notification_action_url(package),
    )


def _notify_package_request_submitted(package):
    _create_package_notification(
        package.user,
        package,
        'rental_package_submitted',
        _package_notification_message(package, 'Your rental package request was submitted.'),
        title=_package_notification_title(package, 'Package Request Submitted'),
    )

    admins = User.objects.filter(is_staff=True, is_active=True).exclude(role='operator')
    for admin in admins:
        _create_package_notification(
            admin,
            package,
            'rental_package_new_request',
            _package_notification_message(package, 'New rental package request received.'),
            title=_package_notification_title(package, 'New Package Request'),
        )


def _notify_package_request_approved(package):
    _create_package_notification(
        package.user,
        package,
        'rental_package_approved',
        _package_notification_message(package, 'Your rental package request was approved and scheduled services are now active.'),
        title=_package_notification_title(package, 'Package Request Approved'),
    )


def _notify_package_request_rejected(package):
    _create_package_notification(
        package.user,
        package,
        'rental_package_rejected',
        _package_notification_message(package, 'Your rental package request was rejected by BUFIA.'),
        title=_package_notification_title(package, 'Package Request Rejected'),
    )


def _notify_package_request_cancelled(package, *, notify_admins=False):
    _create_package_notification(
        package.user,
        package,
        'rental_package_cancelled',
        _package_notification_message(package, 'Your rental package request was cancelled.'),
        title=_package_notification_title(package, 'Package Request Cancelled'),
        priority='normal',
    )

    if notify_admins:
        admins = User.objects.filter(is_staff=True, is_active=True).exclude(role='operator')
        for admin in admins:
            _create_package_notification(
                admin,
                package,
                'rental_package_cancelled',
                _package_notification_message(package, 'A rental package request was cancelled by the requester.'),
                title=_package_notification_title(package, 'Package Request Cancelled'),
                priority='normal',
            )


def _equipment_rentals_url_for_user(user):
    if user and (user.is_staff or user.is_superuser):
        return reverse('machines:admin_rental_dashboard')
    return reverse('machines:rental_list')


def _machine_rental_queryset():
    return Machine.objects.exclude(machine_type__in=['rice_mill', *Machine.DRYER_MACHINE_TYPES])


def _active_maintenance_records_queryset():
    return Maintenance.objects.filter(
        status__in=ACTIVE_MAINTENANCE_STATUSES
    ).annotate(
        status_priority=Case(
            When(status='in_progress', then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by('status_priority', '-start_date', '-pk')


def _sync_machine_maintenance_status(machine):
    if not machine:
        return
    machine.sync_status()


def _get_uploaded_image_payloads(request):
    """Collect new image uploads submitted outside the inline formset."""
    uploaded_files = request.FILES.getlist('uploaded_images')
    payloads = []

    for index, uploaded_file in enumerate(uploaded_files):
        caption = (request.POST.get(f'new-image-{index}-caption') or '').strip()
        is_primary = request.POST.get(f'new-image-{index}-is_primary') in {'1', 'true', 'on'}
        payloads.append({
            'image': uploaded_file,
            'caption': caption,
            'is_primary': is_primary,
        })

    return payloads


def _count_active_formset_images(formset):
    """Count active image rows represented in a validated formset."""
    total = 0
    for image_form in formset.forms:
        if not hasattr(image_form, 'cleaned_data'):
            continue
        cleaned_data = image_form.cleaned_data
        if not cleaned_data or cleaned_data.get('DELETE'):
            continue
        if image_form.instance.pk or cleaned_data.get('image'):
            total += 1
    return total


def _save_machine_image_formset(formset, machine, uploaded_image_payloads=None):
    """Persist machine gallery changes after the parent machine has been saved."""
    formset.instance = machine
    image_instances = formset.save(commit=False)

    for image in image_instances:
        if image is None:
            continue
        image.machine = machine
        image.save()

    for obj in formset.deleted_objects:
        obj.delete()

    for payload in uploaded_image_payloads or []:
        MachineImage.objects.create(
            machine=machine,
            image=payload['image'],
            caption=payload['caption'],
            is_primary=payload['is_primary'],
        )

    images = machine.images.all()
    if images.exists() and not images.filter(is_primary=True).exists():
        first_image = images.first()
        first_image.is_primary = True
        first_image.save(update_fields=['is_primary'])


def _get_current_maintenance_record(machine, maintenance_records=None):
    records = list(
        maintenance_records
        if maintenance_records is not None
        else machine.maintenance_records.all().order_by('-start_date')
    )

    active_record = next(
        (record for record in records if record.status in ACTIVE_MAINTENANCE_STATUSES),
        None,
    )
    if active_record:
        return active_record

    if machine.status == 'maintenance' and records:
        return records[0]

    return None


def _get_maintenance_issue_text(record):
    if not record:
        return 'BUFIA has marked this machine as under maintenance. Issue details will be posted soon.'

    return (
        (record.description or '').strip()
        or 'BUFIA has marked this machine as under maintenance. Issue details will be posted soon.'
    )


def _dryer_queryset():
    return Machine.objects.filter(machine_type__in=Machine.DRYER_MACHINE_TYPES).order_by('name', 'pk')


def _ensure_default_dryer():
    return _dryer_queryset().first()


def _dryer_requestable(machine):
    return bool(machine and machine.status == 'available')


def _format_sack_value(value):
    if value is None:
        return '0'
    value = Decimal(str(value)).quantize(Decimal('0.01'))
    formatted = f"{value:,.2f}"
    if formatted.endswith('.00'):
        return formatted[:-3]
    if formatted.endswith('0'):
        return formatted[:-1]
    return formatted


def _format_estimated_service_schedule(dryer_rental):
    service_end_date = dryer_rental.estimated_service_end_date
    if not service_end_date:
        return 'Not scheduled'

    schedule_label = service_end_date.strftime('%B %d, %Y')
    service_end_time = dryer_rental.estimated_service_end_time
    if service_end_time:
        schedule_label = f"{schedule_label} at {service_end_time.strftime('%I:%M %p').lstrip('0')}"
    return schedule_label


def _combine_dryer_local_datetime(target_date, target_time=None, *, end_of_day=False):
    if not target_date:
        return None
    if target_time is None:
        target_time = time(23, 59) if end_of_day else time(0, 0)
    return timezone.make_aware(
        datetime.combine(target_date, target_time),
        timezone.get_current_timezone(),
    )


def _format_dryer_datetime_label(value, fallback='—'):
    if not value:
        return fallback
    local_value = timezone.localtime(value)
    if local_value.time() in {time(0, 0), time(23, 59)}:
        return local_value.strftime('%b %d, %Y')
    return local_value.strftime('%b %d, %I:%M %p').replace(' 0', ' ')


def _dryer_rental_start_datetime(dryer_rental):
    if dryer_rental.is_hourly_pricing and dryer_rental.start_time:
        return _combine_dryer_local_datetime(dryer_rental.rental_date, dryer_rental.start_time)
    if (
        dryer_rental.status in DRYER_LOCKED_STATUSES
        and timezone.localtime(dryer_rental.updated_at).date() == dryer_rental.rental_date
    ):
        return timezone.localtime(dryer_rental.updated_at)
    return _combine_dryer_local_datetime(dryer_rental.rental_date)


def _dryer_rental_end_datetime(dryer_rental):
    if dryer_rental.estimated_service_end_time and dryer_rental.estimated_service_end_date:
        return _combine_dryer_local_datetime(
            dryer_rental.estimated_service_end_date,
            dryer_rental.estimated_service_end_time,
        )
    if dryer_rental.is_hourly_pricing and dryer_rental.end_time:
        return _combine_dryer_local_datetime(dryer_rental.rental_date, dryer_rental.end_time)
    if dryer_rental.estimated_service_end_date:
        return _combine_dryer_local_datetime(
            dryer_rental.estimated_service_end_date,
            end_of_day=True,
        )
    return None


def _build_dryer_availability_activity_item(rental, *, current_pk=None, next_locked_pk=None):
    start_at = _dryer_rental_start_datetime(rental)
    end_at = _dryer_rental_end_datetime(rental)
    schedule_parts = [_format_dryer_datetime_label(start_at)]
    if end_at:
        schedule_parts.append(_format_dryer_datetime_label(end_at, fallback='To be confirmed'))

    if current_pk and rental.pk == current_pk:
        stage_label = 'Current'
    elif next_locked_pk and rental.pk == next_locked_pk:
        stage_label = 'Next Scheduled'
    elif rental.status in DRYER_LOCKED_STATUSES:
        stage_label = 'Scheduled'
    else:
        stage_label = 'For Review'

    return {
        'reference': rental.reference_number or f'Dryer #{rental.pk}',
        'renter': rental.customer_display_name,
        'status_label': rental.get_status_display(),
        'status_class': rental.status or 'default',
        'stage_label': stage_label,
        'pricing_label': rental.pricing_type_label,
        'schedule_label': ' to '.join(schedule_parts),
        'sacks_label': f"{_format_sack_value(rental.quantity_in_sacks or Decimal('0.00'))} sacks",
    }


def _build_dryer_availability_rows(dryers):
    now = timezone.localtime()
    rows = []

    for dryer in dryers:
        visible_rentals = list(
            DryerRental.objects.filter(
                machine=dryer,
                status__in=DRYER_VISIBLE_STATUSES,
            ).select_related('user', 'machine').order_by('rental_date', 'start_time', 'created_at', 'pk')
        )
        locked_rentals = list(
            rental for rental in visible_rentals if rental.status in DRYER_LOCKED_STATUSES
        )

        current_rental = None
        next_rental = None
        for rental in locked_rentals:
            start_at = _dryer_rental_start_datetime(rental)
            end_at = _dryer_rental_end_datetime(rental)
            if start_at and start_at <= now and (end_at is None or end_at >= now):
                current_rental = rental
                break
            if start_at and start_at > now and next_rental is None:
                next_rental = rental

        current_sacks = current_rental.quantity_in_sacks if current_rental else Decimal('0.00')
        freed_sacks_label = f"{_format_sack_value(current_sacks)} sacks"
        used_capacity = DryerRental.used_dryer_capacity_for_date(dryer, timezone.localdate())
        total_capacity = dryer.get_dryer_capacity_limit_sacks()
        remaining_capacity = max(total_capacity - used_capacity, Decimal('0.00')).quantize(Decimal('0.01'))
        pending_count = sum(1 for rental in visible_rentals if rental.status == 'pending')
        waiting_confirmation_count = sum(
            1 for rental in visible_rentals if rental.status == 'waiting_confirmation'
        )
        activity_items = [
            _build_dryer_availability_activity_item(
                rental,
                current_pk=current_rental.pk if current_rental else None,
                next_locked_pk=next_rental.pk if next_rental else None,
            )
            for rental in visible_rentals
        ]

        if current_rental:
            expected_end_at = _dryer_rental_end_datetime(current_rental)
            sacks_label = freed_sacks_label
            expected_end_label = _format_dryer_datetime_label(expected_end_at, fallback='To be confirmed')
            rows.append({
                'dryer': dryer,
                'current_renter': current_rental.customer_display_name,
                'current_reference': current_rental.reference_number or f'Dryer #{current_rental.pk}',
                'sacks_label': sacks_label,
                'started_label': _format_dryer_datetime_label(_dryer_rental_start_datetime(current_rental)),
                'expected_end_label': expected_end_label,
                'current_pricing_label': current_rental.pricing_type_label,
                'status_label': 'Occupied',
                'status_class': 'occupied',
                'freed_sacks_label': sacks_label,
                'next_renter': next_rental.customer_display_name if next_rental else '—',
                'next_reference': next_rental.reference_number if next_rental and next_rental.reference_number else '—',
                'next_started_label': _format_dryer_datetime_label(_dryer_rental_start_datetime(next_rental)) if next_rental else '—',
                'next_expected_end_label': _format_dryer_datetime_label(_dryer_rental_end_datetime(next_rental), fallback='To be confirmed') if next_rental else '—',
                'next_sacks_label': f"{_format_sack_value(next_rental.quantity_in_sacks or Decimal('0.00'))} sacks" if next_rental else '0 sacks',
                'total_capacity_label': f"{_format_sack_value(total_capacity)} sacks",
                'used_capacity_label': f"{_format_sack_value(used_capacity)} sacks",
                'remaining_capacity_label': f"{_format_sack_value(remaining_capacity)} sacks",
                'pricing_display': dryer.get_rate_display(),
                'pricing_setup_display': dryer.get_dryer_pricing_type_display(),
                'visible_rental_count': len(visible_rentals),
                'locked_rental_count': len(locked_rentals),
                'pending_count': pending_count,
                'waiting_confirmation_count': waiting_confirmation_count,
                'activity_items': activity_items,
                'availability_message': (
                    f'{dryer.name} is currently occupied with {sacks_label} and will be available on {expected_end_label}.'
                ),
            })
            continue

        if next_rental:
            next_start_label = _format_dryer_datetime_label(_dryer_rental_start_datetime(next_rental))
            rows.append({
                'dryer': dryer,
                'current_renter': '—',
                'current_reference': '—',
                'sacks_label': '0 sacks',
                'started_label': '—',
                'expected_end_label': '—',
                'current_pricing_label': '—',
                'status_label': 'Available Soon',
                'status_class': 'soon',
                'freed_sacks_label': '0 sacks',
                'next_renter': next_rental.customer_display_name,
                'next_reference': next_rental.reference_number or f'Dryer #{next_rental.pk}',
                'next_started_label': next_start_label,
                'next_expected_end_label': _format_dryer_datetime_label(_dryer_rental_end_datetime(next_rental), fallback='To be confirmed'),
                'next_sacks_label': f"{_format_sack_value(next_rental.quantity_in_sacks or Decimal('0.00'))} sacks",
                'total_capacity_label': f"{_format_sack_value(total_capacity)} sacks",
                'used_capacity_label': f"{_format_sack_value(used_capacity)} sacks",
                'remaining_capacity_label': f"{_format_sack_value(remaining_capacity)} sacks",
                'pricing_display': dryer.get_rate_display(),
                'pricing_setup_display': dryer.get_dryer_pricing_type_display(),
                'visible_rental_count': len(visible_rentals),
                'locked_rental_count': len(locked_rentals),
                'pending_count': pending_count,
                'waiting_confirmation_count': waiting_confirmation_count,
                'activity_items': activity_items,
                'availability_message': f'{dryer.name} is available now. The next scheduled dryer service starts on {next_start_label}.',
            })
            continue

        rows.append({
            'dryer': dryer,
            'current_renter': '—',
            'current_reference': '—',
            'sacks_label': '0 sacks',
            'started_label': '—',
            'expected_end_label': '—',
            'current_pricing_label': '—',
            'status_label': 'Available',
            'status_class': 'available',
            'freed_sacks_label': '0 sacks',
            'next_renter': '—',
            'next_reference': '—',
            'next_started_label': '—',
            'next_expected_end_label': '—',
            'next_sacks_label': '0 sacks',
            'total_capacity_label': f"{_format_sack_value(total_capacity)} sacks",
            'used_capacity_label': f"{_format_sack_value(used_capacity)} sacks",
            'remaining_capacity_label': f"{_format_sack_value(remaining_capacity)} sacks",
            'pricing_display': dryer.get_rate_display(),
            'pricing_setup_display': dryer.get_dryer_pricing_type_display(),
            'visible_rental_count': len(visible_rentals),
            'locked_rental_count': len(locked_rentals),
            'pending_count': pending_count,
            'waiting_confirmation_count': waiting_confirmation_count,
            'activity_items': activity_items,
            'availability_message': f'{dryer.name} is currently available.',
        })

    return rows


def _is_dryer_setup_flow(request, machine=None):
    selected_machine_type = request.GET.get('machine_type') or request.POST.get('machine_type')
    return bool(
        (machine and machine.is_dryer_service())
        or request.GET.get('service') == 'dryer'
        or request.POST.get('service') == 'dryer'
        or selected_machine_type in Machine.DRYER_MACHINE_TYPES
    )


def _is_rice_mill_machine_form(request, machine=None):
    selected_machine_type = request.GET.get('machine_type') or request.POST.get('machine_type')
    return bool(
        (machine and machine.machine_type == 'rice_mill')
        or selected_machine_type == 'rice_mill'
    )


def _get_dryer_setup_defaults(machine_type):
    machine_type = machine_type if machine_type in Machine.DRYER_MACHINE_TYPES else 'flatbed_dryer'
    labels = dict(Machine.DRYER_MACHINE_TYPE_CHOICES)
    default_pricing_map = {
        'flatbed_dryer': 'hourly',
        'circulating_dryer': 'hourly',
        'solar_dryer': 'per_sack',
    }
    guidance_map = {
        'flatbed_dryer': 'Best for scheduled dryer sessions with a configured hourly rate.',
        'circulating_dryer': 'Use this when the circulating dryer should be booked like a managed dryer unit with saved pricing.',
        'solar_dryer': 'Solar dryers depend on sunlight, so the recommended default is Per Sack pricing for rice grain drying while the service request still captures sun-drying requirements.',
    }
    return {
        'machine_type': machine_type,
        'label': labels.get(machine_type, 'Dryer Unit'),
        'default_pricing_type': default_pricing_map.get(machine_type, 'hourly'),
        'guidance': guidance_map.get(machine_type, 'Configure the dryer details and saved pricing before assignment.'),
    }


def _build_dryer_calendar_events(machine, exclude_pk=None):
    rentals = DryerRental.objects.filter(
        machine=machine,
        status__in=DRYER_VISIBLE_STATUSES,
    )
    if exclude_pk:
        rentals = rentals.exclude(pk=exclude_pk)

    events = []
    for rental in rentals.select_related('user', 'machine'):
        booked_by = rental.customer_display_name
        service_end_date = rental.estimated_service_end_date
        events.append({
            'title': f"{rental.display_time_range} - {booked_by}",
            'start': rental.rental_date.strftime('%Y-%m-%d'),
            'service_end': service_end_date.strftime('%Y-%m-%d') if service_end_date else rental.rental_date.strftime('%Y-%m-%d'),
            'allDay': True,
            'color': '#f59f00',
            'range_label': rental.display_time_range,
            'start_time': rental.start_time.strftime('%H:%M') if rental.start_time else '',
            'end_time': rental.end_time.strftime('%H:%M') if rental.end_time else '',
            'booked_by': booked_by,
            'status': rental.status,
            'status_label': rental.get_status_display(),
            'pricing_type': rental.rental_type or rental.pricing_type_snapshot,
            'pricing_type_label': rental.pricing_type_label,
            'locked': rental.slot_locked,
            'notes': rental.notes or '',
            'admin_note': rental.admin_note or '',
            'quantity': rental.quantity or '',
            'quantity_sacks': str(rental.quantity_in_sacks or Decimal('0.00')),
            'uses_shared_capacity': rental.uses_shared_capacity,
            'shared_capacity_sacks': str(
                rental.machine.get_dryer_capacity_limit_sacks() if rental.machine_id else Decimal('0.00')
            ),
        })
    return events


def _build_dryer_machine_payload(machine, exclude_pk=None):
    pricing = machine.get_pricing_info()
    return {
        'id': machine.pk,
        'name': machine.name,
        'machine_type': machine.machine_type,
        'type': machine.dryer_service_type or 'flatbed',
        'type_display': machine.get_dryer_service_type_display(),
        'status': machine.status,
        'status_display': machine.get_status_display(),
        'pricing_type': machine.dryer_pricing_type or 'hourly',
        'pricing_type_display': machine.get_dryer_pricing_type_display(),
        'pricing_unit': pricing.get('unit') or '',
        'rate_display': machine.get_rate_display(),
        'is_requestable': _dryer_requestable(machine),
        'hourly_rate': str(machine.get_effective_dryer_hourly_rate()),
        'sack_rate': str(machine.get_effective_dryer_sack_rate()),
        'shared_capacity_sacks': str(machine.get_dryer_capacity_limit_sacks()),
        'events': _build_dryer_calendar_events(machine, exclude_pk=exclude_pk),
    }


def _ensure_default_rice_mill():
    rice_mill = Machine.objects.filter(machine_type='rice_mill').order_by('name', 'pk').first()
    if rice_mill:
        return rice_mill
    return Machine.objects.create(
        name='Rice Mill',
        machine_type='rice_mill',
        description='Default rice mill unit for the dedicated rice mill booking module.',
        status='available',
        rental_fee_per_day=Decimal('3.00'),
        current_price='3/kg',
    )


def _sync_ricemill_appointment_pricing(machine):
    if not machine or machine.machine_type != 'rice_mill':
        return

    for appointment in RiceMillAppointment.objects.filter(machine=machine):
        appointment.save(update_fields=['price_per_kg', 'total_amount', 'updated_at'])


def _member_search_queryset():
    User = get_user_model()
    return User.objects.filter(
        is_active=True,
        is_verified=True,
    ).exclude(username='system')


def _member_search_payload(user):
    membership = getattr(user, 'membership_application', None)
    farm_location = ''
    area = None
    if membership:
        farm_location = membership.bufia_farm_location or membership.farm_location or ''
        area = membership.farm_size

    return {
        'id': user.id,
        'name': user.get_full_name() or user.username,
        'contact_number': user.phone_number or '',
        'address': farm_location or user.address or '',
        'farm_area': str(area) if area is not None else '',
        'username': user.username,
    }


def _get_appointment_payment(appointment):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=appointment.id
    ).first()


def _get_appointment_payment_map(appointments):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    appointment_ids = [appointment.id for appointment in appointments if appointment.id]
    if not appointment_ids:
        return {}

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    payments = Payment.objects.filter(
        content_type=content_type,
        object_id__in=appointment_ids,
    )
    return {payment.object_id: payment for payment in payments}


def _reset_over_counter_payment(payment):
    update_fields = []
    if payment.amount_received is not None:
        payment.amount_received = None
        update_fields.append('amount_received')
    if payment.change_given != Decimal('0.00'):
        payment.change_given = Decimal('0.00')
        update_fields.append('change_given')
    if payment.processed_by_id is not None:
        payment.processed_by = None
        update_fields.append('processed_by')
    if update_fields:
        payment.save(update_fields=update_fields)


def _record_over_counter_payment(payment, *, amount_due, amount_received, processed_by):
    amount_due = Decimal(str(amount_due)).quantize(Decimal('0.01'))
    amount_received = Decimal(str(amount_received)).quantize(Decimal('0.01'))
    change_given = (amount_received - amount_due).quantize(Decimal('0.01'))

    payment.amount = amount_due
    payment.amount_received = amount_received
    payment.change_given = change_given
    payment.processed_by = processed_by
    payment.payment_provider = 'manual'
    payment.status = 'completed'
    payment.paid_at = timezone.now()
    payment.save(update_fields=[
        'amount',
        'amount_received',
        'change_given',
        'processed_by',
        'payment_provider',
        'status',
        'paid_at',
        'updated_at',
    ])

    return payment


def _sync_appointment_face_to_face_payment_record(appointment):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=appointment.id,
        defaults={
            'user': appointment.user,
            'payment_type': 'appointment',
            'amount': appointment.total_amount,
            'currency': 'PHP',
            'status': 'pending',
        }
    )

    update_fields = []
    if not created and payment.user_id != appointment.user_id:
        payment.user = appointment.user
        update_fields.append('user')
    if payment.payment_type != 'appointment':
        payment.payment_type = 'appointment'
        update_fields.append('payment_type')
    if payment.amount != appointment.total_amount:
        payment.amount = appointment.total_amount
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != 'pending':
        payment.status = 'pending'
        update_fields.append('status')
    if payment.payment_provider is not None:
        payment.payment_provider = None
        update_fields.append('payment_provider')
    if payment.paid_at is not None:
        payment.paid_at = None
        update_fields.append('paid_at')
    if payment.amount_received is not None:
        payment.amount_received = None
        update_fields.append('amount_received')
    if payment.change_given != Decimal('0.00'):
        payment.change_given = Decimal('0.00')
        update_fields.append('change_given')
    if payment.processed_by_id is not None:
        payment.processed_by = None
        update_fields.append('processed_by')
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


def _get_dryer_payment(dryer_rental):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(DryerRental)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=dryer_rental.id
    ).first()


def _sync_dryer_payment_record(dryer_rental, payment_method):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(DryerRental)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=dryer_rental.id,
        defaults={
            'user': dryer_rental.user,
            'payment_type': 'dryer',
            'amount': dryer_rental.total_amount,
            'currency': 'PHP',
            'status': 'pending',
        }
    )

    update_fields = []
    if not created and payment.user_id != dryer_rental.user_id:
        payment.user = dryer_rental.user
        update_fields.append('user')
    if payment.payment_type != 'dryer':
        payment.payment_type = 'dryer'
        update_fields.append('payment_type')
    if payment.amount != dryer_rental.total_amount:
        payment.amount = dryer_rental.total_amount
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != 'pending':
        payment.status = 'pending'
        update_fields.append('status')
    if payment.payment_provider is not None:
        payment.payment_provider = None
        update_fields.append('payment_provider')
    if payment.paid_at is not None:
        payment.paid_at = None
        update_fields.append('paid_at')
    if payment.amount_received is not None:
        payment.amount_received = None
        update_fields.append('amount_received')
    if payment.change_given != Decimal('0.00'):
        payment.change_given = Decimal('0.00')
        update_fields.append('change_given')
    if payment.processed_by_id is not None:
        payment.processed_by = None
        update_fields.append('processed_by')
    if payment_method == 'face_to_face':
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


def _ensure_service_payment_record(service_object, payment_type, *, status='pending', paid_at=None):
    """Ensure a payment record exists (with internal transaction ID) for service receipts/workflows."""
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(service_object.__class__)
    amount = getattr(service_object, 'total_amount', Decimal('0.00')) or Decimal('0.00')
    normalized_status = status if status in {'pending', 'completed'} else 'pending'
    target_paid_at = paid_at if normalized_status == 'completed' else None

    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=service_object.id,
        defaults={
            'user': service_object.user,
            'payment_type': payment_type,
            'amount': amount,
            'currency': 'PHP',
            'status': normalized_status,
            'paid_at': target_paid_at,
        }
    )

    if normalized_status == 'completed' and target_paid_at is None:
        target_paid_at = payment.paid_at or timezone.now()

    update_fields = []
    if not created and payment.user_id != service_object.user_id:
        payment.user = service_object.user
        update_fields.append('user')
    if payment.payment_type != payment_type:
        payment.payment_type = payment_type
        update_fields.append('payment_type')
    if payment.amount != amount:
        payment.amount = amount
        update_fields.append('amount')
    if payment.currency != 'PHP':
        payment.currency = 'PHP'
        update_fields.append('currency')
    if payment.status != normalized_status:
        payment.status = normalized_status
        update_fields.append('status')
    if payment.paid_at != target_paid_at:
        payment.paid_at = target_paid_at
        update_fields.append('paid_at')
    if normalized_status != 'completed':
        if payment.amount_received is not None:
            payment.amount_received = None
            update_fields.append('amount_received')
        if payment.change_given != Decimal('0.00'):
            payment.change_given = Decimal('0.00')
            update_fields.append('change_given')
        if payment.processed_by_id is not None:
            payment.processed_by = None
            update_fields.append('processed_by')

    if update_fields:
        payment.save(update_fields=update_fields)

    return payment

@login_required
def machine_list(request):
    machines = _machine_rental_queryset()
    
    # Add pagination
    from django.core.paginator import Paginator
    
    paginator = Paginator(machines, 12)  # 12 machines per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_machines = machines.count()
    available_machines = machines.filter(status='available').count()
    in_use_machines = machines.filter(status='rented').count()
    machine_types = machines.values('machine_type').distinct().count()
    
    # Check user permissions
    context = {
        'machines': page_obj,
        'page_obj': page_obj,
        'total_machines': total_machines,
        'available_machines': available_machines,
        'in_use_machines': in_use_machines,
        'machine_types': machine_types,
    }
    return render(request, 'machines/machine_list.html', context)

@login_required
def machine_detail(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    rentals = machine.rentals.all().order_by('-start_date')
    maintenance_records = machine.maintenance_records.all().order_by('-start_date')
    price_history = machine.price_history.all().order_by('-start_date')
    images = [image for image in machine.images.all() if image.get_image_url()]
    
    # Calculate rental statistics
    approved_rentals = rentals.filter(status='approved').count()
    pending_rentals = rentals.filter(status='pending').count()
    rejected_rentals = rentals.filter(status='rejected').count()
    total_rentals = rentals.count()
    
    # Get similar machines based on machine type
    similar_machines = Machine.objects.filter(
        machine_type=machine.machine_type
    ).exclude(
        pk=machine.pk
    ).order_by('-created_at')[:5]
    
    # Create calendar events data
    calendar_events = []
    
    # Add rental events
    for rental in rentals:
        color = '#dc3545' if rental.status == 'approved' else '#ffc107'
        calendar_events.append({
            'title': 'Rented',
            'start': rental.start_date.strftime('%Y-%m-%d'),
            'end': rental.end_date.strftime('%Y-%m-%d'),
            'color': color
        })
    
    # Add maintenance events
    for record in maintenance_records:
        if record.end_date:
            end_date = record.end_date.strftime('%Y-%m-%d')
        else:
            end_date = None
            
        calendar_events.append({
            'title': 'Maintenance',
            'start': record.start_date.strftime('%Y-%m-%d'),
            'end': end_date,
            'color': '#fd7e14'
        })
    
    context = {
        'machine': machine,
        'rentals': rentals,
        'maintenance_records': maintenance_records,
        'price_history': price_history,
        'images': images,
        'similar_machines': similar_machines,
        'calendar_events_json': mark_safe(json.dumps(calendar_events)),
        'approved_rentals': approved_rentals,
        'pending_rentals': pending_rentals,
        'rejected_rentals': rejected_rentals,
        'total_rentals': total_rentals,
    }
    return render(request, 'machines/machine_detail.html', context)

@login_required
def machine_create(request):
    if request.method == 'POST':
        form = MachineForm(request.POST)
        formset = MachineImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            machine = form.save()
            
            # Process the formset
            image_instances = formset.save(commit=False)
            for image in image_instances:
                image.machine = machine
                image.save()
            
            # Handle deleted images
            for obj in formset.deleted_objects:
                obj.delete()
                
            # Ensure there's at least one primary image if images exist
            images = machine.images.all()
            if images.exists() and not images.filter(is_primary=True).exists():
                first_image = images.first()
                first_image.is_primary = True
                first_image.save()
                
            messages.success(request, 'Machine created successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MachineForm()
        formset = MachineImageFormSet()
    
    return render(request, 'machines/machine_form.html', {
        'form': form, 
        'formset': formset,
        'action': 'Create'
    })

@login_required
def machine_update(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        form = MachineForm(request.POST, instance=machine)
        formset = MachineImageFormSet(request.POST, request.FILES, instance=machine)
        
        if form.is_valid() and formset.is_valid():
            machine = form.save()
            
            # Process the formset
            image_instances = formset.save(commit=False)
            for image in image_instances:
                image.machine = machine
                image.save()
            
            # Handle deleted images
            for obj in formset.deleted_objects:
                obj.delete()
            
            # Ensure there's always a primary image if images exist
            images = machine.images.all()
            if images.exists() and not images.filter(is_primary=True).exists():
                first_image = images.first()
                first_image.is_primary = True
                first_image.save()
                
            messages.success(request, 'Machine updated successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MachineForm(instance=machine)
        formset = MachineImageFormSet(instance=machine)
    
    return render(request, 'machines/machine_form.html', {
        'form': form, 
        'formset': formset,
        'action': 'Update'
    })

# Old function-based view - replaced by MachineDeleteView class-based view
# @login_required
# def machine_delete(request, pk):
#     machine = get_object_or_404(Machine, pk=pk)
#     if request.method == 'POST':
#         machine.delete()
#         messages.success(request, 'Machine deleted successfully.')
#         return redirect('machines:machine_list')
#     
#     return render(request, 'machines/machine_confirm_delete.html', {'machine': machine})

@login_required
@verified_member_required
def rental_create(request, machine_pk=None):
    if machine_pk:
        selected_machine = get_object_or_404(Machine, pk=machine_pk)
        if selected_machine.is_dryer_service():
            messages.info(request, 'This dryer uses a separate dryer service process.')
            return redirect('machines:dryer_rental_create_for_machine', machine_id=selected_machine.pk)
        if selected_machine.machine_type == 'rice_mill':
            messages.info(request, 'Rice mill uses a separate milling appointment process.')
            return redirect('machines:ricemill_appointment_create_for_machine', machine_id=selected_machine.pk)

    if request.method == 'POST':
        form = RentalForm(request.POST, user=request.user)
        if form.is_valid():
            rental = form.save(commit=False)
            rental.user = request.user
            
            # Calculate payment amount from admin-configured machine pricing
            rental.payment_amount = rental.calculate_payment_amount()

            # Save the rental
            rental.save()
            
            if rental.payment_type == 'cash':
                # Create the linked payment record, but approval still comes first.
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                
                content_type = ContentType.objects.get_for_model(rental)
                Payment.objects.get_or_create(
                    content_type=content_type,
                    object_id=rental.id,
                    defaults={
                        'user': request.user,
                        'payment_type': 'rental',
                        'amount': rental.payment_amount or 0,
                        'currency': 'PHP',
                        'status': 'pending',
                    }
                )
                messages.success(
                    request,
                    'Rental request submitted successfully. Wait for admin approval before completing payment.'
                )
                return redirect('machines:rental_confirmation', pk=rental.pk)

            messages.success(
                request,
                'Rental request submitted. Non-cash payment settlement will be recorded after harvest and rice delivery.'
            )
            return redirect('machines:rental_confirmation', pk=rental.pk)
        else:
            # Detect overlap/conflict and notify the requester
            error_text = str(form.errors) + " " + " ".join(e for e in form.non_field_errors())
            if 'already rented' in error_text.lower():
                messages.error(request, 'This machine is already rented for the selected dates. Please rent this on another day.')
                try:
                    # Include machine name if available
                    machine_name = None
                    try:
                        mid = request.POST.get('machine') or form.initial.get('machine')
                        if mid:
                            m_obj = Machine.objects.filter(pk=mid).first()
                            machine_name = m_obj.name if m_obj else None
                    except Exception:
                        pass
                    # Try to get dates for message context
                    start_date = request.POST.get('start_date')
                    end_date = request.POST.get('end_date')
                    msg = 'This machine is already rented for the selected dates. Please rent this on another day.'
                    if machine_name:
                        if start_date and end_date:
                            msg = f'{machine_name} is already rented from {start_date} to {end_date}. Please rent this on another day.'
                        else:
                            msg = f'{machine_name} is already rented for the selected dates. Please rent this on another day.'
                    UserNotification.objects.create(
                        user=request.user,
                        notification_type='rental_conflict',
                        message=msg
                    )

                    # Broadcast to other verified members (prefer same sector)
                    try:
                        User = get_user_model()
                        # Determine requester's sector if available
                        requester_sector = None
                        try:
                            requester_sector = getattr(getattr(request.user, 'membership_application', None), 'assigned_sector', None)
                        except Exception:
                            requester_sector = None

                        recipients = None
                        if requester_sector:
                            recipients = User.objects.filter(is_verified=True, membership_application__assigned_sector=requester_sector)
                        else:
                            recipients = User.objects.filter(is_verified=True)
                        # Exclude the requester and operators (already notified or irrelevant)
                        recipients = recipients.exclude(pk=request.user.pk).exclude(role='operator')

                        broadcast_msg = msg
                        # Create notifications in bulk-like loop
                        for member in recipients:
                            UserNotification.objects.create(
                                user=member,
                                notification_type='rental_conflict_broadcast',
                                message=broadcast_msg
                            )
                    except Exception as e:
                        print(f'Failed to broadcast rental conflict notification: {e}')
                except Exception as e:
                    print(f'Failed to create rental conflict notification: {e}')
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = RentalForm(initial=initial, user=request.user)

    # Provide list of all machines with status for Services and Pricing section
    selectable_machines = form.fields['machine'].queryset
    available_machines = selectable_machines.filter(status='available')
    all_machines = selectable_machines
    
    # Get machine object if machine_pk is provided
    machine = None
    if machine_pk:
        try:
            machine = _machine_rental_queryset().get(pk=machine_pk)
        except Machine.DoesNotExist:
            pass
    
    return render(request, 'machines/rental_form_enhanced.html', {
        'form': form,
        'action': 'Create',
        'available_machines': available_machines,
        'all_machines': all_machines,
        'machine': machine,
    })

@login_required
def rental_update(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    if request.method == 'POST':
        form = RentalForm(request.POST, instance=rental, user=request.user)
        if form.is_valid():
            rental = form.save()
            messages.success(request, 'Rental updated successfully.')
            return redirect('machines:rental_confirmation', pk=rental.pk)
    else:
        form = RentalForm(instance=rental, user=request.user)

    selectable_machines = form.fields['machine'].queryset
    available_machines = selectable_machines.filter(status='available')
    all_machines = selectable_machines
    return render(request, 'machines/rental_form_enhanced.html', {
        'form': form,
        'action': 'Update',
        'available_machines': available_machines,
        'all_machines': all_machines,
    })

@login_required
def rental_delete(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    if request.method == 'POST':
        rental.mark_cancelled(
            cancellation_type='customer' if request.user == rental.user else 'admin',
            cancel_reason='Cancelled by customer.' if request.user == rental.user else 'Cancelled by admin.',
            system_note='Rental slot released after manual cancellation.'
        )
        rental.save(update_fields=[
            'status',
            'workflow_state',
            'cancellation_type',
            'cancel_reason',
            'system_note',
            'updated_at',
        ])
        rental.sync_machine_status()
        messages.success(request, 'Rental cancelled successfully.')
        return redirect('machines:machine_detail', pk=rental.machine.pk)
    
    return render(request, 'machines/rental_confirm_delete.html', {'rental': rental})

@login_required
def rental_slip(request, pk):
    """View for displaying printable rental slip after submission"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view the slip
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental slip.")
        return redirect('machines:rental_list')
    
    context = {
        'rental': rental,
    }
    
    return render(request, 'machines/rental_slip.html', context)

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_create(request, machine_pk=None):
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.created_by = request.user
            maintenance.save()
            _sync_machine_maintenance_status(maintenance.machine)
            messages.success(request, 'Maintenance record created successfully.')
            
            # Redirect to the maintenance detail page if it exists, otherwise to the machine detail
            try:
                return redirect('machines:maintenance_detail', pk=maintenance.pk)
            except NoReverseMatch:
                return redirect('machines:machine_detail', pk=maintenance.machine.pk)
    else:
        initial = {}
        if machine_pk:
            initial['machine'] = machine_pk
        elif request.GET.get('machine'):
            initial['machine'] = request.GET.get('machine')
        form = MaintenanceForm(initial=initial)
    
    return render(
        request,
        'machines/maintenance_form.html',
        {
            'form': form,
            'action': 'Create',
            'submit_label': 'Create Maintenance',
        },
    )

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_update(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if maintenance.status == 'completed':
        messages.info(request, 'Completed records are finalized through the Finish Maintenance flow and can no longer be edited here.')
        return redirect('machines:maintenance_detail', pk=maintenance.pk)

    if request.method == 'POST':
        previous_machine = maintenance.machine
        form = MaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            maintenance = form.save(commit=False)

            if maintenance.status == 'completed' and not maintenance.actual_completion_date:
                maintenance.actual_completion_date = timezone.now()
            elif maintenance.status != 'completed':
                maintenance.actual_completion_date = None

            maintenance.save()
            _sync_machine_maintenance_status(maintenance.machine)
            if previous_machine.pk != maintenance.machine.pk:
                _sync_machine_maintenance_status(previous_machine)
            
            messages.success(request, 'Maintenance record updated successfully.')
            
            # Redirect to the maintenance detail page if it exists, otherwise to the machine detail
            try:
                return redirect('machines:maintenance_detail', pk=maintenance.pk)
            except NoReverseMatch:
                return redirect('machines:machine_detail', pk=maintenance.machine.pk)
    else:
        form = MaintenanceForm(instance=maintenance)
    
    return render(
        request,
        'machines/maintenance_form.html',
        {
            'form': form,
            'maintenance': maintenance,
            'action': 'Update',
            'submit_label': 'Save Changes',
        },
    )

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)
    if request.method == 'POST':
        machine = maintenance.machine
        maintenance.delete()
        _sync_machine_maintenance_status(machine)
        messages.success(request, 'Maintenance record deleted successfully.')
        return redirect('machines:machine_detail', pk=machine.pk)
    
    return render(request, 'machines/maintenance_confirm_delete.html', {'maintenance': maintenance})

@login_required
def price_history_create(request, machine_pk):
    machine = get_object_or_404(Machine, pk=machine_pk)
    if request.method == 'POST':
        form = PriceHistoryForm(request.POST)
        if form.is_valid():
            price_history = form.save(commit=False)
            price_history.machine = machine
            price_history.created_by = request.user
            price_history.save()
            
            # Update machine's current price
            machine.current_price = price_history.price
            machine.save()
            
            messages.success(request, 'Price history record created successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
    else:
        form = PriceHistoryForm()
    
    return render(request, 'machines/price_history_form.html', {'form': form, 'machine': machine})

@login_required
def rental_list(request):
    """User's rental history organized by status - Redirects admins to admin dashboard"""
    from datetime import date
    from django.shortcuts import redirect
    
    # If user is admin/staff, redirect to admin dashboard
    if request.user.is_staff or request.user.is_superuser:
        return redirect('machines:admin_rental_dashboard')
    
    today = date.today()
    Rental.sync_overdue_workflow_states(today=today)
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()
    valid_status_filters = {'all', 'pending', 'approved', 'in_progress', 'past', 'cancelled'}
    if status_filter not in valid_status_filters:
        status_filter = 'all'

    user_rentals = Rental.objects.filter(user=request.user).select_related('machine')
    
    # Add payment information to context for each rental efficiently
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment
    
    rental_ct = ContentType.objects.get_for_model(Rental)
    rental_ids = list(user_rentals.values_list('id', flat=True))
    
    # Prefetch payments for all rentals to avoid N+1 queries
    payments_dict = {}
    if rental_ids:
        payments = Payment.objects.filter(
            content_type=rental_ct,
            object_id__in=rental_ids
        ).select_related('user')
        
        for payment in payments:
            payments_dict[payment.object_id] = payment

    if search_query:
        user_rentals = user_rentals.filter(
            Q(machine__name__icontains=search_query) |
            Q(machine__machine_type__icontains=search_query) |
            Q(purpose__icontains=search_query) |
            Q(field_location__icontains=search_query)
        )
    
    # Categorize rentals by workflow state instead of calendar buckets.
    pending_rentals = user_rentals.filter(status='pending').order_by('-created_at')

    approved_rentals = user_rentals.filter(
        status='approved',
        workflow_state__in=['approved', 'conflict_review']
    ).order_by('start_date', 'created_at')

    in_progress_rentals = user_rentals.filter(
        workflow_state__in=['in_progress', 'overdue', 'harvest_report_submitted']
    ).order_by('start_date', 'created_at')

    history_rentals = user_rentals.filter(
        Q(status='completed') |
        Q(workflow_state='completed') |
        Q(status='rejected') |
        Q(status='cancelled')
    ).order_by('-updated_at', '-created_at')

    # Apply status filter
    if status_filter == 'pending':
        approved_rentals = approved_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'approved':
        pending_rentals = pending_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'in_progress':
        pending_rentals = pending_rentals.none()
        approved_rentals = approved_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'past':
        pending_rentals = pending_rentals.none()
        approved_rentals = approved_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
    elif status_filter == 'cancelled':
        pending_rentals = pending_rentals.none()
        approved_rentals = approved_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
        history_rentals = history_rentals.filter(status='cancelled')

    pending_count = pending_rentals.count()
    approved_count = approved_rentals.count()
    in_progress_count = in_progress_rentals.count()
    history_count = history_rentals.count()

    # Add pagination for history rentals (largest list)
    from django.core.paginator import Paginator
    
    history_paginator = Paginator(history_rentals, 10)  # 10 items per page
    history_page_number = request.GET.get('history_page')
    history_page_obj = history_paginator.get_page(history_page_number)
    package_requests = RentalPackage.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    package_update_count = _get_package_update_count(request.user)

    pending_rentals = list(pending_rentals)
    approved_rentals = list(approved_rentals)
    in_progress_rentals = list(in_progress_rentals)

    for rental in pending_rentals:
        rental.payment_record = payments_dict.get(rental.id)
    for rental in approved_rentals:
        rental.payment_record = payments_dict.get(rental.id)
    for rental in in_progress_rentals:
        rental.payment_record = payments_dict.get(rental.id)
    for rental in history_page_obj.object_list:
        rental.payment_record = payments_dict.get(rental.id)

    pending_cash_rentals = [rental for rental in pending_rentals if rental.payment_type != 'in_kind']
    pending_in_kind_rentals = [rental for rental in pending_rentals if rental.payment_type == 'in_kind']
    cash_rentals = sorted(
        [rental for rental in approved_rentals + in_progress_rentals if rental.payment_type != 'in_kind'],
        key=lambda rental: (rental.start_date or today, rental.created_at, rental.pk),
    )
    rice_share_rentals = sorted(
        [rental for rental in approved_rentals + in_progress_rentals if rental.payment_type == 'in_kind'],
        key=lambda rental: (rental.start_date or today, rental.created_at, rental.pk),
    )

    context = {
        'pending_rentals': pending_rentals,
        'approved_rentals': approved_rentals,
        'in_progress_rentals': in_progress_rentals,
        'pending_cash_rentals': pending_cash_rentals,
        'pending_in_kind_rentals': pending_in_kind_rentals,
        'cash_rentals': cash_rentals,
        'rice_share_rentals': rice_share_rentals,
        'history_rentals': history_page_obj,
        'history_page_obj': history_page_obj,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'in_progress_count': in_progress_count,
        'history_count': history_count,
        'status_filter': status_filter,
        'search_query': search_query,
        'package_requests': package_requests[:5],
        'package_total_count': package_requests.count(),
        'package_pending_count': package_requests.filter(status='pending').count(),
        'package_active_count': package_requests.exclude(status__in=['completed', 'cancelled']).count(),
        'package_update_count': package_update_count,
        'payments_dict': payments_dict,  # Add payments for efficient template access
    }
    
    return render(request, 'machines/rental_list_organized.html', context)

@login_required
def rental_detail(request, pk):
    """Legacy rental detail route kept as a redirect to confirmation."""
    rental = get_object_or_404(Rental, pk=pk, user=request.user)
    return redirect('machines:rental_confirmation', pk=rental.pk)

@login_required
def rental_confirmation(request, pk):
    """View rental confirmation after submission"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental confirmation.")
        return redirect('machines:rental_list')

    rental.payment_record = rental.payment
    purpose_details = []
    if rental.purpose:
        for raw_line in str(rental.purpose).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if ':' in line:
                label, value = line.split(':', 1)
                purpose_details.append({
                    'label': label.strip() or 'Detail',
                    'value': value.strip() or 'N/A',
                })
            else:
                purpose_details.append({
                    'label': 'Note',
                    'value': line,
                })

    return render(request, 'machines/rental_confirmation.html', {
        'rental': rental,
        'payment_record': rental.payment_record,
        'purpose_details': purpose_details,
    })


def rental_confirmation_print(request, pk):
    """Render a printable payment form for over-the-counter payments"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental.")
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_confirmation_print.html', {
        'rental': rental,
        'back_url': reverse('machines:rental_confirmation', kwargs={'pk': rental.pk}),
        'back_label': 'Back to Confirmation',
    })

@login_required
def payment_success(request):
    """View payment success page after PayMongo GCash payment"""
    # Get the most recent rental for this user
    rental = Rental.objects.filter(user=request.user).order_by('-created_at').first()
    
    # Mark payment as pending verification if rental exists
    if rental and not rental.payment_verified:
        messages.success(
            request,
            'Payment received. Admin verification is still required before the rental is completed.'
        )
    
    return render(request, 'machines/payment_success.html', {'rental': rental})

@login_required
def upload_payment_proof(request, rental_id):
    """Handle payment proof upload with validation"""
    rental = get_object_or_404(Rental, pk=rental_id)
    
    # Security check - only rental owner can upload proof
    if rental.user != request.user:
        messages.error(request, "You don't have permission to upload proof for this rental.")
        return redirect('machines:rental_list')
    
    if request.method == 'POST':
        payment_proof = request.FILES.get('payment_proof')
        
        if payment_proof:
            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            if payment_proof.size > max_size:
                messages.error(request, 'File size too large. Maximum size is 5MB.')
                return redirect('machines:rental_confirmation', pk=rental_id)
            
            # Validate file type - only JPG, JPEG, PNG
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            file_extension = payment_proof.name.lower().split('.')[-1]
            allowed_extensions = ['jpg', 'jpeg', 'png']
            
            if payment_proof.content_type not in allowed_types or file_extension not in allowed_extensions:
                messages.error(request, 'Invalid file type. Please upload JPG, JPEG, or PNG images only.')
                return redirect('machines:rental_confirmation', pk=rental_id)
            
            # Rename file automatically for security and organization
            # Format: proof_{rental_id}_{timestamp}.{extension}
            from django.utils.text import slugify
            import time
            timestamp = int(time.time())
            new_filename = f"proof_{rental.id}_{timestamp}.{file_extension}"
            
            # Update the file name
            payment_proof.name = new_filename
            
            # Save the payment proof
            rental.payment_slip = payment_proof
            rental.payment_date = timezone.now()
            rental.save()
            
            messages.success(request, 'Payment proof uploaded successfully. Admin will verify it shortly.')
            
            # Create notification for admin
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True).exclude(role='operator')
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='payment_proof_uploaded',
                        message=f'{rental.customer_display_name} uploaded payment proof for {rental.machine.name} rental.'
                    )
            except Exception as e:
                print(f'Failed to create admin notification: {e}')
        else:
            messages.error(request, 'Please select a file to upload.')
    
    return redirect('machines:rental_confirmation', pk=rental_id)



@login_required
def rental_reject(request, pk):
    """View to reject a rental request"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser or request.user.has_perm('machines.can_approve_rentals')):
        messages.error(request, "You don't have permission to reject rentals.")
        return redirect('machines:rental_list')
    
    if request.method == 'POST':
        rental.status = 'rejected'
        rental.save()
        
        rental.machine.sync_status()
        
        messages.success(request, f'Rental request for {rental.machine.name} has been rejected.')
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_confirm_reject.html', {'rental': rental})

# Rental Package Views

def _package_item_rental_area(package_item):
    if package_item.pricing_unit in {'hectare', 'kg', 'sack', 'hour'}:
        quantity = package_item.quantity
        if quantity in [None, '']:
            quantity = package_item.compute_default_quantity()
        return quantity
    return package_item.rental_package.area


def _is_package_reserve_rental(rental):
    return bool((rental.purpose or '').startswith('Package:'))


def _sync_linked_package_after_rental_change(rental):
    try:
        package_item = rental.package_item
    except RentalPackageItem.DoesNotExist:
        return None

    if not package_item.rental_package_id:
        return None

    package = package_item.rental_package
    _sync_package_progress_from_rentals(package, save=True)
    package.refresh_total_amount(save=True)
    package.refresh_payment_status(save=True)
    return package


def _sync_package_rental_payment(rental):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(rental)
    payment, _ = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=rental.id,
        defaults={
            'user': rental.user,
            'payment_type': 'rental',
            'amount': rental.payment_amount or Decimal('0.00'),
            'currency': 'PHP',
            'status': 'pending',
        },
    )

    update_fields = []
    if payment.user_id != rental.user_id:
        payment.user = rental.user
        update_fields.append('user')
    if payment.amount != (rental.payment_amount or Decimal('0.00')):
        payment.amount = rental.payment_amount or Decimal('0.00')
        update_fields.append('amount')
    if payment.status != 'pending':
        payment.status = 'pending'
        update_fields.append('status')
    if update_fields:
        payment.save(update_fields=update_fields)


def _release_package_item_rental(package_item):
    rental = package_item.linked_rental
    if not rental:
        return

    old_machine = rental.machine
    rental.status = 'cancelled'
    rental.workflow_state = 'cancelled'
    rental.operator_status = 'unassigned'
    rental.save(update_fields=['status', 'workflow_state', 'operator_status', 'updated_at'])
    if old_machine:
        old_machine.sync_status()


def _can_close_package(package):
    if package.status in {'completed', 'cancelled', 'in_progress'}:
        return False
    return not package.items.exclude(status='not_included').filter(
        status__in=['in_progress', 'completed']
    ).exists()


def _can_edit_package_schedule(package):
    return package.status not in {'completed', 'cancelled', 'in_progress'}


def _close_rental_package(package, *, acting_user, action_label):
    cancellation_type = 'admin' if getattr(acting_user, 'is_staff', False) else 'customer'
    cancel_reason = (
        f'Package request {action_label.lower()} by admin.'
        if cancellation_type == 'admin'
        else 'Package request cancelled by requester.'
    )
    system_note = f'Package "{package.package_name}" was {action_label.lower()}.'
    item_note = 'Rejected as part of the package decision.' if action_label == 'Rejected' else 'Cancelled by requester.'

    with transaction.atomic():
        items = list(package.items.exclude(status='not_included').select_related('linked_rental', 'machine'))
        for item in items:
            if item.linked_rental_id:
                rental = item.linked_rental
                rental.mark_cancelled(
                    cancellation_type=cancellation_type,
                    cancel_reason=cancel_reason,
                    system_note=system_note,
                )
                rental.operator_status = 'unassigned'
                rental.save(update_fields=[
                    'status',
                    'workflow_state',
                    'cancellation_type',
                    'cancel_reason',
                    'system_note',
                    'operator_status',
                    'updated_at',
                ])
                rental.sync_machine_status()

            item.status = 'cancelled'
            item.is_tentative = False
            item.machine = None
            item.scheduled_start = None
            item.scheduled_end = None
            item.linked_rental = None
            if item_note not in (item.notes or ''):
                item.notes = f'{item.notes}\n{item_note}'.strip() if item.notes else item_note
            item.save(update_fields=[
                'status',
                'is_tentative',
                'machine',
                'scheduled_start',
                'scheduled_end',
                'linked_rental',
                'notes',
                'updated_at',
            ])

        package.status = 'cancelled'
        update_fields = ['status', 'updated_at']
        if getattr(acting_user, 'is_staff', False):
            package.approved_by = acting_user
            package.approved_at = timezone.now()
            update_fields.extend(['approved_by', 'approved_at'])
        package.save(update_fields=update_fields)
        package.refresh_total_amount(save=True)
        package.refresh_payment_status(save=True)


def _sync_package_items_to_rentals(package, acting_user=None):
    for item in package.items.exclude(status='not_included').order_by('sequence_order', 'pk'):
        if item.has_confirmed_schedule:
            _sync_package_item_rental(item, acting_user or package.approved_by)
        else:
            _release_package_item_rental(item)
    package.refresh_payment_status(save=True)


def _undecided_package_items(package):
    return [
        item for item in package.items.exclude(status__in=['not_included', 'completed', 'cancelled']).order_by('sequence_order', 'pk')
        if not item.has_confirmed_schedule
    ]


def _promote_schedule_ready_package_items(items):
    promoted_items = []
    for item in items:
        if item.status in {'cancelled', 'not_included', 'completed', 'in_progress'}:
            continue
        if item.has_schedule_inputs and not item.is_tentative and item.status in {'requested', 'tentative'}:
            item.status = 'scheduled'
            item.save(update_fields=['status', 'updated_at'])
            promoted_items.append(item.pk)
    return promoted_items


def _save_package_status(package, *, approver=None, allow_full_approval=False):
    computed_status = package.update_status_from_items(save=False)
    if computed_status == 'approved' and not allow_full_approval:
        package.status = 'partially_scheduled'

    update_fields = ['status', 'updated_at']
    if approver is not None:
        package.approved_by = approver
        package.approved_at = timezone.now()
        update_fields.extend(['approved_by', 'approved_at'])
    package.save(update_fields=update_fields)
    return package.status


def _sync_package_item_rental(package_item, approved_by):
    if (
        package_item.status not in {'scheduled', 'in_progress', 'completed'}
        or not package_item.machine_id
        or not package_item.scheduled_start
        or not package_item.scheduled_end
    ):
        return None

    package = package_item.rental_package
    is_available, conflicts = Rental.check_availability_for_approval(
        package_item.machine,
        package_item.scheduled_start,
        package_item.scheduled_end,
        exclude_rental_id=package_item.linked_rental_id,
    )
    if not is_available:
        conflict = conflicts.first()
        raise ValidationError(
            f'{package_item.machine.name} is already booked from '
            f'{conflict.start_date} to {conflict.end_date}. Please choose different dates.'
        )

    existing_rental = package_item.linked_rental if package_item.linked_rental_id else None
    if existing_rental and (
        existing_rental.status in {'completed', 'cancelled', 'rejected'}
        or existing_rental.workflow_state in {'completed', 'cancelled'}
        or (
            existing_rental.payment_type == 'in_kind'
            and existing_rental.settlement_status == 'paid'
        )
    ):
        target_status = 'completed'
        if (
            existing_rental.status in {'cancelled', 'rejected'}
            or existing_rental.workflow_state == 'cancelled'
        ):
            target_status = 'cancelled'
        if package_item.status != target_status:
            package_item.status = target_status
            package_item.save(update_fields=['status', 'updated_at'])
        return existing_rental

    previous_machine = existing_rental.machine if existing_rental and existing_rental.machine_id else None
    rental = package_item.linked_rental or Rental(
        machine=package_item.machine,
        user=package.user,
        start_date=package_item.scheduled_start,
        end_date=package_item.scheduled_end,
    )
    rental.machine = package_item.machine
    rental.user = package.user
    rental.customer_name = package.farmer_name
    rental.customer_address = package.location
    rental.field_location = package.location
    rental.area = _package_item_rental_area(package_item)
    rental.start_date = package_item.scheduled_start
    rental.end_date = package_item.scheduled_end
    rental.payment_type = package_item.machine.rental_price_type
    rental.settlement_type = package_item.machine.settlement_type
    rental.payment_method = package.payment_preference if package_item.machine.rental_price_type == 'cash' else None
    rental.status = 'approved'
    rental.workflow_state = 'approved'
    rental.operator_status = 'unassigned'
    rental.verified_by = approved_by if approved_by and approved_by.is_authenticated else None
    rental.purpose = (
        f"Package: {package.package_name}\n"
        f"Service: {package_item.service_name}\n"
        f"Sequence Order: {package_item.sequence_order}\n"
        f"Service Quantity: {package_item.quantity or package_item.compute_default_quantity()} {package_item.pricing_unit or 'unit'}\n"
        f"Preferred Start: {package.preferred_start_date}\n"
        f"Package Notes: {package.notes or 'None'}"
    )
    rental.payment_amount = rental.calculate_payment_amount()
    if rental.payment_type == 'cash':
        rental.payment_status = 'pending'
    else:
        rental.payment_status = 'to_be_determined'
        rental.settlement_status = 'to_be_determined'

    if not rental.requires_operator_service:
        rental.workflow_state = 'ready_for_payment' if rental.payment_type == 'cash' else 'ready_for_operation'

    rental.save()
    rental.machine.sync_status()
    if previous_machine and previous_machine.pk != rental.machine_id:
        previous_machine.sync_status()

    if rental.payment_type == 'cash':
        _sync_package_rental_payment(rental)

    if package_item.linked_rental_id != rental.id:
        package_item.linked_rental = rental
        if package_item.status == 'requested':
            package_item.status = 'scheduled'
        package_item.save()

    return rental


def _package_validation_messages(exc):
    if hasattr(exc, 'message_dict'):
        messages_list = []
        for field_messages in exc.message_dict.values():
            messages_list.extend(field_messages)
        if messages_list:
            return messages_list
    if hasattr(exc, 'messages') and exc.messages:
        return list(exc.messages)
    return [str(exc)]


def _approve_rental_package(package, approved_by):
    with transaction.atomic():
        _promote_schedule_ready_package_items(
            package.items.exclude(status='not_included').order_by('sequence_order', 'pk')
        )
        _sync_package_items_to_rentals(package, approved_by)
        _save_package_status(package, approver=approved_by, allow_full_approval=True)
        package.refresh_total_amount(save=True)
        package.refresh_payment_status(save=True)


def _auto_approve_rental_package_if_ready(package, approved_by):
    if not approved_by or not getattr(approved_by, 'is_authenticated', False):
        return False
    if package.status in {'cancelled', 'completed', 'in_progress'}:
        return False

    included_items = list(
        package.items.exclude(status__in=['not_included', 'cancelled']).select_related('linked_rental')
    )
    if not included_items or _undecided_package_items(package):
        return False
    if not all(item.linked_rental_id or item.status == 'completed' for item in included_items):
        return False

    should_notify = not (
        package.approved_by_id
        and package.approved_at
        and package.status in {'approved', 'in_progress', 'completed'}
    )
    _save_package_status(package, approver=approved_by, allow_full_approval=True)
    package.refresh_total_amount(save=True)
    package.refresh_payment_status(save=True)

    if should_notify and package.status == 'approved':
        _notify_package_request_approved(package)
        return True
    return False


def _annotate_package_linked_rental(item, *, can_manage_package, package_detail_url):
    rental = item.linked_rental
    if not rental:
        return

    is_effectively_completed = bool(
        rental.status in {'completed', 'cancelled', 'rejected'}
        or rental.workflow_state in {'completed', 'cancelled'}
        or (rental.payment_type == 'in_kind' and rental.settlement_status == 'paid')
    )
    rental.package_completed = bool(
        rental.status == 'completed'
        or rental.workflow_state == 'completed'
        or (rental.payment_type == 'in_kind' and rental.settlement_status == 'paid')
    )
    rental.package_needs_operator_assignment = bool(
        rental.requires_operator_service
        and rental.status == 'approved'
        and not is_effectively_completed
        and rental.operator_status not in ('completed', 'harvest_reported')
        and rental.assigned_operator_id is None
    )
    rental.package_can_assign_operator = bool(
        can_manage_package
        and rental.package_needs_operator_assignment
    )
    rental.package_show_operator_assignment = bool(
        rental.requires_operator_service
        and not is_effectively_completed
        and (rental.package_needs_operator_assignment or rental.assigned_operator_id)
    )
    rental.package_ready_for_operation = bool(
        rental.payment_type == 'in_kind'
        and rental.status == 'approved'
        and not is_effectively_completed
        and (
            rental.workflow_state == 'ready_for_operation'
            or (rental.workflow_state == 'approved' and not rental.requires_operator_service)
        )
    )
    rental.package_ready_for_payment = bool(
        rental.payment_type != 'in_kind'
        and rental.status == 'approved'
        and not is_effectively_completed
        and (
            rental.workflow_state == 'ready_for_payment'
            or (
                rental.workflow_state == 'approved'
                and (not rental.requires_operator_service or rental.assigned_operator_id is not None)
            )
        )
        and not (
            rental.payment_method == 'online'
            and (rental.payment_date or rental.stripe_session_id)
        )
    )
    rental.package_payment_submitted = bool(
        rental.payment_type != 'in_kind'
        and rental.status == 'approved'
        and not is_effectively_completed
        and not rental.payment_verified
        and rental.payment_method == 'online'
        and bool(rental.payment_date or rental.stripe_session_id)
    )
    rental.package_in_operation = bool(
        not is_effectively_completed
        and rental.workflow_state == 'in_progress'
    )
    rental.package_harvest_recorded = bool(
        rental.payment_type == 'in_kind'
        and not is_effectively_completed
        and rental.workflow_state == 'harvest_report_submitted'
    )
    rental.package_can_record_face_to_face_payment = bool(
        can_manage_package
        and rental.payment_method in {None, '', 'face_to_face'}
        and not rental.payment_verified
        and rental.package_ready_for_payment
    )
    rental.package_can_verify_online_payment = bool(
        can_manage_package
        and rental.payment_method == 'online'
        and not rental.payment_verified
        and rental.package_payment_submitted
    )
    rental.package_can_complete_paid_rental = bool(
        can_manage_package
        and rental.payment_type != 'in_kind'
        and rental.payment_verified
        and rental.workflow_state == 'in_progress'
        and rental.status == 'approved'
        and (
            not rental.requires_operator_service
            or rental.assigned_operator_id is not None
        )
    )
    rental.package_can_start_operation = bool(
        can_manage_package
        and rental.payment_type == 'in_kind'
        and rental.package_ready_for_operation
    )
    rental.package_can_submit_harvest = bool(
        can_manage_package
        and rental.payment_type == 'in_kind'
        and rental.workflow_state in ('in_progress', 'harvest_report_submitted')
    )
    rental.package_can_confirm_rice_received = bool(
        can_manage_package
        and rental.payment_type == 'in_kind'
        and rental.settlement_status in {'waiting_for_delivery', 'partially_settled'}
    )
    rental.package_has_cash_workflow_actions = bool(
        rental.payment_type != 'in_kind'
        and not is_effectively_completed
        and (
            rental.package_needs_operator_assignment
            or rental.package_ready_for_payment
            or rental.package_payment_submitted
            or rental.package_in_operation
            or rental.package_can_complete_paid_rental
        )
    )
    rental.package_has_rice_workflow_actions = bool(
        rental.payment_type == 'in_kind'
        and not is_effectively_completed
        and (
            rental.package_show_operator_assignment
            or rental.package_ready_for_operation
            or rental.package_can_start_operation
            or rental.package_can_submit_harvest
            or rental.package_can_confirm_rice_received
        )
    )
    if rental.package_completed:
        rental.package_stage_label = 'Completed'
    elif rental.package_needs_operator_assignment:
        rental.package_stage_label = 'Waiting for operator assignment'
    elif rental.package_ready_for_payment:
        rental.package_stage_label = 'Ready for payment'
    elif rental.package_payment_submitted:
        rental.package_stage_label = 'Payment submitted'
    elif rental.package_ready_for_operation:
        rental.package_stage_label = 'Ready for operation'
    elif rental.package_harvest_recorded:
        rental.package_stage_label = 'Harvest recorded'
    elif rental.package_in_operation:
        rental.package_stage_label = 'In operation'
    else:
        rental.package_stage_label = rental.payment_progress_label
    rental.package_detail_url = package_detail_url


def _get_package_update_count(user):
    if not user.is_authenticated or _package_management_access(user):
        return 0

    updated_package_ids = set(
        RentalPackage.objects.filter(user=user).filter(
            Q(member_last_viewed_at__isnull=True) |
            Q(updated_at__gt=F('member_last_viewed_at'))
        ).values_list('id', flat=True)
    )
    unread_package_notification_ids = set(
        UserNotification.objects.filter(
            user=user,
            is_read=False,
            notification_type__startswith='rental_package_',
            related_object_id__isnull=False,
        ).values_list('related_object_id', flat=True)
    )
    return len(updated_package_ids | unread_package_notification_ids)


def _mark_package_notifications_as_read(user, *, package=None):
    if not user or not user.is_authenticated:
        return 0

    notification_qs = UserNotification.objects.filter(
        user=user,
        is_read=False,
        notification_type__startswith='rental_package_',
    )
    if package is not None:
        notification_qs = notification_qs.filter(related_object_id=package.pk)
    return notification_qs.update(is_read=True)


def _build_package_payment_summary(package, *, items=None, can_manage_package=False):
    source_items = items if items is not None else package.items.all()
    included_items = [
        item for item in source_items
        if item.status != 'not_included'
    ]
    package_detail_url = reverse('machines:rental_package_detail', kwargs={'pk': package.pk})
    linked_items = [item for item in included_items if item.linked_rental_id]
    for item in linked_items:
        _annotate_package_linked_rental(
            item,
            can_manage_package=can_manage_package,
            package_detail_url=package_detail_url,
        )
    cash_items = [
        item for item in linked_items
        if item.linked_rental.payment_type != 'in_kind'
    ]
    rice_share_items = [
        item for item in linked_items
        if item.linked_rental.payment_type == 'in_kind'
    ]

    operator_assignment_items = [
        item for item in linked_items
        if item.linked_rental.package_needs_operator_assignment
    ]
    cash_ready_payment_items = [
        item for item in cash_items
        if item.linked_rental.package_ready_for_payment
    ]
    cash_pending_verification_items = [
        item for item in cash_items
        if item.linked_rental.package_payment_submitted
    ]
    cash_in_operation_items = [
        item for item in cash_items
        if item.linked_rental.package_in_operation
    ]
    rice_share_pending_items = [
        item for item in rice_share_items
        if not item.linked_rental.package_completed
        and not item.linked_rental.package_needs_operator_assignment
    ]
    settled_items = [
        item for item in linked_items
        if item.linked_rental.package_completed
    ]
    unscheduled_items = [
        item for item in included_items
        if not item.linked_rental_id
    ]

    return {
        'linked_items': linked_items,
        'operator_assignment_items': operator_assignment_items,
        'cash_ready_payment_items': cash_ready_payment_items,
        'cash_pending_verification_items': cash_pending_verification_items,
        'cash_in_operation_items': cash_in_operation_items,
        'rice_share_pending_items': rice_share_pending_items,
        'settled_items': settled_items,
        'unscheduled_items': unscheduled_items,
    }


def _sync_package_progress_from_rentals(package, *, save=True):
    if package.status in {'cancelled', 'completed'}:
        return package

    included_items = list(
        package.items.exclude(status='not_included').select_related('linked_rental')
    )
    package_changed_fields = []

    for item in included_items:
        rental = item.linked_rental
        if not rental:
            continue

        rental_changed_fields = []
        package_preference = package.payment_preference or None
        operator_ready = (
            not rental.requires_operator_service
            or rental.assigned_operator_id is not None
        )

        if (
            rental.payment_type == 'cash'
            and not rental.payment_method
            and package_preference in {'online', 'face_to_face'}
        ):
            rental.payment_method = package_preference
            rental_changed_fields.append('payment_method')

        if (
            rental.status == 'approved'
            and operator_ready
            and rental.workflow_state == 'approved'
        ):
            target_workflow_state = (
                'ready_for_payment'
                if rental.payment_type == 'cash'
                else 'ready_for_operation'
            )
            rental.workflow_state = target_workflow_state
            rental_changed_fields.append('workflow_state')

        if save and rental_changed_fields:
            rental.save(update_fields=rental_changed_fields + ['updated_at'])

        target_status = item.status
        if rental.status in {'cancelled', 'rejected'} or rental.workflow_state == 'cancelled':
            target_status = 'cancelled'
        elif (
            rental.status == 'completed'
            or rental.workflow_state == 'completed'
            or (rental.payment_type == 'in_kind' and rental.settlement_status == 'paid')
        ):
            target_status = 'completed'
        elif rental.workflow_state in {'in_progress', 'harvest_report_submitted'}:
            target_status = 'in_progress'
        elif rental.status == 'approved':
            target_status = 'scheduled'

        if target_status != item.status:
            item.status = target_status
            if save:
                item.save(update_fields=['status', 'updated_at'])

    non_cancelled_items = [item for item in included_items if item.status != 'cancelled']
    if not non_cancelled_items:
        derived_status = 'cancelled' if included_items else 'pending'
    elif all(item.status == 'completed' for item in non_cancelled_items):
        derived_status = 'completed'
    elif any(item.status == 'in_progress' for item in non_cancelled_items):
        derived_status = 'in_progress'
    elif all(item.linked_rental_id or item.status == 'completed' for item in non_cancelled_items):
        derived_status = 'approved'
    elif any(item.status in {'scheduled', 'tentative'} for item in non_cancelled_items):
        derived_status = 'partially_scheduled'
    else:
        derived_status = 'pending'

    if package.status != derived_status:
        package.status = derived_status
        package_changed_fields.append('status')

    if not package.payment_preference:
        cash_methods = {
            item.linked_rental.payment_method
            for item in non_cancelled_items
            if item.linked_rental_id
            and item.linked_rental
            and item.linked_rental.payment_type == 'cash'
            and item.linked_rental.payment_method
        }
        if len(cash_methods) == 1:
            package.payment_preference = cash_methods.pop()
            package_changed_fields.append('payment_preference')

    if save and package_changed_fields:
        package.save(update_fields=package_changed_fields + ['updated_at'])

    return package


@login_required
def rental_package_list(request):
    if _package_management_access(request.user):
        packages = list(
            RentalPackage.objects.select_related('user', 'approved_by').prefetch_related('items').order_by('-created_at')
        )
    else:
        packages = list(
            RentalPackage.objects.filter(user=request.user).select_related('user', 'approved_by').prefetch_related('items').order_by('-created_at')
        )

    for package in packages:
        _sync_package_progress_from_rentals(package, save=True)
        package.refresh_payment_status(save=True)
        # Add count of unscheduled items
        package.unscheduled_items_count = package.items.filter(status__in=['requested', 'tentative']).count()
        package.can_delete_from_list = _can_close_package(package)

    _mark_package_notifications_as_read(request.user)

    if not _package_management_access(request.user):
        viewed_at = timezone.now()
        RentalPackage.objects.filter(user=request.user).update(member_last_viewed_at=viewed_at)
        for package in packages:
            package.member_last_viewed_at = viewed_at

    package_total_count = len(packages)
    package_pending_count = sum(1 for package in packages if package.status == 'pending')
    package_active_count = sum(1 for package in packages if package.status not in {'completed', 'cancelled'})

    return render(request, 'machines/rental_package_list.html', {
        'packages': packages,
        'can_manage_packages': _package_management_access(request.user),
        'equipment_rentals_url': _equipment_rentals_url_for_user(request.user),
        'package_total_count': package_total_count,
        'package_pending_count': package_pending_count,
        'package_active_count': package_active_count,
    })


@login_required
def rental_package_delete(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Package deletion requires a POST request.')

    package = get_object_or_404(RentalPackage.objects.select_related('user', 'approved_by'), pk=pk)
    can_manage_package = _package_management_access(request.user)
    if not can_manage_package and package.user_id != request.user.id:
        return HttpResponseForbidden('You do not have permission to delete this rental package.')

    if not _can_close_package(package):
        messages.error(request, 'This package can no longer be deleted because work has already started or been completed.')
        return redirect('machines:rental_package_list')

    if can_manage_package:
        _close_rental_package(package, acting_user=request.user, action_label='Rejected')
        _notify_package_request_rejected(package)
        messages.success(request, 'Package request deleted successfully.')
    else:
        _close_rental_package(package, acting_user=request.user, action_label='Cancelled')
        _notify_package_request_cancelled(package, notify_admins=True)
        messages.success(request, 'Package request deleted successfully.')

    return redirect('machines:rental_package_list')


@login_required
def rental_package_create(request):
    if not _package_request_access(request.user):
        messages.error(request, 'Only verified members or authorized staff can request a rental package.')
        return redirect('machines:machine_list')

    if request.method == 'POST':
        form = RentalPackageRequestForm(request.POST, user=request.user)
        if form.is_valid():
            package = form.save()
            _notify_package_request_submitted(package)
            messages.success(request, 'Rental package request submitted successfully. Admin will review and finalize the schedule.')
            return redirect('machines:rental_package_detail', pk=package.pk)
    else:
        form = RentalPackageRequestForm(user=request.user)

    return render(request, 'machines/rental_package_form.html', {
        'form': form,
        'service_fields': form.get_service_field_groups(),
        'machine_pricing_catalog': form.get_machine_pricing_catalog(),
        'equipment_rentals_url': _equipment_rentals_url_for_user(request.user),
    })


@login_required
def rental_package_detail(request, pk):
    package = get_object_or_404(
        RentalPackage.objects.select_related('user', 'approved_by').prefetch_related(
            'items__machine',
            'items__linked_rental',
        ),
        pk=pk,
    )
    can_manage_package = _package_management_access(request.user)
    if not can_manage_package and package.user_id != request.user.id:
        return HttpResponseForbidden('You do not have permission to view this rental package.')
    _sync_package_progress_from_rentals(package, save=True)
    package.refresh_payment_status(save=True)
    can_close_package = _can_close_package(package)
    can_edit_package = can_manage_package and _can_edit_package_schedule(package)

    if request.method == 'POST':
        action = (request.POST.get('action') or 'save').strip()
        if action == 'cancel_package':
            if can_manage_package or package.user_id != request.user.id:
                return HttpResponseForbidden('Only the package requester can cancel this package.')
            if not can_close_package:
                messages.error(request, 'This package can no longer be cancelled because work has already started or been completed.')
                return redirect('machines:rental_package_detail', pk=package.pk)
            _close_rental_package(package, acting_user=request.user, action_label='Cancelled')
            _notify_package_request_cancelled(package, notify_admins=True)
            messages.success(request, 'Package request cancelled successfully.')
            return redirect('machines:rental_package_detail', pk=package.pk)

        if action == 'reject_package':
            if not can_manage_package:
                return HttpResponseForbidden('Only administrators can reject rental packages.')
            if not can_close_package:
                messages.error(request, 'This package can no longer be rejected because work has already started or been completed.')
                return redirect('machines:rental_package_detail', pk=package.pk)
            _close_rental_package(package, acting_user=request.user, action_label='Rejected')
            _notify_package_request_rejected(package)
            messages.success(request, 'Package request rejected. Any reserved machine dates were released.')
            return redirect('machines:rental_package_detail', pk=package.pk)

        if not can_manage_package:
            return HttpResponseForbidden('Only administrators can manage rental package schedules.')
        if not can_edit_package:
            return HttpResponseForbidden('Cancelled, completed, or in-progress packages are read-only.')
        formset = RentalPackageItemScheduleFormSet(request.POST, instance=package)
        if formset.is_valid():
            action_parts = action.split(':', 1)
            action_name = action_parts[0]
            action_target = int(action_parts[1]) if len(action_parts) == 2 and action_parts[1].isdigit() else None
            try:
                with transaction.atomic():
                    package_auto_approved = False
                    items = formset.save()

                    if action_name == 'confirm_item' and action_target:
                        target_item = next((item for item in items if item.pk == action_target), None)
                        if not target_item:
                            messages.error(request, 'Unable to find the selected package item to confirm.')
                            return redirect('machines:rental_package_detail', pk=package.pk)
                        if not target_item.machine_id or not target_item.scheduled_start or not target_item.scheduled_end:
                            messages.error(request, f'Assign a machine and complete the schedule dates for {target_item.service_name} before confirming it.')
                            return redirect('machines:rental_package_detail', pk=package.pk)

                        target_item.is_tentative = False
                        if target_item.status in {'requested', 'tentative'}:
                            target_item.status = 'scheduled'
                        target_item.save()
                    elif action_name in {'preapprove', 'approve'}:
                        _promote_schedule_ready_package_items(items)

                    if package.approved_by_id or action_name in {'preapprove', 'approve', 'confirm_item'}:
                        approver = request.user if action_name in {'preapprove', 'approve', 'confirm_item'} else package.approved_by
                        _sync_package_items_to_rentals(package, approver)

                    package.refresh_total_amount(save=True)
                    package.refresh_payment_status(save=True)
                    if action_name != 'approve':
                        package_auto_approved = _auto_approve_rental_package_if_ready(package, request.user)

                    if action_name == 'confirm_item' and action_target:
                        target_item = next((item for item in items if item.pk == action_target), None)
                        _save_package_status(package, approver=package.approved_by, allow_full_approval=bool(package.approved_by_id))
                        success_message = (
                            f'Schedule confirmed for {target_item.service_name}. '
                            'The machine calendar and availability are now reserved for this package.'
                        )
                        if package_auto_approved:
                            success_message += ' The package was automatically approved because all service schedules are now confirmed.'
                        messages.success(request, success_message)
                    elif action_name == 'preapprove':
                        _save_package_status(package, approver=request.user, allow_full_approval=True)
                        package.refresh_total_amount(save=True)
                        success_message = (
                            'Package pre-approved. Confirmed schedule lines are now reserved, '
                            'while undecided services remain open for later scheduling.'
                        )
                        if package_auto_approved:
                            success_message = 'All service schedules are now confirmed, so the package was automatically approved.'
                        messages.success(request, success_message)
                    elif action_name == 'approve':
                        undecided_items = _undecided_package_items(package)
                        if undecided_items:
                            _save_package_status(package, approver=package.approved_by, allow_full_approval=bool(package.approved_by_id))
                            pending_labels = ', '.join(item.service_name for item in undecided_items)
                            messages.error(request, f'Cannot fully approve this package yet. Confirm schedules first for: {pending_labels}. You can use Pre-Approve while some services are still undecided.')
                            return redirect('machines:rental_package_detail', pk=package.pk)
                        _approve_rental_package(package, request.user)
                        _notify_package_request_approved(package)
                        messages.success(request, 'Rental package approved. All confirmed service schedules were converted into machine reservations.')
                    else:
                        _save_package_status(package, approver=package.approved_by, allow_full_approval=bool(package.approved_by_id))
                        success_message = 'Rental package schedule saved successfully.'
                        if package_auto_approved:
                            success_message += ' The package was automatically approved because all service schedules are now confirmed.'
                        messages.success(request, success_message)
                return redirect('machines:rental_package_detail', pk=package.pk)
            except ValidationError as exc:
                validation_messages = _package_validation_messages(exc)
                if action_name == 'confirm_item' and action_target:
                    target_form = next(
                        (form for form in formset.forms if getattr(form.instance, 'pk', None) == action_target),
                        None,
                    )
                    if target_form:
                        for validation_message in validation_messages:
                            target_form.add_error(None, validation_message)
                    else:
                        formset._non_form_errors = formset.error_class(validation_messages)
                else:
                    formset._non_form_errors = formset.error_class(validation_messages)
    else:
        formset = RentalPackageItemScheduleFormSet(instance=package)

    _sync_package_progress_from_rentals(package, save=True)
    package.refresh_payment_status(save=True)
    can_close_package = _can_close_package(package)
    can_edit_package = can_manage_package and _can_edit_package_schedule(package)
    _mark_package_notifications_as_read(request.user, package=package)
    if not can_manage_package and package.user_id == request.user.id:
        package.member_last_viewed_at = timezone.now()
        package.save(update_fields=['member_last_viewed_at'])
    package_items = list(
        package.items.select_related(
            'machine',
            'linked_rental',
            'linked_rental__assigned_operator',
        ).order_by('sequence_order', 'pk')
    )
    package_detail_url = reverse('machines:rental_package_detail', kwargs={'pk': package.pk})
    for item in package_items:
        if item.linked_rental_id:
            _annotate_package_linked_rental(
                item,
                can_manage_package=can_manage_package,
                package_detail_url=package_detail_url,
            )
    payment_summary = _build_package_payment_summary(
        package,
        items=package_items,
        can_manage_package=can_manage_package,
    )
    operator_candidates = []
    if can_manage_package:
        operator_candidates = User.objects.filter(
            is_active=True,
            role=User.OPERATOR,
        ).order_by('first_name', 'last_name', 'username')

    return render(request, 'machines/rental_package_detail.html', {
        'package': package,
        'items': package_items,
        'formset': formset,
        'can_manage_package': can_manage_package,
        'can_edit_package': can_edit_package,
        'can_cancel_package': (not can_manage_package and package.user_id == request.user.id and can_close_package),
        'can_reject_package': (can_manage_package and can_close_package),
        'equipment_rentals_url': _equipment_rentals_url_for_user(request.user),
        'package_payment_summary': payment_summary,
        'operator_candidates': operator_candidates,
        'package_detail_url': package_detail_url,
    })


@login_required
def set_package_rental_payment_method(request, rental_id):
    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user', 'package_item__rental_package'),
        pk=rental_id,
    )
    package_item = getattr(rental, 'package_item', None)
    if not package_item or not package_item.rental_package_id:
        messages.error(request, 'This rental is not linked to a package request.')
        return redirect('machines:rental_detail', pk=rental.pk)

    package = package_item.rental_package
    can_manage_package = _package_management_access(request.user)
    if not can_manage_package and package.user_id != request.user.id:
        return HttpResponseForbidden('You do not have permission to update this package rental.')

    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    if rental.payment_type != 'cash':
        messages.error(request, 'Only cash rentals can choose a payment method.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    payment_method = (request.POST.get('payment_method') or '').strip()
    if payment_method not in {'online', 'face_to_face'}:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    ready_for_payment = (
        rental.status == 'approved'
        and rental.workflow_state == 'ready_for_payment'
    )
    if not ready_for_payment:
        messages.error(request, 'This rental is not yet ready for payment.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    if payment_method == 'online' and not rental.machine.allow_online_payment:
        messages.error(request, 'This machine does not allow online payment.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    if payment_method == 'face_to_face' and not rental.machine.allow_face_to_face_payment:
        messages.error(request, 'This machine does not allow over-the-counter payment.')
        return redirect('machines:rental_package_detail', pk=package.pk)

    rental.payment_method = payment_method
    rental.workflow_state = 'ready_for_payment'
    rental.save(update_fields=['payment_method', 'workflow_state', 'updated_at'])

    if not package.payment_preference:
        package.payment_preference = payment_method
        package.save(update_fields=['payment_preference', 'updated_at'])

    messages.success(
        request,
        'Payment method updated. You can continue with payment from this package request.',
    )
    return redirect('machines:rental_package_detail', pk=package.pk)


# Machine Views

class MachineListView(LoginRequiredMixin, ListView):
    model = Machine
    template_name = 'machines/machine_list.html'
    context_object_name = 'machines'
    
    def get_queryset(self):
        """Return all machines excluding rice mills, filtered by search query or type if provided."""
        # Exclude rice mills from the machines list
        today = timezone.localdate()
        queryset = _machine_rental_queryset().prefetch_related(
            'images',
            Prefetch(
                'maintenance_records',
                queryset=_active_maintenance_records_queryset(),
                to_attr='active_maintenance_records',
            ),
        )
        active_rentals = Rental.objects.filter(
            machine=OuterRef('pk'),
        ).exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        ).filter(Rental.active_machine_use_q(today=today))
        queryset = queryset.annotate(is_currently_rented=Exists(active_rentals))
        
        # Filter by search query if provided
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Filter by machine type if provided
        machine_type = self.request.GET.get('type')
        if machine_type:
            queryset = queryset.filter(machine_type=machine_type)
            
        # Filter by availability if provided
        availability = self.request.GET.get('availability')
        if availability:
            maintenance_filter = Q(status='maintenance') | Q(maintenance_records__status__in=ACTIVE_MAINTENANCE_STATUSES)
            if availability == 'available':
                queryset = queryset.exclude(maintenance_filter).filter(is_currently_rented=False).distinct()
            elif availability == 'rented':
                queryset = queryset.filter(is_currently_rented=True)
            elif availability == 'maintenance':
                queryset = queryset.filter(maintenance_filter).distinct()
            else:
                queryset = queryset.filter(status=availability)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        machines = list(context['machines'])
        for machine in machines:
            active_maintenance_record = (
                machine.active_maintenance_records[0]
                if getattr(machine, 'active_maintenance_records', None)
                else None
            )
            if active_maintenance_record:
                machine.status = 'maintenance'
            elif getattr(machine, 'is_currently_rented', False):
                machine.status = 'rented'
            elif machine.status == 'maintenance':
                machine.status = 'available'
            machine.active_maintenance_record = active_maintenance_record
            machine.active_maintenance_issue = (
                _get_maintenance_issue_text(active_maintenance_record)
                if machine.status == 'maintenance'
                else ''
            )

        context['machines'] = machines
        context['object_list'] = machines
        today = timezone.localdate()
        active_rentals = Rental.objects.filter(
            machine=OuterRef('pk'),
        ).exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        ).filter(Rental.active_machine_use_q(today=today))
        base_queryset = _machine_rental_queryset().annotate(is_currently_rented=Exists(active_rentals))

        # Add permission checks to context
        context['can_create'] = self.request.user.has_perm('machines.add_machine')
        context['can_edit'] = self.request.user.has_perm('machines.change_machine')
        context['can_delete'] = self.request.user.has_perm('machines.delete_machine')
        context['can_rent'] = self.request.user.has_perm('machines.can_rent_machine')
        context['total_machines'] = base_queryset.count()
        maintenance_filter = Q(status='maintenance') | Q(maintenance_records__status__in=ACTIVE_MAINTENANCE_STATUSES)
        context['available_machines'] = base_queryset.exclude(maintenance_filter).filter(is_currently_rented=False).distinct().count()
        context['in_use_machines'] = base_queryset.filter(is_currently_rented=True).count()
        context['maintenance_machines'] = base_queryset.filter(maintenance_filter).distinct().count()
        context['machine_types'] = base_queryset.values('machine_type').distinct().count()
        context['machine_type_choices'] = [
            choice for choice in Machine._meta.get_field('machine_type').choices
            if choice[0] not in ['rice_mill', *Machine.DRYER_MACHINE_TYPES]
        ]
        context['selected_query'] = self.request.GET.get('q', '').strip()
        context['selected_type'] = self.request.GET.get('type', '').strip()
        context['selected_availability'] = self.request.GET.get('availability', '').strip()
        return context

class MachineDetailView(LoginRequiredMixin, DetailView):
    model = Machine
    template_name = 'machines/machine_detail.html'
    context_object_name = 'machine'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        machine = context['machine']
        context['machine_rent_preview_url'] = reverse(
            'machines:rent_machine',
            kwargs={'machine_pk': machine.pk},
        )
        
        # Get related data
        context['rentals'] = machine.rentals.select_related('user').all().order_by('-start_date')
        maintenance_records = list(machine.maintenance_records.all().order_by('-start_date'))
        context['maintenance_records'] = maintenance_records
        context['price_history'] = machine.price_history.all().order_by('-start_date')
        context['active_maintenance_record'] = _get_current_maintenance_record(
            machine,
            maintenance_records=maintenance_records,
        )
        context['active_maintenance_issue'] = _get_maintenance_issue_text(
            context['active_maintenance_record']
        )
        if context['active_maintenance_record']:
            machine.status = 'maintenance'
        elif machine.is_currently_rented():
            machine.status = 'rented'
        elif machine.status == 'maintenance':
            machine.status = 'available'
        
        # Get machine images (both from related MachineImage model and direct image field)
        context['images'] = [
            image for image in machine.images.all()
            if image.get_image_url()
        ]
        
        # Get similar machines based on machine type
        context['similar_machines'] = Machine.objects.filter(
            machine_type=machine.machine_type
        ).exclude(
            pk=machine.pk
        ).prefetch_related('images').order_by('-created_at')[:5]
        
        # Create calendar events data
        calendar_events = []
        
        # Add rental events
        for rental in context['rentals']:
            color = '#dc3545' if rental.status == 'approved' else '#ffc107'
            calendar_events.append({
                'title': 'Package Reserve' if _is_package_reserve_rental(rental) else 'Rented',
                'start': rental.start_date.strftime('%Y-%m-%d'),
                'end': rental.end_date.strftime('%Y-%m-%d'),
                'color': color
            })
        
        # Add maintenance events
        for record in context['maintenance_records']:
            if record.end_date:
                end_date = record.end_date.strftime('%Y-%m-%d')
            else:
                end_date = None
                
            calendar_events.append({
                'title': 'Maintenance',
                'start': record.start_date.strftime('%Y-%m-%d'),
                'end': end_date,
                'color': '#fd7e14'
            })
        
        # Add rice mill appointments if this is a rice mill
        if machine.is_rice_mill():
            appointments = machine.appointments.all().order_by('-appointment_date')
            context['appointments'] = appointments
            
            # Add appointment events to calendar
            for appointment in appointments:
                if appointment.status in RICE_MILL_LOCKED_STATUSES:
                    title = f"{appointment.display_time_range} - {appointment.customer_display_name}"
                    calendar_events.append({
                        'title': title,
                        'start': appointment.appointment_date.strftime('%Y-%m-%d'),
                        'allDay': True,
                        'color': '#007bff',
                        'range_label': appointment.display_time_range,
                        'start_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else '',
                        'end_time': appointment.end_time.strftime('%H:%M') if appointment.end_time else '',
                    })
        
        context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
        return context


class MachineRentPreviewView(LoginRequiredMixin, DetailView):
    model = Machine
    template_name = 'machines/machine_rent_preview.html'
    context_object_name = 'machine'
    pk_url_kwarg = 'machine_pk'

    def get_queryset(self):
        return _machine_rental_queryset().prefetch_related('images')

    def dispatch(self, request, *args, **kwargs):
        machine = self.get_object()

        if machine.is_dryer_service():
            messages.info(request, 'This dryer uses a separate dryer service process.')
            return redirect('machines:dryer_rental_create_for_machine', machine_id=machine.pk)

        if machine.machine_type == 'rice_mill':
            messages.info(request, 'Rice mill uses a separate milling appointment process.')
            return redirect('machines:ricemill_appointment_create_for_machine', machine_id=machine.pk)

        if machine.get_operational_status() == 'maintenance':
            messages.warning(request, 'This machine is currently under maintenance. Open the machine details to review the reported issue.')
            return redirect('machines:machine_detail', pk=machine.pk)

        user = request.user
        can_start_rental = (
            getattr(user, 'is_verified', False)
            or user.is_staff
            or user.is_superuser
            or user.has_perm('machines.can_rent_machine')
        )
        if not can_start_rental:
            messages.warning(request, 'You need a verified account before starting a rental request.')
            return redirect('machines:machine_detail', pk=machine.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        machine = self.get_object()
        currently_rented = machine.is_currently_rented()
        resolved_status = machine.get_operational_status()

        if resolved_status == 'maintenance':
            status_label = 'Under Maintenance'
            status_tone = 'danger'
        elif currently_rented:
            status_label = 'In Use Today'
            status_tone = 'warning'
        else:
            status_label = 'Available for Booking'
            status_tone = 'success'

        context['currently_rented'] = currently_rented
        context['status_label'] = status_label
        context['status_tone'] = status_tone
        context['confirm_rent_url'] = reverse('machines:rental_create_for_machine', kwargs={'machine_id': machine.pk})
        return context

class MachineCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Machine
    form_class = MachineForm
    template_name = 'machines/machine_form.html'
    success_url = reverse_lazy('machines:machine_list')
    permission_required = 'machines.add_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )

    def get_initial(self):
        initial = super().get_initial()
        requested_machine_type = self.request.GET.get('machine_type')
        requested_pricing_type = self.request.GET.get('dryer_pricing_type')

        if requested_machine_type in Machine.DRYER_MACHINE_TYPES:
            dryer_setup_defaults = _get_dryer_setup_defaults(requested_machine_type)
            initial.setdefault('machine_type', requested_machine_type)
            initial.setdefault('status', 'available')
            initial.setdefault('dryer_pricing_type', requested_pricing_type or dryer_setup_defaults['default_pricing_type'])
            initial.setdefault('pricing_unit', 'hour')

        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request)
        kwargs['hide_machine_type'] = kwargs['is_dryer_setup_flow']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request)
        context['show_machine_type_field'] = not context['is_dryer_setup_flow']
        selected_type = (
            self.request.POST.get('machine_type')
            or self.request.GET.get('machine_type')
            or context['form'].initial.get('machine_type')
        )
        context['dryer_type_is_locked'] = selected_type in Machine.DRYER_MACHINE_TYPES
        context['show_dryer_creation_form'] = (not context['is_dryer_setup_flow']) or context['dryer_type_is_locked']
        context['is_rice_mill_machine_form'] = _is_rice_mill_machine_form(self.request)
        context['skip_image_upload_step'] = context['is_dryer_setup_flow'] or context['is_rice_mill_machine_form']
        if context['is_dryer_setup_flow']:
            if context['dryer_type_is_locked']:
                context['dryer_setup_defaults'] = _get_dryer_setup_defaults(selected_type)
            else:
                context['dryer_setup_defaults'] = {
                    'machine_type': '',
                    'label': 'Dryer Unit',
                    'default_pricing_type': '',
                    'guidance': 'Choose a dryer type first, then continue with the setup and pricing details.',
                }
        
        # Add image formset
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = MachineImageFormSet(self.request.POST, self.request.FILES, prefix='form')
            else:
                context['formset'] = MachineImageFormSet(prefix='form')
            
        # Add machines for Services and Pricing section: both available and all with statuses
        available = Machine.objects.filter(status='available').order_by('name')
        context['available_machines'] = available
        context['all_machines'] = Machine.objects.all().order_by('name')
        return context

    def get_success_url(self):
        if self.object and self.object.is_dryer_service():
            return reverse('machines:dryer_rental_list')
        return str(self.success_url)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def _render_invalid_with_formset(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset),
            status=400,
        )
    
    def form_valid(self, form):
        """Handle form submission when form is valid"""
        skip_image_upload_step = (
            _is_dryer_setup_flow(self.request)
            or form.cleaned_data.get('machine_type') == 'rice_mill'
        )
        if skip_image_upload_step:
            self.object = form.save()
            if self.object.is_dryer_service():
                messages.success(self.request, 'Dryer unit added successfully. It is now available in Dryer Services based on its status.')
            else:
                messages.success(self.request, 'Machine created successfully.')
            return redirect(self.get_success_url())

        formset = MachineImageFormSet(
            self.request.POST,
            self.request.FILES,
            prefix='form',
        )
        if not formset.is_valid():
            messages.error(self.request, 'Please correct the image upload errors before saving the machine.')
            return self._render_invalid_with_formset(form, formset)

        uploaded_image_payloads = _get_uploaded_image_payloads(self.request)
        total_images = _count_active_formset_images(formset) + len(uploaded_image_payloads)
        if total_images > 3:
            form.add_error(None, 'You can only upload a maximum of 3 images per machine.')
            messages.error(self.request, 'Please reduce the number of machine images to 3 or fewer.')
            return self._render_invalid_with_formset(form, formset)

        try:
            with transaction.atomic():
                self.object = form.save()
                _save_machine_image_formset(formset, self.object, uploaded_image_payloads)
        except Exception as exc:
            messages.error(self.request, f'An error occurred while saving machine images: {exc}')
            return self._render_invalid_with_formset(form, formset)
        
        if self.object.is_dryer_service():
            messages.success(self.request, 'Dryer unit added successfully. It is now available in Dryer Services based on its status.')
        else:
            messages.success(self.request, 'Machine created successfully.')
        return redirect(self.get_success_url())

class MachineUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Machine
    form_class = MachineForm
    template_name = 'machines/machine_form.html'
    permission_required = 'machines.change_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request, self.object)
        context['is_rice_mill_machine_form'] = _is_rice_mill_machine_form(self.request, self.object)
        # Show machine_type field for regular machines, hide for dryer setup flow
        context['show_machine_type_field'] = not context['is_dryer_setup_flow']
        context['skip_image_upload_step'] = context['is_dryer_setup_flow'] or context['is_rice_mill_machine_form']
        if context['is_dryer_setup_flow']:
            context['dryer_setup_defaults'] = _get_dryer_setup_defaults(self.object.machine_type)
        
        # Add image formset
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = MachineImageFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form')
            else:
                context['formset'] = MachineImageFormSet(instance=self.object, prefix='form')
             
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request, self.object)
        # Only hide machine_type for dryer setup flow
        kwargs['hide_machine_type'] = kwargs['is_dryer_setup_flow']
        return kwargs
    
    def get_success_url(self):
        if self.object.is_dryer_service():
            return reverse('machines:dryer_rental_list')
        return reverse('machines:machine_detail', kwargs={'pk': self.object.pk})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def _render_invalid_with_formset(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset),
            status=400,
        )
    
    def form_valid(self, form):
        """Handle form submission when form is valid"""
        skip_image_upload_step = (
            _is_dryer_setup_flow(self.request, self.object)
            or _is_rice_mill_machine_form(self.request, self.object)
        )
        if skip_image_upload_step:
            self.object = form.save()
            if self.object.is_dryer_service():
                messages.success(self.request, 'Dryer unit updated successfully. Member and admin dryer bookings will use the saved pricing setup.')
            else:
                messages.success(self.request, 'Machine updated successfully.')
            return redirect(self.get_success_url())

        formset = MachineImageFormSet(
            self.request.POST,
            self.request.FILES,
            instance=self.object,
            prefix='form',
        )
        if not formset.is_valid():
            messages.error(self.request, 'Please correct the errors in the image section.')
            return self._render_invalid_with_formset(form, formset)

        uploaded_image_payloads = _get_uploaded_image_payloads(self.request)
        total_images = _count_active_formset_images(formset) + len(uploaded_image_payloads)
        if total_images > 3:
            form.add_error(None, 'You can only upload a maximum of 3 images per machine.')
            messages.error(self.request, 'Please reduce the number of machine images to 3 or fewer.')
            return self._render_invalid_with_formset(form, formset)

        try:
            with transaction.atomic():
                self.object = form.save()
                _save_machine_image_formset(formset, self.object, uploaded_image_payloads)
        except Exception as exc:
            messages.error(self.request, f'An error occurred while saving images: {exc}')
            return self._render_invalid_with_formset(form, formset)

        if self.object.is_dryer_service():
            messages.success(self.request, 'Dryer unit updated successfully. Member and admin dryer bookings will use the saved pricing setup.')
        else:
            messages.success(self.request, 'Machine updated successfully.')
        return redirect(self.get_success_url())


class RiceMillPricingUpdateView(MachineUpdateView):
    permission_required = 'machines.change_machine'

    def get_object(self, queryset=None):
        return _ensure_default_rice_mill()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['is_ricemill_pricing_flow'] = True
        return context

    def get_success_url(self):
        return reverse('machines:ricemill_appointment_list')

    def form_valid(self, form):
        self.object = form.save()
        _sync_ricemill_appointment_pricing(self.object)
        messages.success(self.request, 'Rice mill pricing updated successfully.')
        return redirect(self.get_success_url())

@login_required
def machine_delete_view(request, pk):
    """Simple function-based view for deleting machines"""
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser or 
            request.user.has_perm('machines.delete_machine')):
        messages.error(request, "You don't have permission to delete machines.")
        return redirect('machines:machine_list')
    
    machine = get_object_or_404(Machine, pk=pk)
    is_dryer_setup_flow = machine.is_dryer_service()
    cancel_url = reverse('machines:dryer_rental_list') if is_dryer_setup_flow else reverse('machines:machine_list')
    detail_url = (
        reverse('machines:edit_machine', kwargs={'pk': machine.pk}) + '?service=dryer'
        if is_dryer_setup_flow
        else reverse('machines:machine_detail', kwargs={'pk': machine.pk})
    )

    delete_context = {
        'machine': machine,
        'is_dryer_setup_flow': is_dryer_setup_flow,
        'cancel_url': cancel_url,
        'detail_url': detail_url,
    }
    
    if request.method == 'POST':
        confirmation_text = (request.POST.get('delete_confirmation') or '').strip()
        if confirmation_text != 'CONFIRM':
            messages.error(request, 'Type CONFIRM before deleting this item.')
            return render(request, 'machines/machine_confirm_delete.html', delete_context, status=400)

        # Delete the machine
        machine_name = machine.name
        machine.delete()
        messages.success(request, f'Machine "{machine_name}" has been deleted successfully.')
        return redirect(cancel_url)
    
    # GET request - show confirmation page
    return render(request, 'machines/machine_confirm_delete.html', delete_context)


# Keep the class-based view as backup
class MachineDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Machine
    template_name = 'machines/machine_confirm_delete.html'
    success_url = reverse_lazy('machines:machine_list')
    permission_required = 'machines.delete_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )
    
    def post(self, request, *args, **kwargs):
        """Handle POST request for deletion"""
        machine = self.get_object()
        machine_name = machine.name
        success_url = reverse('machines:dryer_rental_list') if machine.is_dryer_service() else reverse('machines:machine_list')

        confirmation_text = (request.POST.get('delete_confirmation') or '').strip()
        if confirmation_text != 'CONFIRM':
            messages.error(request, 'Type CONFIRM before deleting this item.')
            context = self.get_context_data(
                object=machine,
                machine=machine,
                is_dryer_setup_flow=machine.is_dryer_service(),
                cancel_url=success_url,
                detail_url=(
                    reverse('machines:edit_machine', kwargs={'pk': machine.pk}) + '?service=dryer'
                    if machine.is_dryer_service()
                    else reverse('machines:machine_detail', kwargs={'pk': machine.pk})
                ),
            )
            return self.render_to_response(context, status=400)

        machine.delete()
        messages.success(request, f'Machine "{machine_name}" has been deleted successfully.')
        return redirect(success_url)

# Rental Views

class RentalListView(LoginRequiredMixin, ListView):
    model = Rental
    template_name = 'machines/rental_list_organized.html'
    context_object_name = 'rentals'
    
    def get_queryset(self):
        """
        Return rentals based on user permissions:
        - Regular users see only their own rentals
        - Staff members can see all rentals
        """
        user = self.request.user
        if user.is_staff or user.has_perm('machines.can_view_all_rentals'):
            return Rental.objects.all()
        else:
            return Rental.objects.filter(user=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_approve'] = self.request.user.has_perm('machines.can_approve_rentals')
        return context

    def get(self, request, *args, **kwargs):
        return redirect('machines:rental_list')

class RentalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Rental
    template_name = 'machines/rental_confirmation.html'
    context_object_name = 'rental'
    
    def test_func(self):
        """
        Ensure users can only view their own rentals unless they have
        permission to view all rentals
        """
        rental = self.get_object()
        user = self.request.user
        return (user == rental.user or 
                user.is_staff or 
                user.has_perm('machines.can_view_all_rentals'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rental = self.get_object()
        user = self.request.user
        
        # Check if user can modify this rental
        context['can_modify'] = (
            rental.can_be_modified() and
            (user == rental.user or user.is_staff)
        )
        
        # Check if user can approve/reject this rental
        context['can_approve'] = user.has_perm('machines.can_approve_rentals')
        
        return context

    def get(self, request, *args, **kwargs):
        rental = self.get_object()
        return redirect('machines:rental_confirmation', pk=rental.pk)

class RentalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Rental
    form_class = RentalForm
    template_name = 'machines/rental_form_enhanced.html'
    permission_required = 'machines.can_rent_machine'
    
    def has_permission(self):
        # Allow verified users or staff to rent machines
        user = self.request.user
        return (user.is_verified or 
                user.is_staff or 
                user.is_superuser or
                user.has_perm('machines.can_rent_machine'))
    
    def get_initial(self):
        initial = super().get_initial()
        if 'machine_pk' in self.kwargs:
            initial['machine'] = self.kwargs['machine_pk']
        return initial

    def dispatch(self, request, *args, **kwargs):
        machine_id = kwargs.get('machine_pk') or kwargs.get('machine_id')
        if machine_id:
            machine = get_object_or_404(Machine, pk=machine_id)
            if machine.is_dryer_service():
                messages.info(request, 'This dryer uses a separate dryer service process.')
                return redirect('machines:dryer_rental_create_for_machine', machine_id=machine.pk)
            if machine.machine_type == 'rice_mill':
                messages.info(request, 'Rice mill uses a separate milling appointment process.')
                return redirect('machines:ricemill_appointment_create_for_machine', machine_id=machine.pk)
            if machine.get_operational_status() == 'maintenance':
                messages.warning(request, 'This machine is currently under maintenance. Open the machine details to review the reported issue.')
                return redirect('machines:machine_detail', pk=machine.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass user to form for autofilling personal details
        kwargs['user'] = self.request.user
        if 'machine_pk' in self.kwargs:
            kwargs['machine_id'] = self.kwargs['machine_pk']
        elif 'machine_id' in self.kwargs: 
            kwargs['machine_id'] = self.kwargs['machine_id']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        
        # Add machine details if specified
        if 'machine_pk' in self.kwargs:
            try:
                machine = _machine_rental_queryset().get(pk=self.kwargs['machine_pk'])
                context['machine'] = machine
            except Machine.DoesNotExist:
                pass
        elif 'machine_id' in self.kwargs:
            try:
                machine = _machine_rental_queryset().get(pk=self.kwargs['machine_id'])
                context['machine'] = machine
            except Machine.DoesNotExist:
                pass
        
        # Add all machines for the service type dropdown
        selectable_machines = context['form'].fields['machine'].queryset
        context['available_machines'] = selectable_machines.filter(status='available')
        context['all_machines'] = selectable_machines
        
        # Prepare machine data for JavaScript
        machines_data = []
        for m in selectable_machines:
            pricing = m.get_pricing_info()
            machines_data.append({
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'machine_type': m.machine_type,
                'type': m.get_machine_type_display(),
                'price': m.current_price,
                'pricing_rate': float(pricing.get('rate') or 0),
                'pricing_unit': pricing.get('unit') or '',
                'rate_display': m.get_rate_display(),
                'payment_summary': m.get_payment_summary(),
                'settlement_label': 'After harvest' if m.rental_price_type == 'in_kind' else 'Upon approval',
                'rental_price_type': m.rental_price_type,
                'allow_online_payment': m.allow_online_payment,
                'allow_face_to_face_payment': m.allow_face_to_face_payment,
                'settlement_type': m.settlement_type,
                'in_kind_farmer_share': m.in_kind_farmer_share,
                'in_kind_organization_share': m.in_kind_organization_share,
                'image': m.get_display_image_url() if m.get_display_image_url() else None,
            })
        context['machines_json'] = json.dumps(machines_data)
                
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if trying to rent a rice mill machine and redirect appropriately
        if 'machine_pk' in kwargs:
            try:
                machine = Machine.objects.get(pk=kwargs['machine_pk'])
                if machine.is_rice_mill():
                    messages.info(request, 'Rice mill machines require scheduling an appointment instead of regular rental.')
                    return redirect('machines:ricemill_appointment_create', machine_pk=machine.pk)
            except Machine.DoesNotExist:
                pass
                
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.apply_booking_identity(form.instance)
        if not form.instance.user_id:
            form.instance.user = self.request.user
        form.instance.payment_amount = form.instance.calculate_payment_amount()
        pending_conflict_count = form.pending_conflicts.count() if hasattr(form, 'pending_conflicts') else 0
        
        # Get payment method from form
        payment_method = form.cleaned_data.get('payment_method')
        if payment_method:
            form.instance.payment_method = payment_method
        
        # Auto-approve request if admin is creating it
        if self.request.user.is_staff or self.request.user.is_superuser:
            form.instance.status = 'approved'
            form.instance.workflow_state = 'approved'
            if form.instance.payment_type != 'in_kind':
                # Only set payment_method to face_to_face if not already set
                if not form.instance.payment_method:
                    form.instance.payment_method = 'face_to_face'
                form.instance.payment_status = 'pending'
            messages.success(self.request, 'Rental request automatically approved.')
        else:
            # Show success message for regular users
            messages.success(
                self.request, 
                f'Rental request submitted successfully! Your request for {form.instance.machine.name} '
                f'is now pending admin approval. You will be notified once it is reviewed.'
            )

        if pending_conflict_count:
            messages.warning(
                self.request,
                'This rental overlaps with an existing pending request. It was still submitted, but availability may change during admin review.'
            )
        
        # Save the object first to get the ID (this will trigger the signal to create notifications)
        self.object = form.save()
        
        if self.object.payment_type == 'cash':
            # Create Payment object only for cash rentals
            from django.contrib.contenttypes.models import ContentType
            from bufia.models import Payment
            
            content_type = ContentType.objects.get_for_model(self.object)
            Payment.objects.get_or_create(
                content_type=content_type,
                object_id=self.object.id,
                defaults={
                    'user': form.instance.user,
                    'payment_type': 'rental',
                    'amount': self.object.payment_amount or 0,
                    'currency': 'PHP',
                    'status': 'pending',
                }
            )
        
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Notify user on date conflicts
        error_text = str(form.errors) + " " + " ".join(e for e in form.non_field_errors())
        if 'already rented' in error_text.lower() or 'already booked' in error_text.lower():
            messages.error(self.request, 'This machine is already rented for the selected dates. Please rent this on another day.')
            try:
                machine_name = None
                try:
                    m = form.cleaned_data.get('machine') if hasattr(form, 'cleaned_data') else None
                    if m:
                        machine_name = getattr(m, 'name', None)
                except Exception:
                    pass
                # Try to get dates from POST
                start_date = self.request.POST.get('start_date')
                end_date = self.request.POST.get('end_date')
                msg = 'This machine is already rented for the selected dates. Please rent this on another day.'
                if machine_name:
                    if start_date and end_date:
                        msg = f'{machine_name} is already rented from {start_date} to {end_date}. Please rent this on another day.'
                    else:
                        msg = f'{machine_name} is already rented for the selected dates. Please rent this on another day.'
                UserNotification.objects.create(
                    user=self.request.user,
                    notification_type='rental_conflict',
                    message=msg
                )

                # Broadcast to other verified members (prefer same sector)
                try:
                    User = get_user_model()
                    requester_sector = None
                    try:
                        requester_sector = getattr(getattr(self.request.user, 'membership_application', None), 'assigned_sector', None)
                    except Exception:
                        requester_sector = None

                    if requester_sector:
                        recipients = User.objects.filter(is_verified=True, membership_application__assigned_sector=requester_sector)
                    else:
                        recipients = User.objects.filter(is_verified=True)
                    recipients = recipients.exclude(pk=self.request.user.pk).exclude(role='operator')

                    broadcast_msg = msg
                    for member in recipients:
                        UserNotification.objects.create(
                            user=member,
                            notification_type='rental_conflict_broadcast',
                            message=broadcast_msg
                        )
                except Exception as e:
                    print(f'Failed to broadcast rental conflict notification: {e}')
            except Exception as e:
                print(f'Failed to create rental conflict notification: {e}')
        return super().form_invalid(form)
    
    def get_success_url(self):
        # Staff-created rentals should continue in the admin approval workflow.
        if self.request.user.is_staff or self.request.user.is_superuser:
            return reverse('machines:admin_approve_rental', kwargs={'rental_id': self.object.pk})

        # Redirect regular renters to their confirmation page
        return reverse('machines:rental_confirmation', kwargs={'pk': self.object.pk})

class RentalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Rental
    form_class = RentalForm
    template_name = 'machines/rental_form_enhanced.html'
    
    def test_func(self):
        """Ensure users can only edit their own rentals that are in editable status"""
        rental = self.get_object()
        user = self.request.user
        return (rental.can_be_modified() and 
                (user == rental.user or user.is_staff) and
                user.has_perm('machines.can_rent_machine'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        selectable_machines = context['form'].fields['machine'].queryset
        context['available_machines'] = selectable_machines.filter(status='available')
        context['all_machines'] = selectable_machines
        return context
    
    def get_success_url(self):
        return reverse('machines:rental_confirmation', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # If status was already approved, set it back to pending
        if self.get_object().status == 'approved' and not self.request.user.is_staff:
            form.instance.status = 'pending'
            messages.info(self.request, 'Your rental has been updated and will require re-approval.')
        else:
            messages.success(self.request, 'Rental updated successfully!')
        
        return super().form_valid(form)

class RentalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Rental
    template_name = 'machines/rental_confirm_delete.html'
    success_url = reverse_lazy('machines:rental_list')
    
    def test_func(self):
        """Ensure users can only delete their own rentals that are in deletable status"""
        rental = self.get_object()
        user = self.request.user
        return (rental.can_be_cancelled() and 
                (user == rental.user or user.is_staff))
    
    def form_valid(self, form):
        rental = self.get_object()
        rental.mark_cancelled(
            cancellation_type='customer' if self.request.user == rental.user else 'admin',
            cancel_reason='Cancelled by customer.' if self.request.user == rental.user else 'Cancelled by admin.',
            system_note='Rental slot released after manual cancellation.',
        )
        rental.save(update_fields=[
            'status',
            'workflow_state',
            'cancellation_type',
            'cancel_reason',
            'system_note',
            'updated_at',
        ])
        rental.sync_machine_status()
        messages.success(self.request, 'Rental cancelled successfully!')
        return redirect(self.success_url)


@login_required
def request_rental_follow_up(request, pk):
    rental = get_object_or_404(Rental, pk=pk, user=request.user)

    if request.method != 'POST':
        return redirect('machines:rental_confirmation', pk=rental.pk)

    action = (request.POST.get('follow_up_action') or '').strip()
    if action not in {'refund_requested', 'reschedule_requested'}:
        messages.error(request, 'Please choose a valid follow-up action.')
        return redirect('machines:rental_confirmation', pk=rental.pk)

    if action == 'refund_requested' and not rental.can_request_refund:
        messages.warning(request, 'Refund requests are only available for cancelled rentals with recorded payments.')
        return redirect('machines:rental_confirmation', pk=rental.pk)

    if action == 'reschedule_requested' and not rental.can_request_reschedule:
        messages.warning(request, 'This rental is not available for reschedule follow-up right now.')
        return redirect('machines:rental_confirmation', pk=rental.pk)

    rental.follow_up_action = action
    rental.follow_up_requested_at = timezone.now()
    rental.save(update_fields=['follow_up_action', 'follow_up_requested_at', 'updated_at'])

    action_label = 'refund' if action == 'refund_requested' else 'reschedule'
    admins = get_user_model().objects.filter(is_staff=True, is_active=True).exclude(role='operator')
    for admin in admins:
        UserNotification.objects.create(
            user=admin,
            notification_type='rental_update',
            message=(
                f'{rental.customer_display_name} requested a {action_label} for the cancelled '
                f'rental of {rental.machine.name} from {rental.start_date:%B %d, %Y} to {rental.end_date:%B %d, %Y}.'
            ),
            related_object_id=rental.id,
        )

    messages.success(
        request,
        f'Your {action_label} request was sent to BUFIA admin. They can now review and process it.'
    )
    return redirect('machines:rental_confirmation', pk=rental.pk)

# Rice Mill Appointment Views
class RiceMillAppointmentListView(LoginRequiredMixin, ListView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_list.html'
    context_object_name = 'appointments'
    
    def get_queryset(self):
        queryset = RiceMillAppointment.objects.all()
        
        # Filter by user if not admin/staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Apply filters if present
        status_filter = self.request.GET.get('status')
        date_filter = self.request.GET.get('date')
        booking_source_filter = self.request.GET.get('booking_source')
        
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        if self.request.user.is_staff and booking_source_filter and booking_source_filter != 'all':
            queryset = queryset.filter(booking_source=booking_source_filter)
        
        if date_filter:
            try:
                date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date=date_obj)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = list(context['appointments'])
        payment_map = _get_appointment_payment_map(appointments)

        for appointment in appointments:
            payment = payment_map.get(appointment.id)
            payment_completed = bool(payment and payment.status == 'completed')
            appointment.payment_record = payment
            appointment.can_pay_now = (
                self.request.user == appointment.user
                and appointment.payment_method == 'online'
                and appointment.final_weight is not None
                and appointment.status not in {'confirmed', 'completed', 'rejected', 'cancelled'}
                and not payment_completed
            )

            if appointment.status == 'pending':
                appointment.queue_status_label = 'Pending'
                appointment.queue_status_variant = 'pending'
            elif appointment.status == 'approved' and appointment.final_weight is None:
                appointment.queue_status_label = 'Approved'
                appointment.queue_status_variant = 'approved'
            elif appointment.payment_method == 'online' and appointment.final_weight is not None and not payment_completed:
                appointment.queue_status_label = 'Ready to Pay'
                appointment.queue_status_variant = 'payment-due'
            elif appointment.payment_method in [None, 'face_to_face'] and appointment.final_weight is not None and appointment.status not in {'confirmed', 'completed'}:
                appointment.queue_status_label = 'Waiting for Payment'
                appointment.queue_status_variant = 'payment-due'
            elif appointment.status == 'paid' and payment_completed:
                appointment.queue_status_label = 'Paid'
                appointment.queue_status_variant = 'paid'
            elif appointment.status == 'confirmed':
                appointment.queue_status_label = 'Confirmed'
                appointment.queue_status_variant = 'confirmed'
            elif appointment.status == 'completed':
                appointment.queue_status_label = 'Completed'
                appointment.queue_status_variant = 'completed'
            elif appointment.status == 'rejected':
                appointment.queue_status_label = 'Rejected'
                appointment.queue_status_variant = 'rejected'
            else:
                appointment.queue_status_label = appointment.get_status_display()
                appointment.queue_status_variant = 'neutral'

        context['rice_mill_machine'] = Machine.objects.filter(machine_type='rice_mill').order_by('name', 'pk').first()
        context['appointments'] = appointments
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['date_filter'] = self.request.GET.get('date', '')
        context['booking_source_filter'] = self.request.GET.get('booking_source', 'all')
        context['booking_source_options'] = [
            ('all', 'All Milling Sources'),
            (RiceMillAppointment.BOOKING_SOURCE_MEMBER, 'Member Milling'),
            (RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER, 'Non-member Milling'),
            (RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE, 'BUFIA Rice Share'),
        ]
        context['pending_count'] = sum(1 for appointment in appointments if appointment.status == 'pending')
        context['approved_count'] = sum(1 for appointment in appointments if appointment.status == 'approved')
        context['paid_count'] = sum(1 for appointment in appointments if appointment.status == 'paid')
        context['confirmed_count'] = sum(1 for appointment in appointments if appointment.status == 'confirmed')
        context['completed_count'] = sum(1 for appointment in appointments if appointment.status == 'completed')
        return context

class RiceMillAppointmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_detail.html'
    context_object_name = 'appointment'
    
    def test_func(self):
        # Only allow users to view their own appointments or staff to view any
        appointment = self.get_object()
        return self.request.user.is_staff or self.request.user == appointment.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.get_object()
        
        # Add machine details
        context['machine_details'] = {
            'name': appointment.machine.name,
            'description': appointment.machine.description,
            'rental_fee': appointment.machine.current_price,
        }
        
        # Check if the appointment can be modified
        context['can_modify'] = appointment.can_be_modified()
        context['can_cancel'] = appointment.can_be_cancelled()
        
        payment = _get_appointment_payment(appointment)
        payment_completed = bool(payment and payment.status == 'completed')
        context['payment'] = payment
        context['transaction_id'] = payment.internal_transaction_id if payment else appointment.get_transaction_id()
        context['total_amount'] = appointment.computed_total_amount
        context['milling_amount'] = appointment.computed_milling_amount
        context['tahop_total_amount'] = appointment.computed_tahop_total_amount
        context['over_counter_suggestions'] = [
            appointment.computed_total_amount,
            Decimal('500.00'),
            Decimal('1000.00'),
            Decimal('1500.00'),
            Decimal('2000.00'),
        ]
        context['price_per_kg'] = appointment.effective_price_per_kg
        context['estimated_weight'] = appointment.estimated_weight
        context['selected_payment_method_label'] = appointment.get_payment_method_display() if appointment.payment_method else 'Not selected yet'
        context['booking_source_label'] = appointment.get_booking_source_display()
        context['appointment_payment_completed'] = payment_completed
        context['awaiting_face_to_face'] = (
            appointment.status == 'approved'
            and appointment.payment_method in [None, 'face_to_face']
            and appointment.final_weight is None
        )
        context['awaiting_online_payment_setup'] = (
            appointment.status == 'approved'
            and appointment.payment_method == 'online'
            and appointment.final_weight is None
        )
        context['awaiting_online_payment_completion'] = (
            appointment.payment_method == 'online'
            and appointment.final_weight is not None
            and appointment.status not in {'confirmed', 'completed', 'rejected', 'cancelled'}
            and not payment_completed
        )
        context['awaiting_counter_payment_confirmation'] = (
            appointment.payment_method in [None, 'face_to_face']
            and appointment.final_weight is not None
            and appointment.status not in {'confirmed', 'completed', 'rejected', 'cancelled'}
            and not payment_completed
        )
        context['can_launch_online_payment'] = (
            self.request.user == appointment.user
            and appointment.payment_method == 'online'
            and appointment.final_weight is not None
            and appointment.status not in {'confirmed', 'completed', 'rejected', 'cancelled'}
            and not payment_completed
        )
        context['can_admin_record_weight'] = (
            self.request.user.is_staff
            and appointment.status == 'approved'
            and appointment.payment_method in [None, 'face_to_face', 'online']
        )
        context['can_admin_confirm_payment'] = (
            self.request.user.is_staff
            and appointment.final_weight is not None
            and appointment.status not in {'pending', 'confirmed', 'completed', 'rejected', 'cancelled'}
            and (
                appointment.payment_method in [None, 'face_to_face']
                or (appointment.payment_method == 'online' and payment_completed)
            )
        )
        context['can_admin_mark_completed'] = (
            self.request.user.is_staff and appointment.status == 'confirmed'
        )
        
        return context

class RiceMillAppointmentCreateView(LoginRequiredMixin, CreateView):
    model = RiceMillAppointment
    form_class = RiceMillAppointmentForm
    template_name = 'machines/ricemill_appointment_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check verification status before processing the view"""
        if not request.user.is_verified:
            if not request.user.is_superuser:
                messages.warning(
                    request,
                    "Your membership requires verification before you can schedule appointments. "
                    "Please complete your profile and submit the membership form."
                )
                return redirect('profile')
        if not self.kwargs.get('machine_id'):
            _ensure_default_rice_mill()
        return super().dispatch(request, *args, **kwargs)
        
    def get_initial(self):
        initial = super().get_initial()
        # Pre-populate machine if provided in URL
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            initial['machine'] = machine_id
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the machine_id to the form if it exists in the URL
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            kwargs['machine_id'] = machine_id
        # Pass the current user to the form
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        
        # Get the rice mill machine for calendar display
        form = context.get('form')
        rice_mill = None

        if form is not None and hasattr(form, 'cleaned_data'):
            rice_mill = form.cleaned_data.get('machine')

        if not rice_mill and form is not None:
            instance = getattr(form, 'instance', None)
            if getattr(instance, 'machine_id', None):
                rice_mill = instance.machine

        if not rice_mill and form is not None:
            rice_mill = getattr(form, '_selected_machine', None)

        if not rice_mill:
            rice_mill = Machine.objects.filter(
                pk=self.kwargs.get('machine_id'),
                machine_type='rice_mill'
            ).first()
        if not rice_mill:
            rice_mill = Machine.objects.filter(machine_type='rice_mill', status='available').first() or _ensure_default_rice_mill()
        if not rice_mill:
            rice_mill = Machine.objects.filter(machine_type='rice_mill').first() or _ensure_default_rice_mill()
        if rice_mill:
            context['machine'] = rice_mill
            machine = rice_mill
            
            # Add calendar data for the rice mill
            # Get existing appointments for this machine
            appointments = RiceMillAppointment.objects.filter(
                machine=machine,
                status__in=RICE_MILL_LOCKED_STATUSES
            )
            
            # Group appointments by date to count them
            from collections import defaultdict
            appointments_by_date = defaultdict(list)
            for appointment in appointments:
                date_key = appointment.appointment_date.strftime('%Y-%m-%d')
                appointments_by_date[date_key].append(appointment)
            
            # Format for calendar
            calendar_events = []
            for date_key, date_appointments in appointments_by_date.items():
                # Count appointments by status
                total_count = len(date_appointments)
                completed_count = sum(1 for apt in date_appointments if apt.status == 'completed')
                ongoing_count = total_count - completed_count
                
                # Determine overall status
                if completed_count == total_count:
                    overall_status = 'All Finished'
                    color = '#28a745'  # Green
                elif completed_count > 0:
                    overall_status = f'{completed_count} Finished, {ongoing_count} Ongoing'
                    color = '#ffc107'  # Yellow
                else:
                    overall_status = 'All Ongoing'
                    color = '#007bff'  # Blue
                
                # Get customer names
                customer_names = [apt.customer_display_name for apt in date_appointments]
                customers_text = ', '.join(customer_names[:3])
                if len(customer_names) > 3:
                    customers_text += f' +{len(customer_names) - 3} more'
                
                title = f"{total_count} Appointment{'s' if total_count > 1 else ''} - {overall_status}"
                
                calendar_events.append({
                    'title': title,
                    'start': date_key,
                    'allDay': True,
                    'color': color,
                    'booked_by': customers_text,
                    'status': overall_status,
                    'status_label': overall_status,
                    'appointment_count': total_count,
                    'completed_count': completed_count,
                    'ongoing_count': ongoing_count,
                    'customer_names': customer_names,
                })
            
            # Also add maintenance and rentals
            maintenance_records = Maintenance.objects.filter(
                machine=machine,
                status__in=['scheduled', 'in_progress']
            )
            
            rentals = Rental.objects.filter(
                machine=machine,
                status='approved'
            )
            
            for record in maintenance_records:
                if record.end_date:
                    end_date = record.end_date.strftime('%Y-%m-%d')
                else:
                    end_date = None
                    
                calendar_events.append({
                    'title': 'Maintenance',
                    'start': record.start_date.strftime('%Y-%m-%d'),
                    'end': end_date,
                    'color': '#fd7e14'
                })
            
            for rental in rentals:
                calendar_events.append({
                    'title': 'Rented',
                    'start': rental.start_date.strftime('%Y-%m-%d'),
                    'end': rental.end_date.strftime('%Y-%m-%d'),
                    'color': '#dc3545'
                })
            
            context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
                
        return context
    
    def form_valid(self, form):
        form.apply_booking_identity(form.instance)
        if not form.instance.user_id:
            form.instance.user = self.request.user
        
        form.instance.status = 'pending'
        appointment = form.save(commit=False)
        
        # Ensure machine is set from cleaned_data
        if not appointment.machine_id:
            appointment.machine = (
                form.cleaned_data.get('machine')
                or Machine.objects.filter(
                    pk=self.kwargs.get('machine_id'),
                    machine_type='rice_mill'
                ).first()
                or Machine.objects.filter(machine_type='rice_mill', status='available').first()
                or Machine.objects.filter(machine_type='rice_mill').first()
                or _ensure_default_rice_mill()
            )
        if not appointment.machine_id:
            form.add_error(None, 'No rice mill is configured yet. Please contact the administrator.')
            return self.form_invalid(form)

        try:
            appointment.save()
        except IntegrityError:
            form.add_error(
                None,
                'That rice mill schedule could not be saved. Please choose another date and try again.'
            )
            return self.form_invalid(form)
        
        # Store the appointment ID for redirect
        self.object = appointment
        
        messages.success(self.request, 'Appointment created successfully and is now waiting for admin approval.')
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.object.pk})

class RiceMillAppointmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RiceMillAppointment
    form_class = RiceMillAppointmentForm
    template_name = 'machines/ricemill_appointment_form.html'
    
    def test_func(self):
        # Only allow users to update their own appointments that are still pending or approved
        appointment = self.get_object()
        if not appointment.can_be_modified():
            return False
        return self.request.user == appointment.user or self.request.user.is_staff

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['machine_id'] = self.get_object().machine_id
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        
        # Add calendar data for the selected machine
        appointment = self.get_object()
        machine = appointment.machine
        context['machine'] = machine
        
        # Get existing appointments for this machine
        appointments = RiceMillAppointment.objects.filter(
            machine=machine,
            status__in=RICE_MILL_LOCKED_STATUSES
        ).exclude(pk=appointment.pk)
        
        # Format for calendar
        calendar_events = []
        for other_appointment in appointments:
            title = f"{other_appointment.customer_display_name} - {other_appointment.display_time_range}"
            color = '#007bff'
            
            calendar_events.append({
                'title': title,
                'start': other_appointment.appointment_date.strftime('%Y-%m-%d'),
                'allDay': True,
                'color': color,
                'range_label': other_appointment.display_time_range,
                'start_time': other_appointment.start_time.strftime('%H:%M') if other_appointment.start_time else '',
                'end_time': other_appointment.end_time.strftime('%H:%M') if other_appointment.end_time else '',
                'booked_by': other_appointment.customer_display_name,
                'status': other_appointment.status,
                'status_label': other_appointment.get_status_display(),
            })
        
        # Also add maintenance and rentals
        maintenance_records = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress']
        )
        
        rentals = Rental.objects.filter(
            machine=machine,
            status='approved'
        )
        
        for record in maintenance_records:
            if record.end_date:
                end_date = record.end_date.strftime('%Y-%m-%d')
            else:
                end_date = None
                
            calendar_events.append({
                'title': 'Maintenance',
                'start': record.start_date.strftime('%Y-%m-%d'),
                'end': end_date,
                'color': '#fd7e14'
            })
        
        for rental in rentals:
            calendar_events.append({
                'title': 'Rented',
                'start': rental.start_date.strftime('%Y-%m-%d'),
                'end': rental.end_date.strftime('%Y-%m-%d'),
                'color': '#dc3545'
            })
        
        context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
        return context
    
    def form_valid(self, form):
        form.instance.status = 'pending'
        messages.info(self.request, 'Your appointment has been updated and is waiting for admin approval again.')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.object.pk})

class RiceMillAppointmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_confirm_delete.html'
    success_url = reverse_lazy('machines:ricemill_appointment_list')
    
    def test_func(self):
        # Only allow users to delete their own appointments that can be cancelled
        appointment = self.get_object()
        if not appointment.can_be_cancelled():
            return False
        return self.request.user == appointment.user or self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        appointment = self.get_object()
        success_message = f'Appointment for {appointment.appointment_date} has been cancelled.'
        messages.success(self.request, success_message)
        return super().delete(request, *args, **kwargs)

@login_required
def approve_appointment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to approve appointments.")
    
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    if request.method == 'POST':
        conflict_exists = False
        if appointment.start_time and appointment.end_time:
            conflict_exists = RiceMillAppointment.objects.filter(
                machine=appointment.machine,
                appointment_date=appointment.appointment_date,
                status__in=RICE_MILL_LOCKED_STATUSES,
                start_time__lt=appointment.end_time,
                end_time__gt=appointment.start_time,
            ).exclude(pk=appointment.pk).exists()
        if conflict_exists:
            messages.error(request, 'This time range overlaps with another approved or confirmed appointment.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

        selected_payment_method = appointment.payment_method or 'face_to_face'
        appointment.status = 'approved'
        appointment.payment_method = selected_payment_method
        appointment.save(update_fields=['status', 'payment_method', 'updated_at'])
        if appointment.payment_method == 'face_to_face':
            _sync_appointment_face_to_face_payment_record(appointment)
            messages.success(request, 'Appointment approved. The schedule is reserved and payment will be collected on-site after milling.')
        else:
            messages.success(request, 'Appointment approved. The schedule is reserved and Gcash payment will be available after the final weight is recorded.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
    
    return render(request, 'machines/ricemill_appointment_confirm_approve.html', {'appointment': appointment})

@login_required
def reject_appointment(request, pk):
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    # Ensure only staff can reject appointments
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to reject appointments.")
    
    # Handle form submission
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        appointment.status = 'rejected'
        appointment.save()
        
        try:
            # Try to create a notification
            create_notification(
                user=appointment.user,
                title="Appointment Rejected",
                message=f"Your rice mill appointment for {appointment.appointment_date} has been rejected.",
                category="appointment",
                reference_object=appointment
            )
        except Exception as e:
            # Log the error but continue
            print(f"Error creating notification: {e}")
        
        messages.success(request, 'Appointment has been rejected.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
    
    return render(request, 'machines/ricemill_appointment_confirm_reject.html', {'appointment': appointment})

@login_required
def ricemill_appointment_pending(request, pk):
    """Legacy pending page kept as a redirect to the main appointment detail."""
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    # Ensure only the appointment owner can view the pending page
    if request.user != appointment.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this appointment.")
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def select_ricemill_payment_method(request, pk):
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    if request.user != appointment.user:
        return HttpResponseForbidden("You don't have permission to update this appointment.")

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status != 'approved':
        messages.info(request, 'Payment is only handled after admin approval.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    payment_method = (request.POST.get('payment_method') or '').strip()
    if payment_method not in {'face_to_face'}:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    appointment.payment_method = payment_method
    appointment.save(update_fields=['payment_method', 'updated_at'])
    _sync_appointment_face_to_face_payment_record(appointment)
    messages.success(request, 'Over-the-counter payment selected. Please pay on-site after milling.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def record_ricemill_final_weight(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to record final weight.")

    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status != 'approved':
        messages.info(request, 'Final weight can only be recorded after admin approval.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.payment_method not in [None, 'face_to_face', 'online']:
        messages.error(request, 'Please select a valid payment method before recording the final weight.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    final_weight_raw = request.POST.get('final_weight', '').strip()
    if not final_weight_raw:
        messages.error(request, 'Please enter the final milled weight before confirming payment.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    try:
        final_weight = Decimal(final_weight_raw)
    except Exception:
        messages.error(request, 'Final milled weight must be a valid number.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if final_weight <= 0:
        messages.error(request, 'Final milled weight must be greater than zero.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    sell_tahop = request.POST.get('sell_tahop') == 'on'
    tahop_weight = None
    tahop_price_per_kg = None

    if sell_tahop:
        tahop_weight_raw = request.POST.get('tahop_weight', '').strip()
        tahop_price_raw = request.POST.get('tahop_price_per_kg', '').strip()

        if not tahop_weight_raw or not tahop_price_raw:
            messages.error(request, 'Please enter both tahop weight and price per kilo when tahop sale is selected.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

        try:
            tahop_weight = Decimal(tahop_weight_raw)
            tahop_price_per_kg = Decimal(tahop_price_raw)
        except Exception:
            messages.error(request, 'Tahop weight and price per kilo must be valid numbers.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

        if tahop_weight <= 0 or tahop_price_per_kg <= 0:
            messages.error(request, 'Tahop weight and price per kilo must both be greater than zero.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    appointment.final_weight = final_weight.quantize(Decimal('0.01'))
    appointment.sell_tahop = sell_tahop
    appointment.tahop_weight = tahop_weight.quantize(Decimal('0.01')) if tahop_weight is not None else None
    appointment.tahop_price_per_kg = tahop_price_per_kg.quantize(Decimal('0.01')) if tahop_price_per_kg is not None else None
    appointment.tahop_total_amount = appointment.computed_tahop_total_amount
    appointment.total_amount = appointment.computed_total_amount
    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=appointment.id,
        defaults={
            'user': appointment.user,
            'payment_type': 'appointment',
            'amount': appointment.total_amount,
            'currency': 'PHP',
            'status': 'pending',
        }
    )
    appointment.payment_method = appointment.payment_method or 'face_to_face'
    appointment.save(update_fields=[
        'final_weight',
        'sell_tahop',
        'tahop_weight',
        'tahop_price_per_kg',
        'tahop_total_amount',
        'total_amount',
        'payment_method',
        'updated_at',
    ])

    update_fields = []
    if payment.amount != appointment.total_amount:
        payment.amount = appointment.total_amount
        update_fields.append('amount')
    if payment.status != 'pending':
        payment.status = 'pending'
        update_fields.append('status')
    if payment.paid_at is not None:
        payment.paid_at = None
        update_fields.append('paid_at')
    if payment.payment_provider is not None:
        payment.payment_provider = None
        update_fields.append('payment_provider')
    if update_fields:
        payment.save(update_fields=update_fields)
    _reset_over_counter_payment(payment)

    if appointment.payment_method == 'online':
        messages.success(request, 'Final weight recorded. The member can now complete the Gcash payment.')
    else:
        messages.success(request, 'Final weight recorded. You can now confirm the over-the-counter payment.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def confirm_ricemill_payment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to confirm payments.")

    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    payment = _get_appointment_payment(appointment)

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status not in {'approved', 'paid'} or appointment.final_weight is None:
        messages.info(request, 'Record the final weight first before confirming payment.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.payment_method == 'online':
        if not payment or payment.status != 'completed':
            messages.error(request, 'Gcash payment has not been completed yet.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
    elif appointment.payment_method not in [None, 'face_to_face']:
        messages.error(request, 'Please select a valid payment method before confirming payment.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=appointment.id,
        defaults={
            'user': appointment.user,
            'payment_type': 'appointment',
            'amount': appointment.total_amount,
            'currency': 'PHP',
            'status': 'completed' if appointment.payment_method == 'online' else 'pending',
            'paid_at': timezone.now() if appointment.payment_method == 'online' else None,
        }
    )

    if appointment.payment_method != 'online':
        amount_received_raw = (request.POST.get('amount_received') or '').strip()
        if not amount_received_raw:
            messages.error(request, 'Enter the cash received before confirming an over-the-counter payment.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
        try:
            amount_received = Decimal(amount_received_raw)
        except Exception:
            messages.error(request, 'Cash received must be a valid amount.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
        if amount_received < appointment.total_amount:
            messages.error(request, 'Cash received cannot be less than the total amount due.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
        if appointment.payment_method != 'face_to_face':
            appointment.payment_method = 'face_to_face'
            appointment.save(update_fields=['payment_method', 'updated_at'])
        _record_over_counter_payment(
            payment,
            amount_due=appointment.total_amount,
            amount_received=amount_received,
            processed_by=request.user,
        )
    else:
        update_fields = []
        if not created and payment.status != 'completed':
            payment.status = 'completed'
            update_fields.append('status')
        if payment.paid_at is None:
            payment.paid_at = timezone.now()
            update_fields.append('paid_at')
        if payment.amount != appointment.total_amount:
            payment.amount = appointment.total_amount
            update_fields.append('amount')
        if update_fields:
            payment.save(update_fields=update_fields)

    appointment.status = 'confirmed'
    appointment.save(update_fields=['status', 'updated_at'])
    if appointment.payment_method == 'face_to_face':
        messages.success(
            request,
            f'Payment confirmed. Cash received: PHP {payment.amount_received:.2f}. Change given: PHP {payment.change_given:.2f}.'
        )
    else:
        messages.success(request, 'Payment confirmed.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def complete_ricemill_appointment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to complete appointments.")

    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status != 'confirmed':
        messages.info(request, 'Only confirmed appointments can be marked as completed.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    appointment.status = 'completed'
    appointment.save(update_fields=['status', 'updated_at'])
    _ensure_service_payment_record(
        appointment,
        'appointment',
        status='completed',
    )
    messages.success(request, 'Appointment marked as completed.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


class DryerRentalListView(LoginRequiredMixin, ListView):
    model = DryerRental
    template_name = 'machines/dryer_rental_list.html'
    context_object_name = 'dryer_rentals'

    def get_queryset(self):
        queryset = DryerRental.objects.select_related('machine', 'user', 'parent_rental').all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        status_filter = self.request.GET.get('status')
        date_filter = self.request.GET.get('date')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        if date_filter:
            try:
                date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(rental_date=date_obj)
            except ValueError:
                pass
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rentals = list(context['dryer_rentals'])
        rentals.sort(
            key=lambda rental: (
                -(rental.parent_rental_id or rental.pk),
                rental.batch_number,
                rental.rental_date,
                rental.pk,
            )
        )
        context['dryer_rentals'] = rentals
        all_dryers = list(_dryer_queryset())
        available_dryers = [machine for machine in all_dryers if _dryer_requestable(machine)]
        availability_rows = _build_dryer_availability_rows(all_dryers)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['date_filter'] = self.request.GET.get('date', '')
        context['show_user_dryer_cards'] = not self.request.user.is_staff
        context['available_dryers'] = available_dryers
        context['admin_dryer_units'] = all_dryers
        context['dryer_availability_rows'] = availability_rows
        context['total_dryer_count'] = len(all_dryers)
        context['available_dryer_count'] = len(available_dryers)
        context['occupied_dryer_count'] = sum(1 for row in availability_rows if row['status_label'] == 'Occupied')
        context['available_soon_dryer_count'] = sum(1 for row in availability_rows if row['status_label'] == 'Available Soon')
        context['pending_count'] = sum(1 for rental in rentals if rental.status == 'pending')
        context['approved_count'] = sum(1 for rental in rentals if rental.status in ['approved', 'paid', 'confirmed', 'in_progress'])
        context['paid_count'] = sum(1 for rental in rentals if rental.status == 'paid')
        context['confirmed_count'] = sum(1 for rental in rentals if rental.status == 'confirmed')
        context['in_progress_count'] = sum(1 for rental in rentals if rental.status == 'in_progress')
        context['completed_count'] = sum(1 for rental in rentals if rental.status == 'completed')
        return context


class DryerRentalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = DryerRental
    template_name = 'machines/dryer_rental_detail.html'
    context_object_name = 'dryer_rental'

    def test_func(self):
        dryer_rental = self.get_object()
        return self.request.user.is_staff or self.request.user == dryer_rental.user

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.is_staff and self.object.status in ['pending', 'waiting_confirmation']:
            return redirect('machines:dryer_rental_approve', pk=self.object.pk)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dryer_rental = self.get_object()
        is_hourly_pricing = dryer_rental.is_hourly_pricing
        is_until_dried_pricing = dryer_rental.is_until_dried_pricing
        batch_group_members = list(dryer_rental.batch_group_members_queryset())

        context['total_amount'] = dryer_rental.total_amount
        context['is_hourly_pricing'] = is_hourly_pricing
        context['is_until_dried_pricing'] = is_until_dried_pricing
        context['is_per_sack_pricing'] = dryer_rental.is_per_sack_pricing
        context['estimated_service_end_date'] = dryer_rental.estimated_service_end_date
        context['estimated_service_end_display'] = dryer_rental.estimated_service_end_display
        context['batch_group_members'] = batch_group_members
        context['is_batch_grouped'] = dryer_rental.is_batch_grouped
        context['batch_group_reference'] = dryer_rental.batch_group_reference
        context['batch_group_total_sacks'] = dryer_rental.batch_group_total_sacks
        context['can_modify'] = dryer_rental.can_be_modified()
        context['can_cancel'] = dryer_rental.can_be_cancelled()
        context['can_staff_review'] = self.request.user.is_staff and dryer_rental.status in ['pending', 'waiting_confirmation']
        context['payment_record'] = _get_dryer_payment(dryer_rental)
        context['transaction_id'] = (
            context['payment_record'].internal_transaction_id
            if context['payment_record']
            else dryer_rental.get_transaction_id()
        )
        context['over_counter_suggestions'] = [
            dryer_rental.total_amount,
            Decimal('500.00'),
            Decimal('1000.00'),
            Decimal('1500.00'),
            Decimal('2000.00'),
        ]
        computed_sack_total = None
        if dryer_rental.is_per_sack_pricing and dryer_rental.billing_quantity_in_sacks is not None:
            computed_sack_total = (
                dryer_rental.billing_quantity_in_sacks * dryer_rental.effective_hourly_rate
            ).quantize(Decimal('0.01'))

        context['computed_sack_total'] = computed_sack_total
        context['requested_quantity_in_sacks'] = dryer_rental.quantity_in_sacks
        context['billing_quantity_in_sacks'] = dryer_rental.billing_quantity_in_sacks
        context['show_payment_section'] = dryer_rental.status in ['paid', 'confirmed']
        context['can_staff_record_payment_amount'] = self.request.user.is_staff and (
            (is_hourly_pricing and dryer_rental.status in ['approved', 'in_progress'])
            or (is_until_dried_pricing and dryer_rental.status in ['approved', 'in_progress'])
        )
        context['can_choose_payment_method'] = (
            self.request.user == dryer_rental.user
            and dryer_rental.status == 'paid'
        )
        context['can_launch_online_payment'] = (
            self.request.user == dryer_rental.user
            and dryer_rental.status == 'paid'
            and dryer_rental.payment_method == 'online'
        )
        context['can_staff_confirm_payment'] = (
            self.request.user.is_staff
            and dryer_rental.status == 'paid'
            and (
                dryer_rental.payment_method in [None, 'face_to_face']
                or (
                    dryer_rental.payment_method == 'online'
                    and context['payment_record']
                    and context['payment_record'].status == 'completed'
                )
            )
        )
        context['can_admin_mark_completed'] = self.request.user.is_staff and (
            dryer_rental.status == 'confirmed'
        )
        return context


class DryerRentalCreateView(LoginRequiredMixin, CreateView):
    model = DryerRental
    form_class = DryerRentalForm
    template_name = 'machines/dryer_rental_form.html'

    def _selected_machine_id(self):
        return self.kwargs.get('machine_id') or self.request.GET.get('selected_machine')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_verified and not request.user.is_superuser:
            messages.warning(request, "Your membership requires verification before you can schedule dryer rentals.")
            return redirect('profile')
        if not request.user.is_staff and not self._selected_machine_id():
            messages.info(
                request,
                'Please choose a dryer from the Dryer Services page before opening the request form.'
            )
            return redirect('machines:dryer_rental_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        machine_id = self._selected_machine_id()
        if machine_id:
            initial['machine'] = machine_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        machine_id = self._selected_machine_id()
        if machine_id:
            kwargs['machine_id'] = machine_id
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        context['action'] = 'Create'
        context['is_admin_booking'] = bool(form and getattr(form, 'is_admin_booking', False))
        selected_dryer = getattr(form, '_selected_machine', None) if form else None
        requested_dryer = Machine.objects.filter(
            pk=self._selected_machine_id(),
            machine_type__in=Machine.DRYER_MACHINE_TYPES
        ).first()
        context['selected_machine_id'] = str(self._selected_machine_id() or '')
        if form and getattr(form, 'is_admin_booking', False):
            selectable_dryers = form.fields['machine'].queryset
            dryer = selected_dryer or requested_dryer or selectable_dryers.first()
        else:
            dryer = selected_dryer or requested_dryer or _ensure_default_dryer()
        if form and getattr(form, 'is_admin_booking', False):
            options = [
                _build_dryer_machine_payload(machine)
                for machine in form.fields['machine'].queryset
            ]
            context['dryer_options_json'] = mark_safe(json.dumps(options))
            context['has_selectable_dryers'] = form.fields['machine'].queryset.exists()
        if dryer:
            context['machine'] = dryer
            events = _build_dryer_calendar_events(dryer)
            context['machine_is_requestable'] = _dryer_requestable(dryer)
            context['calendar_events_json'] = mark_safe(json.dumps(events))
            context.setdefault(
                'dryer_options_json',
                mark_safe(json.dumps([_build_dryer_machine_payload(dryer)]))
            )
        context.setdefault('has_selectable_dryers', bool(dryer))
        return context

    def form_valid(self, form):
        form.apply_booking_identity(form.instance)
        if not form.instance.user_id:
            form.instance.user = self.request.user
        form.instance.status = 'pending'
        if self.request.user.is_staff or self.request.user.is_superuser:
            form.instance.payment_method = 'face_to_face'
        dryer = (
            form.cleaned_data.get('machine')
            or getattr(form, '_selected_machine', None)
            or _ensure_default_dryer()
        )
        if not dryer:
            form.add_error(None, 'No flatbed dryer is configured yet. Please contact the administrator.')
            return self.form_invalid(form)
        form.instance.machine = dryer
        self.object = form.save()
        messages.success(self.request, 'Dryer rental request created successfully and is now waiting for admin approval.')
        return HttpResponseRedirect(
            reverse('machines:dryer_rental_detail', kwargs={'pk': self.object.pk})
        )

    def get_success_url(self):
        return reverse('machines:dryer_rental_detail', kwargs={'pk': self.object.pk})


class DryerRentalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DryerRental
    form_class = DryerRentalForm
    template_name = 'machines/dryer_rental_form.html'

    def test_func(self):
        dryer_rental = self.get_object()
        if not dryer_rental.can_be_modified():
            return False
        return self.request.user == dryer_rental.user or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        context['action'] = 'Update'
        context['is_admin_booking'] = bool(form and getattr(form, 'is_admin_booking', False))
        dryer_rental = self.get_object()
        machine = dryer_rental.machine
        context['machine'] = machine
        context['machine_is_requestable'] = _dryer_requestable(machine)
        events = _build_dryer_calendar_events(machine, exclude_pk=dryer_rental.pk)
        context['calendar_events_json'] = mark_safe(json.dumps(events))
        if form and getattr(form, 'is_admin_booking', False):
            options = [
                _build_dryer_machine_payload(option, exclude_pk=dryer_rental.pk)
                for option in form.fields['machine'].queryset
            ]
            context['dryer_options_json'] = mark_safe(json.dumps(options))
            context['has_selectable_dryers'] = form.fields['machine'].queryset.exists()
        else:
            context['dryer_options_json'] = mark_safe(
                json.dumps([_build_dryer_machine_payload(machine, exclude_pk=dryer_rental.pk)])
            )
            context['has_selectable_dryers'] = True
        return context

    def form_valid(self, form):
        dryer = (
            form.cleaned_data.get('machine')
            or self.get_object().machine
            or getattr(form, '_selected_machine', None)
        )
        if not dryer:
            form.add_error(None, 'No flatbed dryer is configured for this rental.')
            return self.form_invalid(form)
        form.instance.machine = dryer
        form.instance.status = 'pending'
        messages.info(self.request, 'Your dryer rental has been updated and is waiting for admin approval again.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('machines:dryer_rental_detail', kwargs={'pk': self.object.pk})


class DryerRentalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = DryerRental
    template_name = 'machines/dryer_rental_confirm_delete.html'
    success_url = reverse_lazy('machines:dryer_rental_list')

    def test_func(self):
        dryer_rental = self.get_object()
        if not dryer_rental.can_be_cancelled():
            return False
        return self.request.user == dryer_rental.user or self.request.user.is_staff

    def form_valid(self, form):
        dryer_rental = self.get_object()
        if dryer_rental.is_batch_grouped:
            grouped_rentals = list(dryer_rental.batch_group_members_queryset())
            for grouped_rental in sorted(grouped_rentals, key=lambda rental: rental.batch_number, reverse=True):
                grouped_rental.delete()
            messages.success(
                self.request,
                f'Dryer request group {dryer_rental.batch_group_reference} and its {len(grouped_rentals)} linked batch(es) have been cancelled.',
            )
            return redirect(self.success_url)
        messages.success(self.request, f'Dryer rental for {dryer_rental.rental_date} has been cancelled.')
        return super().form_valid(form)


def _dryer_approval_context(dryer_rental, approval_form):
    return {
        'dryer_rental': dryer_rental,
        'approval_form': approval_form,
        'batch_group_members': list(dryer_rental.batch_group_members_queryset()),
        'is_batch_grouped': dryer_rental.is_batch_grouped,
        'batch_group_reference': dryer_rental.batch_group_reference,
        'batch_group_total_sacks': dryer_rental.batch_group_total_sacks,
    }


@login_required
def approve_dryer_rental(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to approve dryer rentals.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    form = DryerRentalApprovalForm(request.POST or None, instance=dryer_rental)
    if request.method == 'POST':
        if not form.is_valid():
            return render(
                request,
                'machines/dryer_rental_confirm_approve.html',
                _dryer_approval_context(dryer_rental, form)
            )

        conflict_queryset = DryerRental.objects.filter(
            machine=dryer_rental.machine,
            status__in=DRYER_LOCKED_STATUSES,
        ).exclude(pk=dryer_rental.pk)

        if dryer_rental.is_hourly_pricing:
            conflict_exists = conflict_queryset.filter(
                rental_date=dryer_rental.rental_date,
                start_time__lt=dryer_rental.end_time,
                end_time__gt=dryer_rental.start_time,
            ).exists()
            if conflict_exists:
                messages.error(
                    request,
                    'This dryer request conflicts with another approved or active dryer booking for the selected time.'
                )
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

            dryer_rental.admin_note = form.cleaned_data.get('admin_note') or ''
            dryer_rental.estimated_end_date = dryer_rental.rental_date
            dryer_rental.estimated_end_time = dryer_rental.end_time
            dryer_rental.status = 'approved'
            dryer_rental.payment_method = 'face_to_face'
            dryer_rental.save(update_fields=['admin_note', 'estimated_end_date', 'estimated_end_time', 'payment_method', 'status', 'updated_at'])
            messages.success(request, 'Dryer rental approved. The selected hours are now reserved.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

        estimated_end_date = form.cleaned_data.get('estimated_end_date')
        estimated_end_time = form.cleaned_data.get('estimated_end_time')
        target_end_date = estimated_end_date or dryer_rental.rental_date
        requested_sacks = dryer_rental.quantity_in_sacks
        if estimated_end_date and requested_sacks is not None and requested_sacks > 0:
            date_cursor = dryer_rental.rental_date
            while date_cursor <= target_end_date:
                available_capacity = DryerRental.available_dryer_capacity_for_date(
                    dryer_rental.machine,
                    date_cursor,
                    exclude_pk=dryer_rental.pk,
                )
                if requested_sacks > available_capacity:
                    messages.error(
                        request,
                        f'This dryer only has {available_capacity:,.2f} sack(s) remaining on '
                        f'{date_cursor:%B %d, %Y}. Reduce the quantity or shorten the service window.'
                    )
                    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
                date_cursor += timedelta(days=1)

        dryer_rental.admin_note = form.cleaned_data.get('admin_note') or ''
        dryer_rental.estimated_end_date = estimated_end_date
        dryer_rental.estimated_end_time = estimated_end_time
        dryer_rental.payment_method = 'face_to_face'
        dryer_rental.status = 'in_progress' if estimated_end_date and estimated_end_time else 'waiting_confirmation'
        dryer_rental.save(update_fields=['admin_note', 'estimated_end_date', 'estimated_end_time', 'payment_method', 'status', 'updated_at'])
        if estimated_end_date:
            schedule_label = _format_estimated_service_schedule(dryer_rental)
            messages.success(
                request,
                f'Dryer service moved to in progress. The dryer is now blocked through {schedule_label}.'
            )
        else:
            messages.success(
                request,
                'Dryer request is now waiting for confirmation. The renter can review your note before scheduling continues.'
            )
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    return render(
        request,
        'machines/dryer_rental_confirm_approve.html',
        _dryer_approval_context(dryer_rental, form)
    )


@login_required
def reject_dryer_rental(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to reject dryer rentals.")
    if request.method == 'POST':
        dryer_rental.status = 'rejected'
        dryer_rental.save()
        messages.success(request, 'Dryer rental has been rejected.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    return render(request, 'machines/dryer_rental_confirm_reject.html', {'dryer_rental': dryer_rental})


@login_required
def dryer_rental_pending(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.user != dryer_rental.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this dryer rental.")
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def select_dryer_payment_method(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.user != dryer_rental.user:
        return HttpResponseForbidden("You don't have permission to update this dryer rental.")
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status != 'paid':
        messages.info(request, 'Payment method can only be selected after staff records the final dryer amount.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.total_amount <= 0:
        messages.info(request, 'Staff must record the final dryer amount before choosing a payment method.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    payment_method = request.POST.get('payment_method')
    if payment_method not in ['face_to_face']:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    dryer_rental.payment_method = payment_method
    dryer_rental.save(update_fields=['payment_method', 'updated_at'])
    _sync_dryer_payment_record(dryer_rental, payment_method)
    messages.success(
        request,
        'Gcash payment selected. You can now proceed to payment.'
        if payment_method == 'online'
        else 'Over-the-counter payment selected. Please pay at the BUFIA office so staff can confirm the transaction.'
    )
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def confirm_dryer_payment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to confirm dryer payments.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    payment = _get_dryer_payment(dryer_rental)
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status != 'paid':
        messages.info(request, 'Record the final dryer amount first before confirming payment.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.total_amount <= 0:
        messages.error(request, 'The final dryer amount must be recorded before confirming payment.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.payment_method not in [None, 'online', 'face_to_face']:
        messages.error(request, 'Please select a valid payment method before confirming payment.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.payment_method == 'online' and (not payment or payment.status != 'completed'):
        messages.error(request, 'Gcash payment has not been completed yet.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.payment_method != 'online':
        amount_received_raw = (request.POST.get('amount_received') or '').strip()
        if not amount_received_raw:
            messages.error(request, 'Enter the cash received before confirming an over-the-counter payment.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
        try:
            amount_received = Decimal(amount_received_raw)
        except Exception:
            messages.error(request, 'Cash received must be a valid amount.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
        if amount_received < dryer_rental.total_amount:
            messages.error(request, 'Cash received cannot be less than the total amount due.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        content_type = ContentType.objects.get_for_model(DryerRental)
        payment, _ = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=dryer_rental.id,
            defaults={
                'user': dryer_rental.user,
                'payment_type': 'dryer',
                'amount': dryer_rental.total_amount,
                'currency': 'PHP',
                'status': 'pending',
                'paid_at': None,
            }
        )
        if dryer_rental.payment_method != 'face_to_face':
            dryer_rental.payment_method = 'face_to_face'
            dryer_rental.save(update_fields=['payment_method', 'updated_at'])
        _record_over_counter_payment(
            payment,
            amount_due=dryer_rental.total_amount,
            amount_received=amount_received,
            processed_by=request.user,
        )
    dryer_rental.status = 'confirmed'
    dryer_rental.save(update_fields=['status', 'updated_at'])
    if dryer_rental.payment_method == 'face_to_face':
        messages.success(
            request,
            f'Dryer rental payment confirmed. Cash received: PHP {payment.amount_received:.2f}. Change given: PHP {payment.change_given:.2f}.'
        )
    else:
        messages.success(request, 'Dryer rental payment confirmed.')
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def complete_dryer_rental(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to complete dryer rentals.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status in ['approved', 'in_progress']:
        update_fields = ['total_amount', 'status', 'updated_at']
        if dryer_rental.is_per_sack_pricing:
            confirmed_sacks_raw = (request.POST.get('confirmed_quantity_sacks') or '').strip()
            if not confirmed_sacks_raw:
                messages.error(request, 'Enter the final confirmed sacks before saving the dryer payment amount.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
            try:
                confirmed_sacks = Decimal(confirmed_sacks_raw).quantize(Decimal('0.01'))
            except Exception:
                messages.error(request, 'Enter a valid confirmed sacks amount.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
            if confirmed_sacks <= 0:
                messages.error(request, 'Confirmed sacks must be greater than zero.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

            dryer_rental.confirmed_quantity_sacks = confirmed_sacks
            final_amount = (confirmed_sacks * dryer_rental.effective_hourly_rate).quantize(Decimal('0.01'))
            if final_amount <= 0:
                messages.error(request, 'Final dryer amount must be greater than zero.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

            dryer_rental.total_amount = final_amount
            update_fields.append('confirmed_quantity_sacks')
        else:
            actual_hours_raw = (request.POST.get('actual_drying_hours') or '').strip()
            if not actual_hours_raw:
                messages.error(request, 'Enter the total drying hours before saving the payment amount.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
            try:
                actual_drying_hours = Decimal(actual_hours_raw).quantize(Decimal('0.01'))
            except Exception:
                messages.error(request, 'Enter a valid number of actual drying hours.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
            if actual_drying_hours <= 0:
                messages.error(request, 'Actual drying hours must be greater than zero.')
                return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

            dryer_rental.actual_drying_hours = actual_drying_hours
            if dryer_rental.hourly_rate_snapshot is None:
                dryer_rental.hourly_rate_snapshot = dryer_rental.machine.get_effective_dryer_hourly_rate()
            dryer_rental.total_amount = (actual_drying_hours * dryer_rental.effective_hourly_rate).quantize(Decimal('0.01'))
            update_fields.extend(['actual_drying_hours', 'hourly_rate_snapshot'])

        dryer_rental.status = 'paid'
        dryer_rental.payment_method = 'face_to_face'
        update_fields.extend(['payment_method'])
        dryer_rental.save(update_fields=update_fields)
        _sync_dryer_payment_record(dryer_rental, 'face_to_face')

        messages.success(
            request,
            'Final dryer billing recorded. The total due now follows the admin-confirmed service amount and can be confirmed for payment.'
        )
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

    if dryer_rental.status != 'confirmed':
        messages.info(request, 'Confirm payment first before marking this dryer request as completed.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)

    dryer_rental.status = 'completed'
    dryer_rental.save(update_fields=['status', 'updated_at'])
    _ensure_service_payment_record(
        dryer_rental,
        'dryer',
        status='completed',
    )
    messages.success(request, 'Dryer rental marked as completed.')
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def dryer_rental_receipt(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if dryer_rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('machines:dryer_rental_list')
    payment = _get_dryer_payment(dryer_rental)
    if not payment and dryer_rental.status in ['paid', 'confirmed', 'completed']:
        payment = _ensure_service_payment_record(
            dryer_rental,
            'dryer',
            status='completed' if dryer_rental.status in ['confirmed', 'completed'] else 'pending',
        )
    transaction_id = payment.internal_transaction_id if payment else dryer_rental.get_transaction_id()
    return render(request, 'machines/dryer_rental_receipt.html', {
        'dryer_rental': dryer_rental,
        'total_amount': dryer_rental.total_amount,
        'payment': payment,
        'transaction_id': transaction_id,
    })

@login_required
def debug_machine_images(request, pk):
    """Debug view to check machine images"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only")
    
    machine = get_object_or_404(Machine, pk=pk)
    
    # Check media directories
    media_root = settings.MEDIA_ROOT
    machine_dir = os.path.join(media_root, 'machines')
    machine_images_dir = os.path.join(machine_dir, 'images')
    
    # Generate machine slug
    machine_slug = slugify(machine.name)
    machine_specific_dir = os.path.join(machine_images_dir, machine_slug)
    
    # Directory structure
    directories = {
        'MEDIA_ROOT': {
            'path': media_root,
            'exists': os.path.exists(media_root),
        },
        'machines/': {
            'path': machine_dir,
            'exists': os.path.exists(machine_dir),
        },
        'machines/images/': {
            'path': machine_images_dir,
            'exists': os.path.exists(machine_images_dir),
        },
        f'machines/images/{machine_slug}/': {
            'path': machine_specific_dir,
            'exists': os.path.exists(machine_specific_dir),
        },
    }
    
    # Check machine direct image
    machine_image = {
        'field': machine.image,
        'url': machine.image.url if machine.image else None,
        'path': machine.image.path if machine.image else None,
        'exists': os.path.exists(machine.image.path) if machine.image else False,
    }
    
    # Check related images
    related_images = []
    for img in machine.images.all():
        related_images.append({
            'id': img.id,
            'url': img.image.url if img.image else None,
            'path': img.image.path if img.image else None,
            'exists': os.path.exists(img.image.path) if img.image else False,
            'is_primary': img.is_primary,
        })
    
    # List files in machine-specific directory
    directory_files = []
    if os.path.exists(machine_specific_dir):
        for file in os.listdir(machine_specific_dir):
            file_path = os.path.join(machine_specific_dir, file)
            directory_files.append({
                'name': file,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'in_db': any(img['path'] == file_path for img in related_images) if related_images else False,
            })
    
    context = {
        'machine': machine,
        'directories': directories,
        'machine_image': machine_image,
        'related_images': related_images,
        'directory_files': directory_files,
    }
    
    return render(request, 'machines/debug_images.html', context)

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_list(request):
    """View all maintenance records with filtering options"""
    affected_machine_ids = set(
        Machine.objects.filter(status='maintenance').values_list('id', flat=True)
    )
    affected_machine_ids.update(
        Maintenance.objects.filter(
            status__in=ACTIVE_MAINTENANCE_STATUSES
        ).values_list('machine_id', flat=True)
    )
    for machine in Machine.objects.filter(id__in=affected_machine_ids):
        machine.sync_status()
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    machine_filter = request.GET.get('machine', '')
    maintenance_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    maintenance_records = Maintenance.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        maintenance_records = maintenance_records.filter(status=status_filter)
    if machine_filter:
        maintenance_records = maintenance_records.filter(machine_id=machine_filter)
    if maintenance_type:
        maintenance_records = maintenance_records.filter(maintenance_type=maintenance_type)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(start_date__date__gte=date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(start_date__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Find machines with status 'maintenance' that don't have active maintenance records
    machines_under_maintenance = Machine.objects.filter(status='maintenance')
    
    # Create a list to track machines that already have active maintenance records
    machines_with_records = set(
        maintenance_records.filter(
            status__in=['scheduled', 'in_progress'],
            machine__status='maintenance'
        ).values_list('machine_id', flat=True)
    )
    
    # Find machines that are in maintenance status but don't have active maintenance records
    orphaned_machines = []
    for machine in machines_under_maintenance:
        if machine.id not in machines_with_records:
            orphaned_machines.append(machine)
    
    # Get machines and maintenance types for filter dropdowns
    machines = Machine.objects.all().order_by('name')
    maintenance_types = Maintenance.MAINTENANCE_TYPE_CHOICES
    status_choices = Maintenance.STATUS_CHOICES
    
    # Statistics
    active_maintenance = maintenance_records.filter(status__in=['scheduled', 'in_progress']).count() + len(orphaned_machines)
    completed_maintenance = maintenance_records.filter(status='completed').count()
    overdue_maintenance = sum(1 for record in maintenance_records if record.is_overdue())
    
    context = {
        'maintenance_records': maintenance_records,
        'orphaned_machines': orphaned_machines, 
        'machines': machines,
        'maintenance_types': maintenance_types,
        'status_choices': status_choices,
        'active_maintenance': active_maintenance,
        'completed_maintenance': completed_maintenance,
        'overdue_maintenance': overdue_maintenance,
        'selected_status': status_filter,
        'selected_machine': machine_filter,
        'selected_type': maintenance_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'machines/maintenance_list.html', context)

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_detail(request, pk):
    """View details of a specific maintenance record"""
    maintenance = get_object_or_404(
        Maintenance.objects.select_related('machine', 'created_by', 'technician').prefetch_related(
            'parts_used',
            Prefetch(
                'machine__maintenance_records',
                queryset=Maintenance.objects.select_related('created_by', 'technician').order_by('-start_date', '-pk'),
            ),
        ),
        pk=pk,
    )
    
    context = {
        'maintenance': maintenance,
    }
    
    return render(request, 'machines/maintenance_detail.html', context)

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_start(request, pk):
    """Move a scheduled maintenance record into progress."""
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if request.method != 'POST':
        return redirect('machines:maintenance_detail', pk=maintenance.pk)

    if maintenance.status == 'completed':
        messages.info(request, 'This maintenance record is already completed.')
    elif maintenance.status == 'cancelled':
        messages.error(request, 'Cancelled maintenance records cannot be started.')
    elif maintenance.status == 'in_progress':
        messages.info(request, f'{maintenance.machine.name} is already in progress.')
    else:
        maintenance.status = 'in_progress'
        maintenance.actual_completion_date = None
        maintenance.save(update_fields=['status', 'actual_completion_date', 'updated_at'])
        _sync_machine_maintenance_status(maintenance.machine)
        messages.success(request, f'Maintenance for {maintenance.machine.name} is now in progress.')

    return redirect('machines:maintenance_detail', pk=maintenance.pk)

@login_required
@user_passes_test(_maintenance_management_access, login_url='/dashboard/', redirect_field_name=None)
def maintenance_complete(request, pk):
    """Finish a maintenance record through the completion workflow."""
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if maintenance.status == 'completed':
        messages.info(request, 'This maintenance record is already completed.')
        return redirect('machines:maintenance_detail', pk=maintenance.pk)

    if maintenance.status != 'in_progress':
        messages.error(request, 'Start the maintenance record before finishing it.')
        return redirect('machines:maintenance_detail', pk=maintenance.pk)

    if request.method == 'POST':
        form = MaintenanceCompletionForm(request.POST, instance=maintenance)
        part_formset = MaintenancePartFormSet(request.POST, instance=maintenance, prefix='parts')

        form_is_valid = form.is_valid()
        formset_is_valid = part_formset.is_valid()

        if form_is_valid and formset_is_valid:
            has_part_rows = any(
                cleaned_data.get('part_name')
                for cleaned_data in (
                    part_form.cleaned_data
                    for part_form in part_formset.forms
                    if hasattr(part_form, 'cleaned_data')
                )
                if cleaned_data and not cleaned_data.get('DELETE')
            )
            no_parts_replaced = form.cleaned_data.get('no_parts_replaced')

            if not has_part_rows and not no_parts_replaced:
                form.add_error('no_parts_replaced', 'Add at least one part row or select "No parts replaced".')
            elif has_part_rows and no_parts_replaced:
                form.add_error('no_parts_replaced', 'Clear this option when listing replaced parts.')
            else:
                with transaction.atomic():
                    maintenance = form.save(commit=False)
                    maintenance.status = 'completed'
                    maintenance.technician = None
                    maintenance.technician_name = form.cleaned_data.get('technician_name', '')
                    maintenance.save()
                    part_formset.instance = maintenance
                    part_instances = part_formset.save(commit=False)
                    for deleted_part in part_formset.deleted_objects:
                        deleted_part.delete()
                    for part in part_instances:
                        if not (part.part_name or '').strip():
                            continue
                        if part.quantity in (None, '') or part.unit_price is None:
                            continue
                        part.maintenance_record = maintenance
                        part.save()
                    maintenance.sync_completion_totals()
                    _sync_machine_maintenance_status(maintenance.machine)

                messages.success(request, f'Maintenance for {maintenance.machine.name} completed successfully.')
                return redirect('machines:maintenance_detail', pk=maintenance.pk)
    else:
        form = MaintenanceCompletionForm(instance=maintenance)
        part_formset = MaintenancePartFormSet(instance=maintenance, prefix='parts')

    context = {
        'maintenance': maintenance,
        'form': form,
        'part_formset': part_formset,
        'parts_total': maintenance.get_parts_total(),
        'projected_total': maintenance.calculate_actual_cost(),
    }
    
    return render(request, 'machines/maintenance_complete_confirm.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_rental_create(request, machine_pk=None):
    """Admin view for creating rentals on behalf of users"""
    if request.method == 'POST':
        form = AdminRentalForm(request.POST)
        if form.is_valid():
            rental = form.save(commit=False)
            form.apply_booking_identity(rental)
            rental.status = 'approved'
            rental.workflow_state = 'approved'
            if rental.payment_type != 'in_kind':
                # Don't force payment_method - preserve what user selected
                if not rental.payment_method:
                    rental.payment_method = 'face_to_face'
                rental.payment_status = 'pending'
            rental.save()

            # Keep amount aligned with admin-configured machine pricing
            rental.payment_amount = rental.calculate_payment_amount()
            rental.save(update_fields=['payment_amount'])
            
            if rental.payment_type == 'cash':
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                
                content_type = ContentType.objects.get_for_model(rental)
                Payment.objects.get_or_create(
                    content_type=content_type,
                    object_id=rental.id,
                    defaults={
                        'user': rental.user,
                        'payment_type': 'rental',
                        'amount': rental.payment_amount or 0,
                        'currency': 'PHP',
                        'status': 'pending',
                    }
                )
            
            messages.success(request, f'Rental for {rental.customer_display_name} created and automatically approved.')
            return redirect('machines:admin_approve_rental', rental_id=rental.pk)
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = AdminRentalForm(initial=initial)
    
    context = {
        'form': form,
        'action': 'Create',
        'is_admin_form': True
    }
    return render(request, 'machines/admin_rental_form.html', context)


@login_required
@user_passes_test(lambda user: user.is_staff or user.is_superuser)
def member_autocomplete(request):
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    members = _member_search_queryset().filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(username__icontains=query)
    ).order_by('first_name', 'last_name', 'username')[:8]

    return JsonResponse({
        'results': [_member_search_payload(member) for member in members]
    })


@login_required
def ricemill_appointment_receipt(request, pk):
    """Render a printable receipt for rice mill appointment"""
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    # Security check - only allow the appointment owner or staff to view
    if appointment.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('machines:ricemill_appointment_list')
    
    final_weight = appointment.final_weight
    billable_weight = appointment.billable_weight
    price_per_kg = appointment.effective_price_per_kg
    final_amount = ((final_weight or Decimal('0.00')) * price_per_kg).quantize(Decimal('0.01')) if final_weight is not None else None
    tahop_total_amount = appointment.computed_tahop_total_amount
    total_amount = appointment.computed_total_amount
    payment = _get_appointment_payment(appointment)
    if not payment and appointment.status in ['paid', 'confirmed', 'completed']:
        payment = _ensure_service_payment_record(
            appointment,
            'appointment',
            status='completed' if appointment.status in ['confirmed', 'completed'] else 'pending',
        )
    transaction_id = payment.internal_transaction_id if payment else appointment.get_transaction_id()
    
    context = {
        'appointment': appointment,
        'final_weight': final_weight,
        'billable_weight': billable_weight,
        'price_per_kg': price_per_kg,
        'final_amount': final_amount,
        'milling_amount': appointment.computed_milling_amount,
        'tahop_total_amount': tahop_total_amount,
        'total_amount': total_amount,
        'payment': payment,
        'transaction_id': transaction_id,
    }
    
    return render(request, 'machines/ricemill_appointment_receipt.html', context)
