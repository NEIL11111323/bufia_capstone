from django.core.management.base import BaseCommand
from machines.models import RiceMillAppointment
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Update reference numbers for rice mill appointments that do not have one'

    def handle(self, *args, **options):
        # Get all appointments without a reference number
        appointments = RiceMillAppointment.objects.filter(reference_number__isnull=True)
        count = appointments.count()
        
        self.stdout.write(f"Found {count} appointments without reference numbers")
        
        # Update each appointment
        for appointment in appointments:
            # Generate a unique reference number
            date_str = appointment.created_at.strftime('%Y%m%d')
            random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            reference_number = f"RM-{date_str}-{random_num}"
            
            # Check if this reference number already exists
            while RiceMillAppointment.objects.filter(reference_number=reference_number).exists():
                # If it does, generate a new one
                random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                reference_number = f"RM-{date_str}-{random_num}"
            
            # Update the appointment
            appointment.reference_number = reference_number
            appointment.save(update_fields=['reference_number'])
            
            self.stdout.write(f"Updated appointment {appointment.id} with reference number {reference_number}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {count} appointments")) 