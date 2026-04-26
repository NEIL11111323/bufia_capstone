"""
Management command to sync overdue rental workflow states.
This command identifies rentals that have passed their end date
but are not yet completed and marks them as overdue.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from machines.models import Rental


class Command(BaseCommand):
    help = 'Update workflow states for overdue rentals and handle conflicts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Use specific date (YYYY-MM-DD) instead of today',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if options['date']:
            try:
                target_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            target_date = timezone.localdate()

        self.stdout.write(f'Checking for overdue rentals as of {target_date}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Use the existing sync method
        if not dry_run:
            updated_ids = Rental.sync_overdue_workflow_states(today=target_date)
            updated_count = len(updated_ids) if updated_ids else 0
            self.stdout.write(
                self.style.SUCCESS(f'Updated {updated_count} rental(s) workflow states')
            )
        else:
            # Simulate the sync for dry run
            active_rentals = Rental.objects.filter(
                status='approved',
                end_date__lt=target_date,
                actual_return_at__isnull=True
            ).exclude(
                workflow_state__in=['completed', 'cancelled', 'overdue']
            ).select_related('machine', 'user')

            if not active_rentals.exists():
                self.stdout.write('No rentals need to be marked as overdue')
                return

            self.stdout.write(f'Found {active_rentals.count()} rental(s) that would be marked as overdue:')
            
            for rental in active_rentals:
                days_overdue = (target_date - rental.end_date).days
                self.stdout.write(
                    f'  - Rental {rental.id}: {rental.machine.name} '
                    f'(ended {rental.end_date}, {days_overdue} days overdue)'
                )

            # Check for potential conflicts
            conflict_count = 0
            for rental in active_rentals:
                future_approved = Rental.objects.filter(
                    machine=rental.machine,
                    status='approved',
                    workflow_state='approved',
                    start_date__gte=target_date
                ).exclude(id=rental.id)
                
                if future_approved.exists():
                    conflict_count += future_approved.count()
                    self.stdout.write(
                        self.style.WARNING(
                            f'  - Machine {rental.machine.name} has {future_approved.count()} '
                            f'future approved rental(s) that would be affected'
                        )
                    )

            if conflict_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Total of {conflict_count} future rental(s) would need conflict review'
                    )
                )

        self.stdout.write('Overdue sync completed')