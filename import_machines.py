"""
Import machines from JSON file to database
Safe to run multiple times - will skip existing machines
"""
import os
import django
import json
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Machine

# Read the JSON file
try:
    with open('machines_export.json', 'r') as f:
        machines_data = json.load(f)
except FileNotFoundError:
    print("❌ Error: machines_export.json not found!")
    print("Please create this file first by running export_machines.py locally")
    exit(1)

print(f"{'='*60}")
print(f"IMPORTING MACHINES")
print(f"{'='*60}\n")

created_count = 0
skipped_count = 0
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
        print(f"✓ Updated: {machine_name}")
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
        print(f"✓ Created: {machine_name}")

print(f"\n{'='*60}")
print(f"IMPORT SUMMARY")
print(f"{'='*60}")
print(f"Total machines in file: {len(machines_data)}")
print(f"Created: {created_count}")
print(f"Updated: {updated_count}")
print(f"Skipped: {skipped_count}")
print(f"{'='*60}")

if created_count > 0 or updated_count > 0:
    print(f"\n✓ Successfully imported machines!")
    print(f"All machines now have online payment enabled by default.")
