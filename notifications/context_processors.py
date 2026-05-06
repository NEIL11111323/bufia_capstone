"""
Context processors for notifications
"""
import logging

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.db.models import F, Q
from .models import UserNotification

User = get_user_model()
logger = logging.getLogger(__name__)


def _package_notification_count(user):
    if not user or not user.is_authenticated:
        return 0

    unread_package_notification_ids = set(
        UserNotification.objects.filter(
            user=user,
            is_read=False,
            notification_type__startswith='rental_package_',
            related_object_id__isnull=False,
        ).values_list('related_object_id', flat=True)
    )

    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return len(unread_package_notification_ids)

    from machines.models import RentalPackage

    updated_package_ids = set(
        RentalPackage.objects.filter(user=user).filter(
            Q(member_last_viewed_at__isnull=True) |
            Q(updated_at__gt=F('member_last_viewed_at'))
        ).values_list('id', flat=True)
    )
    return len(updated_package_ids | unread_package_notification_ids)


def _group_recent_notifications(recent_notifications):
    grouped = []
    grouped_map = {}

    for notification in recent_notifications:
        group_key = (
            notification.notification_type,
            notification.status_label,
            notification.timestamp.date(),
        )
        if group_key in grouped_map:
            grouped_map[group_key]['count'] += 1
            grouped_map[group_key]['notifications'].append(notification)
            continue

        item = {
            'primary': notification,
            'count': 1,
            'notifications': [notification],
            'is_grouped': False,
        }
        grouped_map[group_key] = item
        grouped.append(item)

    for item in grouped:
        item['is_grouped'] = item['count'] > 1

    return grouped


def notifications_context(request):
    """Add notification counts and recent notifications to template context"""
    context = {
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'recent_notification_groups': [],
        'package_notification_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            context['unread_notifications_count'] = UserNotification.objects.filter(
                user=request.user,
                is_read=False
            ).count()

            recent_notifications = list(UserNotification.objects.filter(
                user=request.user
            ).order_by('-timestamp')[:10])
            context['package_notification_count'] = _package_notification_count(request.user)
        except DatabaseError as exc:
            logger.warning(
                "Skipping notification context for user %s because notification queries failed: %s",
                getattr(request.user, 'pk', None),
                exc,
            )
            return context

        context['recent_notifications'] = recent_notifications
        context['recent_notification_groups'] = _group_recent_notifications(recent_notifications)
    
    return context
