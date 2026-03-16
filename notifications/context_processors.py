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
    }
    
    if request.user.is_authenticated:
        # Get unread count for all users
        context['unread_notifications_count'] = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Get recent notifications (last 5) for dropdown
        context['recent_notifications'] = UserNotification.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:5]
    
    return context