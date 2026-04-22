from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from bufia.models import Payment
from machines.models import Rental
from notifications.models import UserNotification
from users.activity import log_activity


def upsert_payment_record(
    content_object,
    user,
    payment_type,
    amount,
    currency,
    status,
    session_id,
    payment_intent_id=None,
    *,
    payment_provider='paymongo',
    external_payment_id=None,
):
    """Create or update the canonical payment record for a content object."""
    content_type = ContentType.objects.get_for_model(content_object.__class__)
    payment_obj, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=content_object.pk,
        defaults={
            'user': user,
            'payment_type': payment_type,
            'amount': amount,
            'currency': currency,
            'status': status,
            'payment_provider': payment_provider,
            'stripe_session_id': session_id,
            'stripe_payment_intent_id': payment_intent_id,
            'stripe_charge_id': external_payment_id,
            'paid_at': timezone.now(),
        }
    )

    update_fields = []
    if not created and payment_obj.amount != amount:
        payment_obj.amount = amount
        update_fields.append('amount')
    if payment_obj.status != status:
        payment_obj.status = status
        update_fields.append('status')
    if payment_obj.currency != currency:
        payment_obj.currency = currency
        update_fields.append('currency')
    if payment_provider and payment_obj.payment_provider != payment_provider:
        payment_obj.payment_provider = payment_provider
        update_fields.append('payment_provider')
    if payment_obj.stripe_session_id != session_id:
        payment_obj.stripe_session_id = session_id
        update_fields.append('stripe_session_id')
    if payment_obj.stripe_payment_intent_id != payment_intent_id:
        payment_obj.stripe_payment_intent_id = payment_intent_id
        update_fields.append('stripe_payment_intent_id')
    if external_payment_id is not None and payment_obj.stripe_charge_id != external_payment_id:
        payment_obj.stripe_charge_id = external_payment_id
        update_fields.append('stripe_charge_id')
    if payment_obj.paid_at is None:
        payment_obj.paid_at = timezone.now()
        update_fields.append('paid_at')

    if update_fields:
        payment_obj.save(update_fields=update_fields)

    return payment_obj


def create_user_notification(user, notification_type, message, related_object_id):
    UserNotification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        related_object_id=related_object_id,
    )


def notify_staff(notification_type, message, related_object_id):
    user_model = get_user_model()
    admins = list(user_model.objects.filter(is_staff=True))
    for admin in admins:
        create_user_notification(admin, notification_type, message, related_object_id)
    return admins


def notify_named_user(first_name, last_name, notification_type, message, related_object_id, exclude_users=None):
    user_model = get_user_model()
    exclude_ids = [user.pk for user in (exclude_users or [])]
    target = user_model.objects.filter(
        first_name__icontains=first_name,
        last_name__icontains=last_name,
    ).exclude(pk__in=exclude_ids).first()
    if target:
        create_user_notification(target, notification_type, message, related_object_id)


def record_rental_online_payment(
    rental,
    user,
    session_id,
    payment_intent_id=None,
    paid_amount=None,
    *,
    payment_provider='paymongo',
    external_payment_id=None,
):
    """Persist a successful online rental payment while waiting for admin verification."""
    rental.payment_verified = False
    rental.payment_method = 'online'
    rental.payment_date = timezone.now()
    rental.stripe_session_id = session_id
    rental.payment_status = 'pending'
    if paid_amount and paid_amount > 0:
        rental.payment_amount = paid_amount
    rental.save()

    amount = paid_amount if paid_amount and paid_amount > 0 else (rental.payment_amount or 0)
    payment_record = upsert_payment_record(
        rental,
        user,
        'rental',
        amount,
        'PHP',
        'pending',
        session_id,
        payment_intent_id=payment_intent_id,
        payment_provider=payment_provider,
        external_payment_id=external_payment_id,
    )
    log_activity(
        activity_type='payment',
        actor=user,
        subject_user=user,
        title=f'Online rental payment recorded for {rental.machine.name}',
        description=f'Payment is on file and waiting for staff verification. Amount: PHP {amount}.',
        related_object=rental,
        created_at=rental.payment_date,
    )
    return payment_record


def record_membership_online_payment(
    membership,
    user,
    session_id,
    payment_intent_id=None,
    paid_amount=None,
    *,
    payment_provider='paymongo',
    external_payment_id=None,
):
    """Persist a successful online membership payment."""
    amount = paid_amount if paid_amount and paid_amount > 0 else Decimal('500.00')

    membership.payment_status = 'paid'
    membership.payment_method = 'online'
    membership.payment_date = timezone.now()
    membership.save(update_fields=['payment_status', 'payment_method', 'payment_date'])

    payment_record = upsert_payment_record(
        membership,
        user,
        'membership',
        amount,
        'PHP',
        'completed',
        session_id,
        payment_intent_id=payment_intent_id,
        payment_provider=payment_provider,
        external_payment_id=external_payment_id,
    )
    log_activity(
        activity_type='payment',
        actor=user,
        subject_user=user,
        title=f'{user.get_full_name() or user.username} completed the membership payment',
        description='Membership payment was received and is waiting for admin review.',
        related_object=membership,
        created_at=membership.payment_date,
    )
    return payment_record


def sync_membership_payment_record(membership, *, processed_by=None):
    """Keep the canonical membership payment record aligned with admin/manual updates."""
    amount = Decimal('500.00')
    content_type = ContentType.objects.get_for_model(membership.__class__)
    existing_record = Payment.objects.filter(
        content_type=content_type,
        object_id=membership.pk,
        payment_type='membership',
    ).first()

    if membership.payment_status != 'paid':
        if existing_record is None:
            return None

        update_fields = []
        if existing_record.amount != amount:
            existing_record.amount = amount
            update_fields.append('amount')
        if existing_record.currency != 'PHP':
            existing_record.currency = 'PHP'
            update_fields.append('currency')
        if existing_record.status != 'pending':
            existing_record.status = 'pending'
            update_fields.append('status')
        if existing_record.amount_received is not None:
            existing_record.amount_received = None
            update_fields.append('amount_received')
        if existing_record.change_given != Decimal('0.00'):
            existing_record.change_given = Decimal('0.00')
            update_fields.append('change_given')
        if existing_record.processed_by_id is not None:
            existing_record.processed_by = None
            update_fields.append('processed_by')
        if existing_record.paid_at is not None:
            existing_record.paid_at = None
            update_fields.append('paid_at')
        if update_fields:
            existing_record.save(update_fields=update_fields)
        return existing_record

    paid_at = membership.payment_date or timezone.now()
    payment_record = upsert_payment_record(
        membership,
        membership.user,
        'membership',
        amount,
        'PHP',
        'completed',
        None,
        payment_provider='manual',
    )

    update_fields = []
    if payment_record.amount != amount:
        payment_record.amount = amount
        update_fields.append('amount')
    if payment_record.currency != 'PHP':
        payment_record.currency = 'PHP'
        update_fields.append('currency')
    if payment_record.status != 'completed':
        payment_record.status = 'completed'
        update_fields.append('status')
    if payment_record.payment_provider != 'manual':
        payment_record.payment_provider = 'manual'
        update_fields.append('payment_provider')
    amount_received = amount if membership.payment_method == 'face_to_face' else None
    if payment_record.amount_received != amount_received:
        payment_record.amount_received = amount_received
        update_fields.append('amount_received')
    if payment_record.change_given != Decimal('0.00'):
        payment_record.change_given = Decimal('0.00')
        update_fields.append('change_given')
    if payment_record.processed_by_id != getattr(processed_by, 'pk', None):
        payment_record.processed_by = processed_by
        update_fields.append('processed_by')
    if payment_record.paid_at != paid_at:
        payment_record.paid_at = paid_at
        update_fields.append('paid_at')
    if payment_record.stripe_session_id is not None:
        payment_record.stripe_session_id = None
        update_fields.append('stripe_session_id')
    if payment_record.stripe_payment_intent_id is not None:
        payment_record.stripe_payment_intent_id = None
        update_fields.append('stripe_payment_intent_id')
    if payment_record.stripe_charge_id is not None:
        payment_record.stripe_charge_id = None
        update_fields.append('stripe_charge_id')
    if update_fields:
        payment_record.save(update_fields=update_fields)

    return payment_record
