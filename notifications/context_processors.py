"""
Context processors for notifications
"""
import logging

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from .models import UserNotification

User = get_user_model()
logger = logging.getLogger(__name__)


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
