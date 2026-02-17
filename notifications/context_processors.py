from .models import UserNotification


def notifications_context(request):
    """Add unread notifications count and recent notifications to all templates."""
    unread_notifications_count = 0
    recent_notifications = []
    
    if request.user.is_authenticated:
        try:
            # Get all notifications for the user
            all_notifications = UserNotification.objects.filter(
                user=request.user
            ).order_by('-timestamp')
            
            # Filter out orphaned notifications (those referencing deleted objects)
            valid_notifications = []
            for notification in all_notifications:
                is_valid = True
                
                # Only check if there's a related_object_id
                if notification.related_object_id:
                    # Check rental-related notifications
                    if 'rental' in notification.notification_type:
                        from machines.models import Rental
                        if not Rental.objects.filter(id=notification.related_object_id).exists():
                            is_valid = False
                    
                    # Check irrigation-related notifications
                    elif 'irrigation' in notification.notification_type:
                        from irrigation.models import WaterIrrigationRequest
                        if not WaterIrrigationRequest.objects.filter(id=notification.related_object_id).exists():
                            is_valid = False
                    
                    # Check rice mill appointment notifications
                    elif 'appointment' in notification.notification_type or 'rice' in notification.notification_type:
                        from machines.models import RiceMillAppointment
                        if not RiceMillAppointment.objects.filter(id=notification.related_object_id).exists():
                            is_valid = False
                    
                    # Check maintenance-related notifications
                    elif 'maintenance' in notification.notification_type or 'machine' in notification.notification_type:
                        from machines.models import MaintenanceRecord
                        if not MaintenanceRecord.objects.filter(id=notification.related_object_id).exists():
                            is_valid = False
                    
                    # Check membership-related notifications
                    elif 'membership' in notification.notification_type:
                        from users.models import MembershipApplication
                        if not MembershipApplication.objects.filter(id=notification.related_object_id).exists():
                            is_valid = False
                
                if is_valid:
                    valid_notifications.append(notification)
                    
                # Stop once we have 5 valid notifications
                if len(valid_notifications) >= 5:
                    break
            
            recent_notifications = valid_notifications[:5]
            
            # Count unread notifications (only valid ones)
            unread_notifications_count = sum(1 for n in valid_notifications if not n.is_read)
            
        except Exception as e:
            unread_notifications_count = 0
            recent_notifications = []
            
    return {
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }










