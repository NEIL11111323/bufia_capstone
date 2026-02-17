"""
Quick script to check notifications in the database
Run with: python manage.py shell < check_notifications.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from notifications.models import UserNotification
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*60)
print("NOTIFICATION CHECK")
print("="*60)

# Check total notifications
total_notifications = UserNotification.objects.count()
print(f"\nTotal notifications in database: {total_notifications}")

# Check notifications per user
users = User.objects.all()
print(f"\nTotal users: {users.count()}")

for user in users[:10]:  # Show first 10 users
    user_notifications = UserNotification.objects.filter(user=user).count()
    unread = UserNotification.objects.filter(user=user, is_read=False).count()
    print(f"  - {user.username}: {user_notifications} total, {unread} unread")

# Show recent notifications
print("\nRecent 5 notifications:")
recent = UserNotification.objects.all().order_by('-timestamp')[:5]
for notif in recent:
    print(f"  - [{notif.notification_type}] {notif.user.username}: {notif.message[:50]}...")

print("\n" + "="*60)
