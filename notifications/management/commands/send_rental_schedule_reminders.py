from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from notifications.notification_helpers import send_rental_schedule_reminders


class Command(BaseCommand):
    help = 'Send reminder notifications to users and admins for machine rentals, rice mill bookings, and dryer rentals one day before and on the booking date.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            dest='target_date',
            help='Run reminders as if today were YYYY-MM-DD. Useful for testing.',
        )

    def handle(self, *args, **options):
        target_date = options.get('target_date')
        current_date = None

        if target_date:
            try:
                current_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('Invalid --date format. Use YYYY-MM-DD.') from exc

        result = send_rental_schedule_reminders(current_date=current_date)

        self.stdout.write(
            self.style.SUCCESS(
                'Rental schedule reminders processed '
                f'(date={result["current_date"]}, rentals={result["rentals_checked"]}, '
                f'user_notifications={result["user_notifications_created"]}, '
                f'admin_notifications={result["admin_notifications_created"]}).'
            )
        )
