"""
Utility functions for machine rental availability checking and management
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Rental, Machine, Maintenance


class AvailabilityChecker:
    """Utility class for checking machine availability with race condition protection"""
    
    @staticmethod
    def get_available_dates(machine, start_date=None, end_date=None):
        """
        Get list of blocked periods for a machine
        
        Args:
            machine: Machine instance
            start_date: Start date for checking (default: today)
            end_date: End date for checking (default: 90 days from start)
            
        Returns:
            List of dictionaries with blocked period information
        """
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=90)
        
        blocked_periods = []
        
        # Add rental periods (both approved and pending)
        rentals = Rental.objects.filter(
            machine=machine,
            status__in=['approved', 'pending'],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).order_by('start_date')
        
        for rental in rentals:
            blocked_periods.append({
                'start': rental.start_date,
                'end': rental.end_date,
                'type': 'rental',
                'status': rental.status,
                'user': rental.user.get_full_name() if rental.user else 'Unknown'
            })
        
        # Add maintenance periods
        maintenances = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        ).order_by('start_date')
        
        for maintenance in maintenances:
            end = maintenance.end_date.date() if maintenance.end_date else maintenance.start_date.date()
            blocked_periods.append({
                'start': maintenance.start_date.date(),
                'end': end,
                'type': 'maintenance',
                'status': maintenance.status,
                'description': maintenance.description
            })
        
        return blocked_periods
    
    @staticmethod
    @transaction.atomic
    def check_availability(machine, start_date, end_date, user=None, exclude_rental_id=None):
        """
        Check if machine is available for the given date range with database locking
        
        Args:
            machine: Machine instance
            start_date: Rental start date
            end_date: Rental end date
            user: User making the request (optional)
            exclude_rental_id: Rental ID to exclude from check (for updates)
            
        Returns:
            Tuple of (is_available: bool, message: str)
        """
        # Validate dates
        today = timezone.now().date()
        
        if start_date < today:
            return False, "Start date cannot be in the past"
        
        if end_date < start_date:
            return False, "End date must be after start date"
        
        # Maximum rental period check (30 days)
        if (end_date - start_date).days > 30:
            return False, "Rental period cannot exceed 30 days"
        
        # Check machine status
        if machine.status == 'maintenance':
            return False, "Machine is currently under maintenance"
        
        # Use select_for_update to lock the rows we're checking (prevents race conditions)
        overlapping_rentals = Rental.objects.select_for_update().filter(
            machine=machine,
            status__in=['approved', 'pending'],  # Check both approved AND pending
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if exclude_rental_id:
            overlapping_rentals = overlapping_rentals.exclude(id=exclude_rental_id)
        
        if overlapping_rentals.exists():
            conflict = overlapping_rentals.first()
            return False, (
                f"Machine is already booked from {conflict.start_date} to {conflict.end_date}. "
                f"Status: {conflict.get_status_display()}"
            )
        
        # Check maintenance schedule
        maintenance_conflicts = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress'],
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        )
        
        if maintenance_conflicts.exists():
            maintenance = maintenance_conflicts.first()
            end_date_str = maintenance.end_date.date() if maintenance.end_date else maintenance.start_date.date()
            return False, (
                f"Machine has scheduled maintenance from "
                f"{maintenance.start_date.date()} to {end_date_str}"
            )
        
        return True, "Machine is available for the selected dates"
    
    @staticmethod
    def get_next_available_date(machine, preferred_start_date=None):
        """
        Find the next available date for a machine
        
        Args:
            machine: Machine instance
            preferred_start_date: Preferred start date (default: today)
            
        Returns:
            Next available date or None if not available in next 90 days
        """
        if not preferred_start_date:
            preferred_start_date = timezone.now().date()
        
        # Get all blocked periods for next 90 days
        blocked_periods = AvailabilityChecker.get_available_dates(
            machine,
            start_date=preferred_start_date,
            end_date=preferred_start_date + timedelta(days=90)
        )
        
        # Sort by start date
        blocked_periods.sort(key=lambda x: x['start'])
        
        # Find first gap
        current_date = preferred_start_date
        for period in blocked_periods:
            if current_date < period['start']:
                return current_date
            current_date = max(current_date, period['end'] + timedelta(days=1))
        
        # If we've checked all blocked periods and current_date is still reasonable
        if (current_date - preferred_start_date).days <= 90:
            return current_date
        
        return None
