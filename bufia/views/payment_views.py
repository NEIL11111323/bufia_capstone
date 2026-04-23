import csv
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from bufia.forms import RefundForm
from bufia.models import Payment
from bufia.services.payments import (
    create_user_notification,
    notify_named_user,
    notify_staff,
    record_membership_online_payment,
    record_rental_online_payment,
    upsert_payment_record,
)
from bufia.services.paymongo import (
    PayMongoAPIError,
    checkout_session_is_successful as paymongo_checkout_session_is_successful,
    create_checkout_session as paymongo_create_checkout_session,
    extract_paid_amount as paymongo_extract_paid_amount,
    extract_payment_id as paymongo_extract_payment_id,
    extract_payment_intent_id as paymongo_extract_payment_intent_id,
    get_enabled_payment_methods,
    is_configured as paymongo_is_configured,
    retrieve_checkout_session as paymongo_retrieve_checkout_session,
    verify_webhook_signature as paymongo_verify_webhook_signature,
)
from irrigation.models import IrrigationSeasonRecord
from machines.models import DryerRental, Rental, RiceMillAppointment
from reports.export_utils import build_pdf_bytes, build_xlsx_bytes
from users.activity import log_activity


class _LegacyStripeNamespace:
    class checkout:
        class Session:
            @staticmethod
            def create(*args, **kwargs):
                raise NotImplementedError('Stripe checkout is no longer active in this project.')

            @staticmethod
            def retrieve(*args, **kwargs):
                raise NotImplementedError('Stripe checkout is no longer active in this project.')


stripe = _LegacyStripeNamespace()


def _paymongo_is_configured():
    return paymongo_is_configured()


def _stripe_is_configured():
    """Compatibility alias retained for older tests and helper calls."""
    return _paymongo_is_configured()


def _checkout_session_is_successful(session) -> bool:
    return paymongo_checkout_session_is_successful(session)


def _is_mocked_callable(value) -> bool:
    return value is not None and value.__class__.__module__.startswith('unittest.mock')


def _session_value(session_payload, key, default=None):
    if isinstance(session_payload, dict):
        return session_payload.get(key, default)
    return getattr(session_payload, key, default)


def _create_checkout_session_compat(
    *,
    amount_centavos,
    name,
    description,
    success_url,
    cancel_url,
    metadata,
    reference_number,
    customer_email=None,
    customer_name=None,
    payment_method_types=None,
):
    legacy_create = getattr(getattr(getattr(stripe, 'checkout', None), 'Session', None), 'create', None)
    if _is_mocked_callable(legacy_create):
        legacy_session = legacy_create(
            payment_method_types=payment_method_types or ['gcash'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'php',
                        'product_data': {
                            'name': name,
                            'description': description,
                        },
                        'unit_amount': int(amount_centavos),
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=f'{success_url}&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=cancel_url,
            metadata=metadata,
            customer_email=customer_email,
            customer_name=customer_name,
            reference_number=reference_number,
        )
        return {
            'id': _session_value(legacy_session, 'id'),
            'attributes': {
                'checkout_url': _session_value(legacy_session, 'url'),
            },
        }

    return paymongo_create_checkout_session(
        amount_centavos=amount_centavos,
        name=name,
        description=description,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        reference_number=reference_number,
        customer_email=customer_email,
        customer_name=customer_name,
        payment_method_types=payment_method_types,
    )


def _retrieve_checkout_session_compat(checkout_session_id):
    legacy_retrieve = getattr(getattr(getattr(stripe, 'checkout', None), 'Session', None), 'retrieve', None)
    if _is_mocked_callable(legacy_retrieve):
        return legacy_retrieve(checkout_session_id)
    return paymongo_retrieve_checkout_session(checkout_session_id)


ONLINE_CHECKOUT_MAX_AMOUNT_PHP = Decimal('999999.99')


def _get_payment_for_object(content_object):
    content_type = ContentType.objects.get_for_model(content_object.__class__)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=content_object.pk,
    ).first()


def _prepare_pending_online_payment(payment_obj, *, amount):
    update_fields = []
    normalized_amount = Decimal(str(amount)).quantize(Decimal('0.01'))

    if payment_obj.amount != normalized_amount:
        payment_obj.amount = normalized_amount
        update_fields.append('amount')
    if payment_obj.currency != 'PHP':
        payment_obj.currency = 'PHP'
        update_fields.append('currency')
    if payment_obj.status != 'pending':
        payment_obj.status = 'pending'
        update_fields.append('status')
    if payment_obj.payment_provider != 'paymongo':
        payment_obj.payment_provider = 'paymongo'
        update_fields.append('payment_provider')
    if payment_obj.paid_at is not None:
        payment_obj.paid_at = None
        update_fields.append('paid_at')
    if payment_obj.stripe_payment_intent_id is not None:
        payment_obj.stripe_payment_intent_id = None
        update_fields.append('stripe_payment_intent_id')
    if payment_obj.stripe_charge_id is not None:
        payment_obj.stripe_charge_id = None
        update_fields.append('stripe_charge_id')

    if update_fields:
        payment_obj.save(update_fields=update_fields)

    return payment_obj


def _set_payment_gateway_references(
    payment_obj,
    *,
    provider='paymongo',
    session_id=None,
    payment_intent_id=None,
    payment_id=None,
    status=None,
    paid_at=None,
):
    update_fields = []

    if provider and payment_obj.payment_provider != provider:
        payment_obj.payment_provider = provider
        update_fields.append('payment_provider')
    if session_id is not None and payment_obj.stripe_session_id != session_id:
        payment_obj.stripe_session_id = session_id
        update_fields.append('stripe_session_id')
    if payment_intent_id is not None and payment_obj.stripe_payment_intent_id != payment_intent_id:
        payment_obj.stripe_payment_intent_id = payment_intent_id
        update_fields.append('stripe_payment_intent_id')
    if payment_id is not None and payment_obj.stripe_charge_id != payment_id:
        payment_obj.stripe_charge_id = payment_id
        update_fields.append('stripe_charge_id')
    if status and payment_obj.status != status:
        payment_obj.status = status
        update_fields.append('status')
    if paid_at is not None and payment_obj.paid_at != paid_at:
        payment_obj.paid_at = paid_at
        update_fields.append('paid_at')

    if update_fields:
        payment_obj.save(update_fields=update_fields)

    return payment_obj


def _get_or_create_payment_record(content_object, user, payment_type, amount, *, status='pending'):
    content_type = ContentType.objects.get_for_model(content_object.__class__)
    payment_obj, _created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=content_object.pk,
        defaults={
            'user': user,
            'payment_type': payment_type,
            'amount': Decimal(str(amount)).quantize(Decimal('0.01')),
            'currency': 'PHP',
            'status': status,
            'payment_provider': 'paymongo',
        },
    )

    if status == 'pending':
        return _prepare_pending_online_payment(payment_obj, amount=amount)

    update_fields = []
    normalized_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    if payment_obj.amount != normalized_amount:
        payment_obj.amount = normalized_amount
        update_fields.append('amount')
    if payment_obj.currency != 'PHP':
        payment_obj.currency = 'PHP'
        update_fields.append('currency')
    if payment_obj.status != status:
        payment_obj.status = status
        update_fields.append('status')
    if payment_obj.payment_provider != 'paymongo':
        payment_obj.payment_provider = 'paymongo'
        update_fields.append('payment_provider')
    if update_fields:
        payment_obj.save(update_fields=update_fields)
    return payment_obj


def _payment_urls(request, payment_type, item_id, transaction_id):
    success_url = request.build_absolute_uri(reverse('payment_success'))
    success_url += f'?type={payment_type}&id={item_id}&transaction_id={transaction_id}'

    cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
    cancel_url += f'?type={payment_type}&id={item_id}'
    return success_url, cancel_url


def _redirect_to_paymongo_checkout(
    request,
    *,
    payment_obj,
    payment_type,
    item_id,
    amount_php,
    item_name,
    description,
    extra_metadata=None,
):
    amount_php = Decimal(str(amount_php)).quantize(Decimal('0.01'))
    amount_centavos = int(amount_php * 100)
    success_url, cancel_url = _payment_urls(
        request,
        payment_type,
        item_id,
        payment_obj.internal_transaction_id,
    )

    metadata = {
        'type': payment_type,
        'item_id': str(item_id),
        'user_id': str(request.user.id),
        'internal_transaction_id': payment_obj.internal_transaction_id,
    }
    if extra_metadata:
        metadata.update({key: str(value) for key, value in extra_metadata.items()})

    checkout_session = _create_checkout_session_compat(
        amount_centavos=amount_centavos,
        name=item_name,
        description=description,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        reference_number=payment_obj.internal_transaction_id,
        customer_email=request.user.email or None,
        customer_name=request.user.get_full_name().strip() or request.user.username,
        payment_method_types=get_enabled_payment_methods(),
    )

    _set_payment_gateway_references(
        payment_obj,
        provider='paymongo',
        session_id=checkout_session.get('id'),
    )
    checkout_url = (checkout_session.get('attributes') or {}).get('checkout_url')
    return redirect(checkout_url, code=303)


def _payment_detail_url(payment_type, item_id):
    if payment_type == 'rental':
        return reverse('machines:rental_detail', kwargs={'pk': item_id})
    if payment_type == 'irrigation':
        return reverse('irrigation:irrigation_request_detail', kwargs={'pk': item_id})
    if payment_type == 'appointment':
        return reverse('machines:ricemill_appointment_detail', kwargs={'pk': item_id})
    if payment_type == 'dryer':
        return reverse('machines:dryer_rental_detail', kwargs={'pk': item_id})
    if payment_type == 'membership':
        return reverse('membership_slip')
    return reverse('dashboard')


def _payment_incomplete_redirect(payment_type, item_id):
    if payment_type == 'membership':
        return reverse('submit_membership_form')
    if payment_type == 'dryer':
        return reverse('machines:dryer_rental_detail', kwargs={'pk': item_id})
    return _payment_detail_url(payment_type, item_id)


def _get_payment_from_request(transaction_id, session_id, user):
    payment = None
    if transaction_id:
        payment = Payment.objects.filter(
            internal_transaction_id=transaction_id,
            user=user,
        ).first()
    if payment is None and session_id:
        payment = Payment.objects.filter(
            stripe_session_id=session_id,
            user=user,
        ).first()
    return payment


def _is_payment_already_processed(payment_type, item_id, user, payment=None, session_id=None):
    if payment_type == 'rental':
        rental = get_object_or_404(Rental, pk=item_id, user=user)
        if not rental.payment_date or rental.payment_method != 'online':
            return False
        if session_id and rental.stripe_session_id and rental.stripe_session_id != session_id:
            return False
        return True

    if payment_type == 'membership':
        from users.models import MembershipApplication

        membership = get_object_or_404(MembershipApplication, pk=item_id, user=user)
        return membership.payment_status == 'paid' and membership.payment_method == 'online'

    if payment is None:
        if payment_type == 'irrigation':
            irrigation_record = get_object_or_404(IrrigationSeasonRecord, pk=item_id, farmer=user)
            payment = _get_payment_for_object(irrigation_record)
        elif payment_type == 'appointment':
            appointment = get_object_or_404(RiceMillAppointment, pk=item_id, user=user)
            payment = _get_payment_for_object(appointment)
        elif payment_type == 'dryer':
            dryer_rental = get_object_or_404(DryerRental, pk=item_id, user=user)
            payment = _get_payment_for_object(dryer_rental)

    return bool(payment and payment.status == 'completed')


def _finalize_rental_payment(
    rental,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    already_processed = bool(
        rental.payment_date
        and rental.payment_method == 'online'
        and (not session_id or rental.stripe_session_id == session_id)
    )

    if already_processed:
        payment_obj = _get_payment_for_object(rental) or _get_or_create_payment_record(
            rental,
            user,
            'rental',
            paid_amount if paid_amount > 0 else (rental.payment_amount or Decimal('0.00')),
        )
        _set_payment_gateway_references(
            payment_obj,
            provider='paymongo',
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_id=external_payment_id,
        )
    else:
        payment_obj = record_rental_online_payment(
            rental,
            user,
            session_id,
            payment_intent_id=payment_intent_id,
            paid_amount=paid_amount,
            payment_provider='paymongo',
            external_payment_id=external_payment_id,
        )

        if notify:
            create_user_notification(
                user,
                'rental_payment_completed',
                f'Gcash payment recorded for {rental.machine.name}. Waiting for admin verification.',
                rental.id,
            )
            notify_staff(
                'rental_payment_received',
                (
                    f'Gcash payment received from {user.get_full_name() or user.username} '
                    f'for {rental.machine.name}. Please verify and complete the rental.'
                ),
                rental.id,
            )

    return {
        'payment': payment_obj,
        'redirect_url': reverse('machines:rental_detail', kwargs={'pk': rental.id}),
        'success_message': f'Gcash payment recorded for {rental.machine.name}. Waiting for admin verification.',
    }


def _finalize_irrigation_payment(
    irrigation_record,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    payment_obj = _get_payment_for_object(irrigation_record)
    already_processed = bool(
        payment_obj
        and payment_obj.status == 'completed'
        and (not session_id or payment_obj.stripe_session_id == session_id)
    )

    if not already_processed:
        if irrigation_record.payment_method != IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE:
            irrigation_record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
            irrigation_record.save(update_fields=['payment_method', 'updated_at'])

        payment_obj = upsert_payment_record(
            irrigation_record,
            user,
            'irrigation',
            paid_amount if paid_amount > 0 else (irrigation_record.balance_due or irrigation_record.total_fee),
            'PHP',
            'completed',
            session_id,
            payment_intent_id=payment_intent_id,
            payment_provider='paymongo',
            external_payment_id=external_payment_id,
        )
        if notify:
            create_user_notification(
                user,
                'irrigation_payment_completed',
                f'Gcash payment recorded for your irrigation billing in {irrigation_record.season.name}. Waiting for admin confirmation.',
                irrigation_record.id,
            )
            log_activity(
                activity_type='payment',
                actor=user,
                subject_user=user,
                title=f'Gcash irrigation payment recorded for {irrigation_record.season.name}',
                description='Payment is on file and waiting for staff confirmation.',
                related_object=irrigation_record,
                created_at=payment_obj.paid_at,
            )
            notify_staff(
                'irrigation_payment_completed',
                f'Gcash irrigation payment received from {user.get_full_name() or user.username} for {irrigation_record.season.name}. Please confirm payment.',
                irrigation_record.id,
            )
    else:
        _set_payment_gateway_references(
            payment_obj,
            provider='paymongo',
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_id=external_payment_id,
        )

    return {
        'payment': payment_obj,
        'redirect_url': reverse('irrigation:irrigation_request_detail', kwargs={'pk': irrigation_record.pk}),
        'success_message': 'Gcash payment recorded. Waiting for admin confirmation.',
    }


def _finalize_appointment_payment(
    appointment,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    payment_obj = _get_payment_for_object(appointment)
    already_processed = bool(
        payment_obj
        and payment_obj.status == 'completed'
        and (not session_id or payment_obj.stripe_session_id == session_id)
    )

    if not already_processed:
        appointment.status = 'paid'
        appointment.payment_method = 'online'
        appointment.save(update_fields=['status', 'payment_method', 'updated_at'])
        payment_obj = upsert_payment_record(
            appointment,
            user,
            'appointment',
            paid_amount if paid_amount > 0 else appointment.total_amount,
            'PHP',
            'completed',
            session_id,
            payment_intent_id=payment_intent_id,
            payment_provider='paymongo',
            external_payment_id=external_payment_id,
        )
        if notify:
            create_user_notification(
                user,
                'appointment_payment_completed',
                f'Gcash payment recorded for your rice mill appointment on {appointment.appointment_date}. Waiting for admin confirmation.',
                appointment.id,
            )
            notify_staff(
                'appointment_payment_completed',
                f'Gcash payment received for the rice mill appointment of {user.get_full_name() or user.username} on {appointment.appointment_date}. Please confirm payment.',
                appointment.id,
            )
    else:
        _set_payment_gateway_references(
            payment_obj,
            provider='paymongo',
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_id=external_payment_id,
        )

    return {
        'payment': payment_obj,
        'redirect_url': reverse('machines:ricemill_appointment_detail', kwargs={'pk': appointment.id}),
        'success_message': 'Gcash payment recorded. Waiting for admin confirmation.',
    }


def _finalize_dryer_payment(
    dryer_rental,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    payment_obj = _get_payment_for_object(dryer_rental)
    already_processed = bool(
        payment_obj
        and payment_obj.status == 'completed'
        and dryer_rental.status == 'paid'
        and (not session_id or payment_obj.stripe_session_id == session_id)
    )

    if not already_processed:
        dryer_rental.status = 'paid'
        dryer_rental.payment_method = 'online'
        dryer_rental.save(update_fields=['status', 'payment_method', 'updated_at'])
        payment_obj = upsert_payment_record(
            dryer_rental,
            user,
            'dryer',
            paid_amount if paid_amount > 0 else dryer_rental.total_amount,
            'PHP',
            'completed',
            session_id,
            payment_intent_id=payment_intent_id,
            payment_provider='paymongo',
            external_payment_id=external_payment_id,
        )
        if notify:
            create_user_notification(
                user,
                'dryer_payment_completed',
                f'Gcash payment recorded for your dryer rental on {dryer_rental.rental_date}. Waiting for admin confirmation.',
                dryer_rental.id,
            )
            notify_staff(
                'dryer_payment_completed',
                f'Gcash payment received for the dryer rental of {user.get_full_name() or user.username} on {dryer_rental.rental_date} {dryer_rental.display_time_range}. Please confirm payment.',
                dryer_rental.id,
            )
    else:
        _set_payment_gateway_references(
            payment_obj,
            provider='paymongo',
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_id=external_payment_id,
        )

    return {
        'payment': payment_obj,
        'redirect_url': reverse('machines:dryer_rental_detail', kwargs={'pk': dryer_rental.id}),
        'success_message': 'Gcash payment recorded. Waiting for admin confirmation.',
    }


def _finalize_membership_payment(
    membership,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    already_processed = membership.payment_status == 'paid' and membership.payment_method == 'online'

    if not already_processed:
        payment_obj = record_membership_online_payment(
            membership,
            user,
            session_id,
            payment_intent_id=payment_intent_id,
            paid_amount=paid_amount,
            payment_provider='paymongo',
            external_payment_id=external_payment_id,
        )
        if notify:
            transaction_id = payment_obj.internal_transaction_id
            create_user_notification(
                user,
                'membership',
                f'Payment successful! Your membership fee has been paid (Transaction ID: {transaction_id}). Your application is now pending admin approval.',
                membership.pk,
            )
            admins = notify_staff(
                'membership',
                f'Membership payment received from {user.get_full_name() or user.username} (Transaction ID: {transaction_id}). Application is ready for review.',
                membership.pk,
            )
            notify_named_user(
                'hazel',
                'osorio',
                'membership',
                f'Membership payment received from {user.get_full_name() or user.username} (Transaction ID: {transaction_id}). Application is ready for review.',
                membership.pk,
                exclude_users=admins,
            )
    else:
        payment_obj = _get_payment_for_object(membership) or _get_or_create_payment_record(
            membership,
            user,
            'membership',
            paid_amount if paid_amount > 0 else Decimal('500.00'),
            status='completed',
        )
        _set_payment_gateway_references(
            payment_obj,
            provider='paymongo',
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_id=external_payment_id,
            status='completed',
            paid_at=membership.payment_date or timezone.now(),
        )

    return {
        'payment': payment_obj,
        'redirect_url': reverse('membership_slip'),
        'success_message': (
            'Payment successful! Your membership fee has been paid. '
            f'Transaction ID: {payment_obj.internal_transaction_id}. Your application is now pending admin approval.'
        ),
    }


def _finalize_payment(
    payment_type,
    item_id,
    user,
    *,
    session_id,
    paid_amount,
    payment_intent_id=None,
    external_payment_id=None,
    notify=True,
):
    if payment_type == 'rental':
        rental = get_object_or_404(Rental, pk=item_id, user=user)
        if rental.payment_method != 'online':
            raise PayMongoAPIError('This rental is no longer set to Gcash payment.')
        return _finalize_rental_payment(
            rental,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=notify,
        )

    if payment_type == 'irrigation':
        irrigation_record = get_object_or_404(IrrigationSeasonRecord, pk=item_id, farmer=user)
        return _finalize_irrigation_payment(
            irrigation_record,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=notify,
        )

    if payment_type == 'appointment':
        appointment = get_object_or_404(RiceMillAppointment, pk=item_id, user=user)
        if appointment.payment_method != 'online':
            raise PayMongoAPIError('This rice mill appointment is no longer set to Gcash payment.')
        return _finalize_appointment_payment(
            appointment,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=notify,
        )

    if payment_type == 'dryer':
        dryer_rental = get_object_or_404(DryerRental, pk=item_id, user=user)
        if dryer_rental.payment_method != 'online':
            raise PayMongoAPIError('This dryer rental is no longer set to Gcash payment.')
        return _finalize_dryer_payment(
            dryer_rental,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=notify,
        )

    if payment_type == 'membership':
        from users.models import MembershipApplication

        membership = get_object_or_404(MembershipApplication, pk=item_id, user=user)
        return _finalize_membership_payment(
            membership,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=notify,
        )

    raise PayMongoAPIError('Unsupported payment type.')


@login_required
def create_rental_payment(request, rental_id):
    rental = get_object_or_404(Rental, pk=rental_id, user=request.user)

    if rental.payment_type == 'in_kind':
        messages.info(request, 'This rental uses non-cash payment settlement. Gcash payment is not required.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.payment_method != 'online':
        messages.info(request, 'This rental is configured for over-the-counter payment, not Gcash checkout.')
        return redirect('machines:rental_detail', pk=rental_id)

    if not _stripe_is_configured():
        messages.error(request, 'Gcash payment is not configured. Please contact administrator.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.status != 'approved':
        messages.info(request, 'Gcash payment becomes available after the rental is approved by admin.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.payment_verified or rental.payment_status == 'paid':
        messages.info(request, 'This rental payment has already been verified.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.payment_date or rental.stripe_session_id:
        messages.info(request, 'Your Gcash payment is already on file and is waiting for admin verification.')
        return redirect('machines:rental_detail', pk=rental_id)

    try:
        recalculated_amount = rental.calculate_payment_amount()
        if recalculated_amount <= 0:
            messages.error(request, 'Unable to calculate rental amount. Please contact administrator.')
            return redirect('machines:rental_detail', pk=rental_id)
        if recalculated_amount > ONLINE_CHECKOUT_MAX_AMOUNT_PHP:
            messages.error(
                request,
                (
                    f'Online payment is limited to PHP {ONLINE_CHECKOUT_MAX_AMOUNT_PHP:,.2f} per transaction. '
                    f'This rental total is PHP {recalculated_amount:,.2f}. '
                    'Please contact admin to switch to over-the-counter payment or split the booking.'
                ),
            )
            return redirect('machines:rental_detail', pk=rental_id)

        if rental.payment_amount != recalculated_amount:
            rental.payment_amount = recalculated_amount
            rental.save(update_fields=['payment_amount'])

        payment_obj = _get_or_create_payment_record(
            rental,
            request.user,
            'rental',
            rental.payment_amount or recalculated_amount,
        )
        return _redirect_to_paymongo_checkout(
            request,
            payment_obj=payment_obj,
            payment_type='rental',
            item_id=rental_id,
            amount_php=rental.payment_amount or recalculated_amount,
            item_name=f'Machine Rental: {rental.machine.name}',
            description=(
                f'Rental from {rental.start_date} to {rental.end_date} - {rental.area} hectares'
                if rental.area
                else f'Rental from {rental.start_date} to {rental.end_date}'
            ),
            extra_metadata={
                'rental_id': rental_id,
                'area': str(rental.area) if rental.area else '0',
                'amount': str(rental.payment_amount or recalculated_amount or '0'),
            },
        )
    except PayMongoAPIError as exc:
        messages.error(request, f'Error creating payment session: {exc}')
        return redirect('machines:rental_detail', pk=rental_id)


@login_required
def create_irrigation_payment(request, irrigation_id):
    irrigation_record = get_object_or_404(IrrigationSeasonRecord, pk=irrigation_id, farmer=request.user)

    if not _stripe_is_configured():
        messages.error(request, 'Gcash payment is not configured. Please contact administrator.')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)

    if irrigation_record.status != IrrigationSeasonRecord.STATUS_HARVESTED or irrigation_record.balance_due <= 0:
        messages.info(request, 'Gcash payment is only available after irrigation billing is generated and while the balance is still unpaid.')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)

    if irrigation_record.payment_method != IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE:
        messages.info(request, 'Please choose Gcash payment first before opening PayMongo checkout.')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)

    try:
        amount_php = Decimal(str(irrigation_record.balance_due or irrigation_record.total_fee or '0')).quantize(Decimal('0.01'))
        if amount_php <= 0:
            messages.error(request, 'Unable to calculate irrigation billing amount.')
            return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)
        if amount_php > ONLINE_CHECKOUT_MAX_AMOUNT_PHP:
            messages.error(
                request,
                (
                    f'Online payment is limited to PHP {ONLINE_CHECKOUT_MAX_AMOUNT_PHP:,.2f} per transaction. '
                    f'This irrigation balance is PHP {amount_php:,.2f}. Please contact BUFIA staff.'
                ),
            )
            return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)

        payment_obj = _get_or_create_payment_record(
            irrigation_record,
            request.user,
            'irrigation',
            amount_php,
        )
        if payment_obj.status == 'completed':
            messages.info(request, 'Your Gcash payment is already on file and is waiting for staff confirmation.')
            return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)

        return _redirect_to_paymongo_checkout(
            request,
            payment_obj=payment_obj,
            payment_type='irrigation',
            item_id=irrigation_id,
            amount_php=amount_php,
            item_name=f'Irrigation Billing: {irrigation_record.season.name}',
            description=f'{irrigation_record.farm_area} hectares @ PHP {irrigation_record.irrigation_rate}/ha',
            extra_metadata={
                'irrigation_record_id': irrigation_id,
                'amount': str(amount_php),
            },
        )
    except PayMongoAPIError as exc:
        messages.error(request, f'Error creating payment session: {exc}')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)


@login_required
def create_appointment_payment(request, appointment_id):
    appointment = get_object_or_404(RiceMillAppointment, pk=appointment_id, user=request.user)
    if not _stripe_is_configured():
        messages.error(request, 'Gcash payment is not configured. Please contact administrator.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)

    if appointment.payment_method != 'online':
        messages.info(request, 'This rice mill appointment is set for over-the-counter payment.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)

    if appointment.status != 'paid':
        messages.info(request, 'Gcash payment will be available after BUFIA staff records the final milled weight.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)

    try:
        amount_php = Decimal(str(appointment.total_amount)).quantize(Decimal('0.01'))
        payment_obj = _get_or_create_payment_record(
            appointment,
            request.user,
            'appointment',
            amount_php,
        )
        if payment_obj.status == 'completed':
            messages.info(request, 'Your Gcash payment is already recorded and is waiting for admin confirmation.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment_id)

        return _redirect_to_paymongo_checkout(
            request,
            payment_obj=payment_obj,
            payment_type='appointment',
            item_id=appointment_id,
            amount_php=amount_php,
            item_name=f'Rice Mill Appointment: {appointment.machine.name}',
            description=(
                f'{appointment.appointment_date} '
                f'({appointment.final_weight or appointment.estimated_weight} kg @ PHP {appointment.price_per_kg}/kg)'
            ),
            extra_metadata={'appointment_id': appointment.id},
        )
    except PayMongoAPIError as exc:
        messages.error(request, f'Error creating payment session: {exc}')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)


@login_required
def create_dryer_payment(request, dryer_rental_id):
    dryer_rental = get_object_or_404(DryerRental, pk=dryer_rental_id, user=request.user)

    if not _stripe_is_configured():
        messages.error(request, 'Gcash payment is not configured. Please contact administrator.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)

    if dryer_rental.status != 'paid':
        messages.info(request, 'Gcash payment is only available after staff records the final dryer amount.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)

    if dryer_rental.payment_method != 'online':
        messages.info(request, 'This dryer rental is set for over-the-counter payment.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)

    if dryer_rental.total_amount <= 0:
        messages.info(request, 'The final dryer amount has not been recorded yet.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)

    try:
        amount_php = Decimal(str(dryer_rental.total_amount)).quantize(Decimal('0.01'))
        if dryer_rental.is_hourly_pricing:
            description = (
                f'{dryer_rental.rental_date} '
                f'({dryer_rental.actual_drying_hours or dryer_rental.duration_hours} hrs @ '
                f'PHP {dryer_rental.effective_hourly_rate}/hr)'
            )
        else:
            description = (
                f'{dryer_rental.rental_date} {dryer_rental.quantity or "Dryer service"} '
                f'@ PHP {dryer_rental.effective_hourly_rate}/'
                f'{"sack" if dryer_rental.is_per_sack_pricing else "hour"}'
            )
        payment_obj = _get_or_create_payment_record(
            dryer_rental,
            request.user,
            'dryer',
            amount_php,
        )
        if payment_obj.status == 'completed':
            messages.info(request, 'Your Gcash payment is already recorded and is waiting for admin confirmation.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)

        return _redirect_to_paymongo_checkout(
            request,
            payment_obj=payment_obj,
            payment_type='dryer',
            item_id=dryer_rental_id,
            amount_php=amount_php,
            item_name=f'Dryer Rental: {dryer_rental.machine.name}',
            description=description,
            extra_metadata={'dryer_rental_id': dryer_rental.id},
        )
    except PayMongoAPIError as exc:
        messages.error(request, f'Error creating payment session: {exc}')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental_id)


@login_required
def _legacy_payment_success(request):
    return payment_success(request)


@login_required
def payment_cancelled(request):
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')

    messages.warning(request, 'Payment was cancelled. You can try again when ready.')

    if payment_type == 'rental':
        return redirect('machines:rental_detail', pk=item_id)
    if payment_type == 'irrigation':
        return redirect('irrigation:irrigation_request_detail', pk=item_id)
    if payment_type == 'appointment':
        return redirect('machines:ricemill_appointment_detail', pk=item_id)
    if payment_type == 'dryer':
        return redirect('machines:dryer_rental_detail', pk=item_id)
    if payment_type == 'membership':
        return redirect('submit_membership_form')

    return redirect('dashboard')


@csrf_exempt
def paymongo_webhook(request):
    logger = logging.getLogger('bufia.payments.paymongo')
    raw_payload = request.body
    signature = request.META.get('HTTP_PAYMONGO_SIGNATURE')

    if request.method != 'POST':
        return HttpResponse(status=405)

    if not _paymongo_is_configured():
        logger.error('PayMongo webhook received but PayMongo is not configured.')
        return HttpResponse(status=503)

    try:
        if settings.PAYMONGO_WEBHOOK_SECRET and not paymongo_verify_webhook_signature(
            raw_payload,
            signature,
            settings.PAYMONGO_WEBHOOK_SECRET,
        ):
            logger.error('Invalid PayMongo webhook signature.')
            return HttpResponse(status=400)

        payload = json.loads(raw_payload.decode('utf-8'))
    except json.JSONDecodeError as exc:
        logger.error('Invalid PayMongo webhook payload: %s', exc)
        return HttpResponse(status=400)

    event_attributes = payload.get('data', {}).get('attributes', {})
    event_type = event_attributes.get('type')
    if event_type != 'checkout_session.payment.paid':
        logger.info('Ignoring unsupported PayMongo webhook event: %s', event_type)
        return HttpResponse(status=200)

    session_payload = event_attributes.get('data') or {}
    session_attributes = session_payload.get('attributes') or {}
    metadata = session_attributes.get('metadata') or {}
    payment_type = metadata.get('type') or metadata.get('payment_type')
    item_id = metadata.get('item_id')
    transaction_id = metadata.get('internal_transaction_id')
    session_id = session_payload.get('id')
    payment_intent_id = paymongo_extract_payment_intent_id(session_payload)
    external_payment_id = paymongo_extract_payment_id(session_payload)
    paid_amount = paymongo_extract_paid_amount(session_payload)

    payment_record = None
    if transaction_id:
        payment_record = Payment.objects.filter(internal_transaction_id=transaction_id).first()
    if payment_record is None and session_id:
        payment_record = Payment.objects.filter(stripe_session_id=session_id).first()

    user = payment_record.user if payment_record else None
    user_id = metadata.get('user_id')
    if user is None and user_id:
        user = get_user_model().objects.filter(pk=user_id).first()

    if not payment_type or not item_id or user is None:
        logger.error(
            'Unable to resolve PayMongo webhook payment context. type=%s item_id=%s transaction_id=%s session_id=%s',
            payment_type,
            item_id,
            transaction_id,
            session_id,
        )
        return HttpResponse(status=200)

    try:
        result = _finalize_payment(
            payment_type,
            item_id,
            user,
            session_id=session_id,
            paid_amount=paid_amount,
            payment_intent_id=payment_intent_id,
            external_payment_id=external_payment_id,
            notify=True,
        )
        logger.info(
            'PayMongo webhook processed successfully: %s %s %s',
            payment_type,
            result['payment'].internal_transaction_id if result.get('payment') else 'N/A',
            session_id,
        )
    except Exception as exc:
        logger.exception('Error processing PayMongo webhook: %s', exc)

    return HttpResponse(status=200)


stripe_webhook = paymongo_webhook


@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')
    transaction_id = request.GET.get('transaction_id')

    if not session_id and not transaction_id:
        messages.error(request, 'Invalid payment session.')
        return redirect('dashboard')

    payment = _get_payment_from_request(transaction_id, session_id, request.user)
    if payment:
        payment_type = payment_type or payment.payment_type
        item_id = item_id or str(payment.object_id)
        transaction_id = payment.internal_transaction_id

    if not payment_type or not item_id:
        messages.error(request, 'Unable to resolve the payment record.')
        return redirect('dashboard')

    if _is_payment_already_processed(payment_type, item_id, request.user, payment, session_id):
        messages.success(request, 'Your payment has already been recorded.')
        return redirect(_payment_detail_url(payment_type, item_id))

    if not _stripe_is_configured():
        messages.error(request, 'Gcash payment is not configured. Please contact administrator.')
        return redirect(_payment_detail_url(payment_type, item_id))

    checkout_session_id = session_id or (payment.stripe_session_id if payment else None)
    if not checkout_session_id:
        messages.warning(request, 'Payment is being processed. Please check back later.')
        return redirect(_payment_incomplete_redirect(payment_type, item_id))

    try:
        session = _retrieve_checkout_session_compat(checkout_session_id)
        if not paymongo_checkout_session_is_successful(session):
            if payment_type == 'membership':
                messages.warning(request, 'Your membership payment is not completed yet. Please choose a payment method again or finish the PayMongo checkout.')
            elif payment_type == 'dryer':
                messages.warning(request, 'Your dryer payment is not completed yet. Please finish the PayMongo checkout to keep your booking moving.')
            else:
                messages.warning(request, 'Payment is being processed. Please check back later.')
            return redirect(_payment_incomplete_redirect(payment_type, item_id))

        result = _finalize_payment(
            payment_type,
            item_id,
            request.user,
            session_id=checkout_session_id,
            paid_amount=paymongo_extract_paid_amount(session),
            payment_intent_id=paymongo_extract_payment_intent_id(session),
            external_payment_id=paymongo_extract_payment_id(session),
            notify=True,
        )
        messages.success(request, result['success_message'])
        return redirect(result['redirect_url'])
    except PayMongoAPIError as exc:
        messages.error(request, f'Error verifying payment: {exc}')
        return redirect(_payment_detail_url(payment_type, item_id))


@login_required
def create_membership_payment(request, membership_id):
    from users.models import MembershipApplication

    membership = get_object_or_404(MembershipApplication, pk=membership_id, user=request.user)

    if not _stripe_is_configured():
        messages.error(
            request,
            'Gcash payment is currently unavailable because PayMongo is not configured. '
            'Please contact the administrator or choose over-the-counter payment.',
        )
        return redirect('profile')

    if membership.is_approved:
        messages.info(request, 'Your membership has already been approved.')
        return redirect('profile')

    if membership.payment_status == 'paid':
        messages.info(request, 'Your membership fee has already been paid.')
        return redirect('profile')

    try:
        payment_obj = _get_or_create_payment_record(
            membership,
            request.user,
            'membership',
            Decimal('500.00'),
        )
        return _redirect_to_paymongo_checkout(
            request,
            payment_obj=payment_obj,
            payment_type='membership',
            item_id=membership_id,
            amount_php=Decimal('500.00'),
            item_name='BUFIA Membership Fee',
            description=f'Membership registration fee for {request.user.get_full_name() or request.user.username}',
            extra_metadata={'membership_id': membership_id},
        )
    except PayMongoAPIError as exc:
        messages.error(request, f'Error creating payment session: {exc}')
        return redirect('profile')


def _payment_filters_from_request(request):
    return {
        'search_query': (request.GET.get('search') or '').strip(),
        'status_filter': (request.GET.get('status') or '').strip(),
        'payment_type_filter': (request.GET.get('payment_type') or '').strip(),
        'date_from': (request.GET.get('date_from') or '').strip(),
        'date_to': (request.GET.get('date_to') or '').strip(),
    }


def _filtered_payments_queryset(filters, include_content_type=False):
    related_fields = ['user']
    if include_content_type:
        related_fields.append('content_type')

    payments = Payment.objects.select_related(*related_fields).order_by('-created_at')

    search_query = filters['search_query']
    if search_query:
        payments = payments.filter(
            Q(internal_transaction_id__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    if filters['status_filter']:
        payments = payments.filter(status=filters['status_filter'])

    if filters['payment_type_filter']:
        payments = payments.filter(payment_type=filters['payment_type_filter'])

    if filters['date_from']:
        payments = payments.filter(created_at__date__gte=filters['date_from'])

    if filters['date_to']:
        payments = payments.filter(created_at__date__lte=filters['date_to'])

    return payments


def _payment_export_filter_details(filters):
    status_label = dict(Payment.PAYMENT_STATUS_CHOICES).get(filters['status_filter'], '')
    type_label = dict(Payment.PAYMENT_TYPE_CHOICES).get(filters['payment_type_filter'], '')

    if filters['date_from'] and filters['date_to']:
        date_label = f"{filters['date_from']} to {filters['date_to']}"
    elif filters['date_from']:
        date_label = f"From {filters['date_from']}"
    elif filters['date_to']:
        date_label = f"Until {filters['date_to']}"
    else:
        date_label = ''

    return [
        ('Search', filters['search_query']),
        ('Status', status_label),
        ('Type', type_label),
        ('Date', date_label),
    ]


def _payment_export_rows(payments):
    rows = []
    for payment in payments:
        member_name = payment.user.get_full_name().strip() or payment.user.username
        rows.append([
            payment.internal_transaction_id or 'N/A',
            payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            member_name,
            payment.user.email or 'No email',
            payment.get_payment_type_display(),
            f"{payment.currency} {payment.amount}",
            f"{payment.currency} {payment.amount_received}" if payment.amount_received is not None else 'N/A',
            f"{payment.currency} {payment.change_given}" if payment.change_given is not None else 'N/A',
            payment.payment_channel_display,
            (payment.processed_by.get_full_name().strip() or payment.processed_by.username) if payment.processed_by_id else 'N/A',
            payment.get_status_display(),
            payment.provider_display_name,
        ])
    return rows


def _payment_export_filename(prefix, extension):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    return f'{prefix}_{timestamp}.{extension}'


@staff_member_required
def admin_payment_list(request):
    filters = _payment_filters_from_request(request)
    payments = _filtered_payments_queryset(filters, include_content_type=True)

    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for payment in page_obj:
        payment.related_object = payment.content_object

    context = {
        'page_obj': page_obj,
        'search_query': filters['search_query'],
        'status_filter': filters['status_filter'],
        'payment_type_filter': filters['payment_type_filter'],
        'date_from': filters['date_from'],
        'date_to': filters['date_to'],
        'status_choices': Payment.PAYMENT_STATUS_CHOICES,
        'payment_type_choices': Payment.PAYMENT_TYPE_CHOICES,
        'total_count': paginator.count,
        'total_amount_due': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_amount_received': payments.aggregate(total=Sum('amount_received'))['total'] or 0,
        'total_change_given': payments.aggregate(total=Sum('change_given'))['total'] or 0,
        'over_counter_count': payments.filter(amount_received__isnull=False).count(),
        'gcash_count': payments.filter(stripe_session_id__isnull=False).count(),
        'completed_count': payments.filter(status='completed').count(),
        'pending_count': payments.filter(status='pending').count(),
    }
    context['other_manual_count'] = max(
        context['total_count'] - context['gcash_count'] - context['over_counter_count'],
        0,
    )
    context['other_status_count'] = max(
        context['total_count'] - context['completed_count'] - context['pending_count'],
        0,
    )

    return render(request, 'payments/admin_payment_list.html', context)


@staff_member_required
def admin_payment_detail(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('user', 'processed_by').prefetch_related('refunds__refunded_by'),
        pk=payment_id,
    )
    related_object = payment.content_object
    refund_form = RefundForm(payment=payment)

    if request.method == 'POST':
        if not payment.can_accept_refunds:
            messages.error(request, 'This payment cannot accept additional refunds.')
            return redirect('admin_payment_detail', payment_id=payment.id)

        refund_form = RefundForm(request.POST, payment=payment)
        if refund_form.is_valid():
            refund = refund_form.save(commit=False)
            refund.payment = payment
            refund.status = 'refunded'
            refund.refunded_by = request.user
            refund.refunded_at = timezone.now()
            refund.save()

            payment.refresh_from_db(fields=['status'])
            target_status = 'refunded' if payment.refundable_balance == Decimal('0.00') else 'completed'
            if payment.status != target_status:
                payment.status = target_status
                payment.save(update_fields=['status', 'updated_at'])

            messages.success(request, 'Refund recorded successfully.')
            return redirect('admin_payment_detail', payment_id=payment.id)

        messages.error(request, 'Please correct the refund form and try again.')

    context = {
        'payment': payment,
        'related_object': related_object,
        'refund_form': refund_form,
        'refund_history': payment.refunds.select_related('refunded_by').all(),
    }

    return render(request, 'payments/admin_payment_detail.html', context)


@staff_member_required
def export_payments(request):
    filters = _payment_filters_from_request(request)
    payments = _filtered_payments_queryset(filters)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID',
        'Date',
        'Member Name',
        'Member Email',
        'Payment Type',
        'Amount',
        'Currency',
        'Status',
        'Payment Provider',
        'Checkout Session ID',
    ])

    for payment in payments:
        member_name = payment.user.get_full_name().strip() or payment.user.username
        writer.writerow([
            payment.internal_transaction_id or 'N/A',
            payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            member_name,
            payment.user.email,
            payment.get_payment_type_display(),
            payment.amount,
            payment.currency,
            payment.get_status_display(),
            payment.provider_display_name,
            payment.checkout_session_reference or 'N/A',
        ])

    return response


@staff_member_required
def export_payments_excel(request):
    filters = _payment_filters_from_request(request)
    payments = _filtered_payments_queryset(filters)
    headers = ['Transaction ID', 'Date', 'Member', 'Email', 'Type', 'Amount', 'Status', 'Provider']
    headers = ['Transaction ID', 'Date', 'Member', 'Email', 'Type', 'Amount Due', 'Cash Received', 'Change Given', 'Channel', 'Processed By', 'Status', 'Provider']
    rows = _payment_export_rows(payments)
    response = HttpResponse(
        build_xlsx_bytes(
            title='Payment Transactions Filtered Report',
            filter_details=_payment_export_filter_details(filters),
            headers=headers,
            rows=rows,
            column_widths=[21, 18, 20, 24, 14, 14, 14, 14, 16, 18, 12, 14],
            sheet_name='Payments',
        ),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{_payment_export_filename("payments_export", "xlsx")}"'
    return response


@staff_member_required
def export_payments_pdf(request):
    filters = _payment_filters_from_request(request)
    payments = _filtered_payments_queryset(filters)
    headers = ['Transaction ID', 'Date', 'Member', 'Email', 'Type', 'Amount Due', 'Cash Received', 'Change Given', 'Channel', 'Processed By', 'Status', 'Provider']
    rows = _payment_export_rows(payments)
    response = HttpResponse(
        build_pdf_bytes(
            title='Payment Transactions Filtered Report',
            filter_details=_payment_export_filter_details(filters),
            headers=headers,
            rows=rows,
            column_widths=[18, 13, 16, 22, 11, 11, 11, 11, 13, 16, 10, 12],
        ),
        content_type='application/pdf',
    )
    disposition = 'inline' if (request.GET.get('preview') or '').strip().lower() in {'1', 'true', 'yes'} else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{_payment_export_filename("payments_export", "pdf")}"'
    return response
