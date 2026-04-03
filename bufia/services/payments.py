from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from bufia.models import Payment
from machines.models import Rental
from notifications.models import UserNotification


def upsert_payment_record(content_object, user, payment_type, amount, currency, status, session_id, payment_intent_id=None):
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
            'stripe_session_id': session_id,
            'stripe_payment_intent_id': payment_intent_id,
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
    if payment_obj.stripe_session_id != session_id:
        payment_obj.stripe_session_id = session_id
        update_fields.append('stripe_session_id')
    if payment_obj.stripe_payment_intent_id != payment_intent_id:
        payment_obj.stripe_payment_intent_id = payment_intent_id
        update_fields.append('stripe_payment_intent_id')
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


def record_rental_online_payment(rental, user, session_id, payment_intent_id=None, paid_amount=None):
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
    return upsert_payment_record(
        rental,
        user,
        'rental',
        amount,
        'PHP',
        'pending',
        session_id,
        payment_intent_id=payment_intent_id,
    )


def record_membership_online_payment(membership, user, session_id, payment_intent_id=None, paid_amount=None):
    """Persist a successful online membership payment."""
    amount = paid_amount if paid_amount and paid_amount > 0 else Decimal('500.00')

    membership.payment_status = 'paid'
    membership.payment_method = 'online'
    membership.payment_date = timezone.now()
    membership.save(update_fields=['payment_status', 'payment_method', 'payment_date'])

    return upsert_payment_record(
        membership,
        user,
        'membership',
        amount,
        'PHP',
        'completed',
        session_id,
        payment_intent_id=payment_intent_id,
    )
