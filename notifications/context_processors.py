"""
Context processors for notifications
"""
from django.contrib.auth import get_user_model
from .models import UserNotification

User = get_user_model()


def notifications_context(request):
    """Add notification counts and recent notifications to template context"""
    context = {
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'recent_notification_groups': [],
    }
    
    if request.user.is_authenticated:
        # Get unread count for all users
        context['unread_notifications_count'] = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Get recent notifications (last 5) for dropdown
        recent_notifications = list(UserNotification.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:10])
        context['recent_notifications'] = recent_notifications

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

        context['recent_notification_groups'] = grouped
    
    return context
