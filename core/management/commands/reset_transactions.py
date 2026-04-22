"""
Management command to reset all transaction data for fresh system implementation.
This removes all transactions, payments, rentals, sales, etc. while keeping
users, machines, sectors, and system configuration.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from bufia.models import Payment, Refund
from machines.models import (
    Rental, RiceMillAppointment, DryerRental, Maintenance, 
    MaintenancePartUsed, PriceHistory
)
from reports.models import RiceSale
from users.models import MembershipApplication, MembershipApplicationProof
from notifications.models import UserNotification


class Command(BaseCommand):
    help = 'Reset all transaction data for fresh system implementation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all transaction data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will DELETE ALL transaction data including:\n'
                    '- All rentals and machine bookings\n'
                    '- All payments and refunds\n'
                    '- All rice mill appointments\n'
                    '- All dryer rentals\n'
                    '- All maintenance records\n'
                    '- All rice sales\n'
                    '- All membership applications\n'
                    '- All notifications\n'
                    '- All price history\n\n'
                    'Users, machines, sectors, and settings will be KEPT.\n\n'
                    'To proceed, run: python manage.py reset_transactions --confirm'
                )
            )
            return

        self.stdout.write(self.style.WARNING('Starting transaction data reset...'))

        with transaction.atomic():
            # Delete notifications
            notification_count = UserNotification.objects.all().count()
            UserNotification.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {notification_count} notifications'))

            # Delete membership proof documents
            proof_count = MembershipApplicationProof.objects.all().count()
            MembershipApplicationProof.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {proof_count} membership proof documents'))

            # Delete membership applications
            membership_count = MembershipApplication.objects.all().count()
            MembershipApplication.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {membership_count} membership applications'))

            # Delete rice sales
            rice_sale_count = RiceSale.objects.all().count()
            RiceSale.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {rice_sale_count} rice sales'))

            # Delete maintenance parts
            parts_count = MaintenancePartUsed.objects.all().count()
            MaintenancePartUsed.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {parts_count} maintenance parts'))

            # Delete maintenance records
            maintenance_count = Maintenance.objects.all().count()
            Maintenance.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {maintenance_count} maintenance records'))

            # Delete price history
            price_history_count = PriceHistory.objects.all().count()
            PriceHistory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {price_history_count} price history records'))

            # Delete dryer rentals
            dryer_count = DryerRental.objects.all().count()
            DryerRental.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {dryer_count} dryer rentals'))

            # Delete rice mill appointments
            rice_mill_count = RiceMillAppointment.objects.all().count()
            RiceMillAppointment.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {rice_mill_count} rice mill appointments'))

            # Delete rentals
            rental_count = Rental.objects.all().count()
            Rental.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {rental_count} rentals'))

            # Delete refunds
            refund_count = Refund.objects.all().count()
            Refund.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {refund_count} refunds'))

            # Delete payments
            payment_count = Payment.objects.all().count()
            Payment.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {payment_count} payments'))

        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Transaction data reset complete!\n'
                'All transactions have been removed.\n'
                'Users, machines, sectors, and settings are preserved.\n'
                'System is ready for fresh implementation.'
            )
        )
