"""
Management command to update rental and machine statuses automatically
Run this command via cron job or Celery Beat every hour

Usage:
    python manage.py update_rental_status
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from machines.models import Rental, Machine
from django.db.models import Q


class Command(BaseCommand):
    help = 'Update rental and machine statuses based on current dates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # 1. Mark rentals as completed if end date has passed
        expired_rentals = Rental.objects.filter(
            status='approved',
            end_date__lt=today
        )
        
        expired_count = expired_rentals.count()
        if expired_count > 0:
            self.stdout.write(f'Found {expired_count} rentals to mark as completed:')
            for rental in expired_rentals:
                self.stdout.write(f'  - {rental.machine.name}: {rental.start_date} to {rental.end_date}')
            
            if not dry_run:
                expired_rentals.update(status='completed')
                self.stdout.write(self.style.SUCCESS(f'✓ Marked {expired_count} rentals as completed'))
        else:
            self.stdout.write('No expired rentals found')
        
        # 2. Update machine status for rentals starting today
        starting_rentals = Rental.objects.filter(
            status='approved',
            start_date=today
        ).select_related('machine')
        
        starting_count = starting_rentals.count()
        if starting_count > 0:
            self.stdout.write(f'\nFound {starting_count} rentals starting today:')
            for rental in starting_rentals:
                self.stdout.write(f'  - {rental.machine.name}')
                if not dry_run:
                    rental.machine.status = 'rented'
                    rental.machine.save(update_fields=['status'])
            
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'✓ Updated {starting_count} machines to "rented" status'))
        else:
            self.stdout.write('\nNo rentals starting today')
        
        # 3. Update machine status for completed rentals (set back to available)
        machines_to_check = set()
        for rental in expired_rentals:
            machines_to_check.add(rental.machine_id)
        
        if machines_to_check:
            self.stdout.write(f'\nChecking {len(machines_to_check)} machines for status updates:')
            
            for machine_id in machines_to_check:
                try:
                    machine = Machine.objects.get(pk=machine_id)
                    
                    # Check if there are other active rentals
                    active_rentals = Rental.objects.filter(
                        machine=machine,
                        status='approved',
                        start_date__lte=today,
                        end_date__gte=today
                    ).exists()
                    
                    # Check if under maintenance
                    from machines.models import Maintenance
                    active_maintenance = Maintenance.objects.filter(
                        machine=machine,
                        status__in=['scheduled', 'in_progress'],
                        start_date__date__lte=today,
                        end_date__date__gte=today
                    ).exists()
                    
                    new_status = None
                    if active_rentals:
                        new_status = 'rented'
                    elif active_maintenance:
                        new_status = 'maintenance'
                    else:
                        new_status = 'available'
                    
                    if machine.status != new_status:
                        self.stdout.write(f'  - {machine.name}: {machine.status} → {new_status}')
                        if not dry_run:
                            machine.status = new_status
                            machine.save(update_fields=['status'])
                    
                except Machine.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  - Machine {machine_id} not found'))
            
            if not dry_run:
                self.stdout.write(self.style.SUCCESS('✓ Machine statuses updated'))
        
        # 4. Clean up expired locks (if RentalLock model exists)
        try:
            from machines.models import RentalLock
            expired_locks = RentalLock.objects.filter(
                expires_at__lt=timezone.now()
            )
            lock_count = expired_locks.count()
            
            if lock_count > 0:
                self.stdout.write(f'\nFound {lock_count} expired locks to clean up')
                if not dry_run:
                    expired_locks.delete()
                    self.stdout.write(self.style.SUCCESS(f'✓ Cleaned up {lock_count} expired locks'))
            else:
                self.stdout.write('\nNo expired locks found')
        except ImportError:
            self.stdout.write(self.style.WARNING('\nRentalLock model not found - skipping lock cleanup'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No changes were made'))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS('✓ Status update completed successfully'))
