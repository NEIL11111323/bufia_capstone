"""
Management command to create test notifications
Usage: python manage.py create_test_notifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import UserNotification

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test notifications for all users'

    def handle(self, *args, **options):
        users = User.objects.all()
        
        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found in the database'))
            return
        
        created_count = 0
        
        for user in users:
            # Create a welcome notification
            UserNotification.objects.create(
                user=user,
                notification_type='general',
                message=f'Welcome to BUFIA, {user.get_full_name() or user.username}! Your account is ready to use.',
                is_read=False
            )
            created_count += 1
            
            # Create a system notification
            UserNotification.objects.create(
                user=user,
                notification_type='general',
                message='System maintenance scheduled for this weekend. Please save your work.',
                is_read=False
            )
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} test notifications for {users.count()} users'
            )
        )
