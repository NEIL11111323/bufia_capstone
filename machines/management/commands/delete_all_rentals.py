"""
Management command to delete all rental records from the database
"""
from django.core.management.base import BaseCommand
from machines.models import Rental


class Command(BaseCommand):
    help = 'Delete all rental records from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all rentals',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL rental records from the database!\n'
                    'To confirm, run: python manage.py delete_all_rentals --confirm'
                )
            )
            return

        # Count rentals before deletion
        rental_count = Rental.objects.count()
        
        if rental_count == 0:
            self.stdout.write(self.style.SUCCESS('No rentals found in the database.'))
            return

        # Show breakdown by status
        self.stdout.write(self.style.WARNING(f'\nFound {rental_count} rental(s):'))
        for status, label in Rental.STATUS_CHOICES:
            count = Rental.objects.filter(status=status).count()
            if count > 0:
                self.stdout.write(f'  - {label}: {count}')

        # Delete all rentals
        self.stdout.write(self.style.WARNING('\nDeleting all rentals...'))
        Rental.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully deleted {rental_count} rental record(s)!'
            )
        )
