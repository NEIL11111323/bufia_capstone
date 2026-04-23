"""
Django management command to import machines from JSON file
"""
import json
from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from machines.models import Machine


class Command(BaseCommand):
    help = 'Import machines from machines_export.json file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='machines_export.json',
            help='Path to the JSON file containing machine data'
        )

    def handle(self, *args, **options):
        json_file = options['file']
        
        try:
            with open(json_file, 'r') as f:
                machines_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Error: {json_file} not found!'))
            self.stdout.write('Please create this file first by running export_machines.py locally')
            return

        self.stdout.write('='*60)
        self.stdout.write('IMPORTING MACHINES')
        self.stdout.write('='*60)
        self.stdout.write('')

        created_count = 0
        updated_count = 0

        for machine_dict in machines_data:
            machine_name = machine_dict['name']
            
            # Check if machine already exists
            existing = Machine.objects.filter(name=machine_name).first()
            
            if existing:
                # Update existing machine
                for key, value in machine_dict.items():
                    if key in ['acquisition_date'] and value:
                        value = date.fromisoformat(value)
                    elif key in ['acquisition_amount', 'rental_fee_per_day', 'dryer_hourly_rate'] and value:
                        value = Decimal(value)
                    
                    setattr(existing, key, value)
                
                existing.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Updated: {machine_name}'))
            else:
                # Create new machine
                machine_dict_copy = machine_dict.copy()
                
                # Convert string values to proper types
                if machine_dict_copy.get('acquisition_date'):
                    machine_dict_copy['acquisition_date'] = date.fromisoformat(machine_dict_copy['acquisition_date'])
                if machine_dict_copy.get('acquisition_amount'):
                    machine_dict_copy['acquisition_amount'] = Decimal(machine_dict_copy['acquisition_amount'])
                if machine_dict_copy.get('rental_fee_per_day'):
                    machine_dict_copy['rental_fee_per_day'] = Decimal(machine_dict_copy['rental_fee_per_day'])
                if machine_dict_copy.get('dryer_hourly_rate'):
                    machine_dict_copy['dryer_hourly_rate'] = Decimal(machine_dict_copy['dryer_hourly_rate'])
                
                Machine.objects.create(**machine_dict_copy)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {machine_name}'))

        self.stdout.write('')
        self.stdout.write('='*60)
        self.stdout.write('IMPORT SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'Total machines in file: {len(machines_data)}')
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write('='*60)

        if created_count > 0 or updated_count > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Successfully imported machines!'))
            self.stdout.write('All machines now have online payment enabled by default.')
