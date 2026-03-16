"""
Update existing notifications with categories, priorities, and titles
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from notifications.models import UserNotification
from notifications.notification_helpers import generate_notification_title

def update_existing_notifications():
    """Update all existing notifications with new fields"""
    
    print("=" * 80)
    print("UPDATING EXISTING NOTIFICATIONS")
    print("=" * 80)
    
    notifications = UserNotification.objects.all()
    total = notifications.count()
    updated = 0
    
    print(f"\nFound {total} notifications to update...")
    
    for notif in notifications:
        # Auto-detect category
        if 'rental' in notif.notification_type.lower():
            notif.category = 'rental'
        elif 'operator' in notif.notification_type.lower():
            notif.category = 'operator'
        elif 'payment' in notif.notification_type.lower() or 'settlement' in notif.notification_type.lower():
            notif.category = 'payment'
        elif 'maintenance' in notif.notification_type.lower() or 'machine' in notif.notification_type.lower():
            notif.category = 'maintenance'
        elif 'irrigation' in notif.notification_type.lower():
            notif.category = 'irrigation'
        elif 'appointment' in notif.notification_type.lower() or 'rice' in notif.notification_type.lower():
            notif.category = 'appointment'
        elif 'membership' in notif.notification_type.lower():
            notif.category = 'membership'
        else:
            notif.category = 'system'
        
        # Auto-detect priority
        if 'urgent' in notif.notification_type.lower() or 'critical' in notif.notification_type.lower():
            notif.priority = 'critical'
        elif 'new_request' in notif.notification_type.lower() or 'approved' in notif.notification_type.lower():
            notif.priority = 'important'
        elif 'update' in notif.notification_type.lower() or 'completed' in notif.notification_type.lower():
            notif.priority = 'normal'
        else:
            notif.priority = 'low'
        
        # Generate title if empty
        if not notif.title:
            notif.title = generate_notification_title(notif.notification_type, notif.message)
        
        notif.save()
        updated += 1
        
        if updated % 100 == 0:
            print(f"  Updated {updated}/{total} notifications...")
    
    print(f"\n✓ Successfully updated {updated} notifications!")
    
    # Show statistics
    print("\n" + "=" * 80)
    print("UPDATED STATISTICS")
    print("=" * 80)
    
    print("\nBy Category:")
    for category, label in UserNotification.CATEGORY_CHOICES:
        count = UserNotification.objects.filter(category=category).count()
        if count > 0:
            print(f"  - {label}: {count}")
    
    print("\nBy Priority:")
    for priority, label in UserNotification.PRIORITY_CHOICES:
        count = UserNotification.objects.filter(priority=priority).count()
        if count > 0:
            print(f"  - {label}: {count}")
    
    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    update_existing_notifications()
