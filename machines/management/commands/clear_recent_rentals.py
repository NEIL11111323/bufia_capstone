"""
Management command to delete recent rental records for testing purposes

Usage:
    python manage.py clear_recent_rentals
    python manage.py clear_recent_rentals --days 7
    python manage.py clear_recent_rentals --all
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from machines.models import Rental
from datetime import timedelta


class Command(BaseCommand):
    help = 'Delete recent rental records for testing purposes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete rentals created in the last N days (default: 30)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL rentals (use with caution!)',
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Only delete rentals with specific status (pending, approved, rejected, cancelled, completed)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_all = options['all']
        days = options['days']
        status_filter = options['status']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No rentals will be deleted'))
        
        # Build query
        if delete_all:
            rentals = Rental.objects.all()
            self.stdout.write(self.style.WARNING('⚠️  Deleting ALL rentals!'))
        else:
            cutoff_date = timezone.now() - timedelta(days=days)
            rentals = Rental.objects.filter(created_at__gte=cutoff_date)
            self.stdout.write(f'Deleting rentals created in the last {days} days')
        
        # Apply status filter if specified
        if status_filter:
            rentals = rentals.filter(status=status_filter)
            self.stdout.write(f'Filtering by status: {status_filter}')
        
        # Show what will be deleted
        count = rentals.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No rentals found matching criteria'))
            return
        
        self.stdout.write(f'\nFound {count} rental(s) to delete:\n')
        
        for rental in rentals:
            self.stdout.write(
                f'  - ID: {rental.id} | Machine: {rental.machine.name} | '
                f'User: {rental.user.username} | Status: {rental.status} | '
                f'Dates: {rental.start_date} to {rental.end_date} | '
                f'Created: {rental.created_at.strftime("%Y-%m-%d %H:%M")}'
            )
        
        # Confirm deletion
        if not dry_run:
            self.stdout.write('\n' + '='*70)
            confirm = input(f'Are you sure you want to delete {count} rental(s)? (yes/no): ')
            
            if confirm.lower() == 'yes':
                # Get affected machines before deletion
                affected_machines = set(rental.machine for rental in rentals)
                
                # Delete rentals
                rentals.delete()
                
                self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully deleted {count} rental(s)'))
                
                # Update machine statuses
                self.stdout.write('\nUpdating machine statuses...')
                today = timezone.now().date()
                
                for machine in affected_machines:
                    # Check if machine has any active rentals
                    active_rentals = Rental.objects.filter(
                        machine=machine,
                        status='approved',
                        start_date__lte=today,
                        end_date__gte=today
                    ).exists()
                    
                    if active_rentals:
                        machine.status = 'rented'
                    else:
                        # Check maintenance
                        from machines.models import Maintenance
                        active_maintenance = Maintenance.objects.filter(
                            machine=machine,
                            status__in=['scheduled', 'in_progress']
                        ).exists()
                        
                        if active_maintenance:
                            machine.status = 'maintenance'
                        else:
                            machine.status = 'available'
                    
                    machine.save(update_fields=['status'])
                    self.stdout.write(f'  - {machine.name}: {machine.status}')
                
                self.stdout.write(self.style.SUCCESS('\n✓ Machine statuses updated'))
            else:
                self.stdout.write(self.style.WARNING('Deletion cancelled'))
        else:
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No rentals were deleted'))
            self.stdout.write('Run without --dry-run to actually delete these rentals')
