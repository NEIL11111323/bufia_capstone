"""
Management command to delete all rental-related notifications
"""
from django.core.management.base import BaseCommand
from notifications.models import UserNotification


class Command(BaseCommand):
    help = 'Delete all rental-related notifications from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of rental notifications',
        )

    def handle(self, *args, **options):
        # Define rental-related notification types
        rental_notification_types = [
            'rental_submitted',
            'rental_approved',
            'rental_rejected',
            'rental_cancelled',
            'rental_completed',
            'rental_new_request',
            'rental_conflict',
            'rental_conflict_broadcast',
            'rental_reminder',
            'rental_payment_pending',
            'rental_payment_verified',
        ]

        if not options['confirm']:
            # Count notifications
            total_count = UserNotification.objects.filter(
                notification_type__in=rental_notification_types
            ).count()
            
            self.stdout.write(
                self.style.WARNING(
                    f'\nThis will delete {total_count} rental-related notification(s)!\n'
                    'To confirm, run: python manage.py delete_rental_notifications --confirm'
                )
            )
            return

        # Count notifications before deletion
        notification_count = UserNotification.objects.filter(
            notification_type__in=rental_notification_types
        ).count()
        
        if notification_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No rental-related notifications found in the database.')
            )
            return

        # Show breakdown by type
        self.stdout.write(
            self.style.WARNING(f'\nFound {notification_count} rental notification(s):')
        )
        for notif_type in rental_notification_types:
            count = UserNotification.objects.filter(notification_type=notif_type).count()
            if count > 0:
                self.stdout.write(f'  - {notif_type}: {count}')

        # Delete rental-related notifications
        self.stdout.write(self.style.WARNING('\nDeleting rental notifications...'))
        UserNotification.objects.filter(
            notification_type__in=rental_notification_types
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully deleted {notification_count} rental notification(s)!'
            )
        )
