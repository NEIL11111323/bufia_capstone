"""
Create test machine with online payment enabled
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Machine

# Create or update test machine
machine_name = 'Test Tractor'
from decimal import Decimal

machine, created = Machine.objects.get_or_create(
    name=machine_name,
    defaults={
        'description': 'Test tractor for equipment rental',
        'machine_type': 'tractor_4wd',
        'status': 'available',
        'current_price': '1200',
        'rental_fee_per_day': Decimal('1200.00'),
        'rental_price_type': 'cash',
        'allow_online_payment': True,
        'allow_face_to_face_payment': True,
        'settlement_type': 'immediate',
    }
)

if not created:
    # Update existing machine
    machine.allow_online_payment = True
    machine.allow_face_to_face_payment = True
    machine.rental_price_type = 'cash'
    machine.status = 'available'
    machine.save()
    print(f"✓ Updated machine: {machine_name}")
else:
    print(f"✓ Created machine: {machine_name}")

print(f"\n{'='*50}")
print(f"MACHINE DETAILS")
print(f"{'='*50}")
print(f"ID: {machine.id}")
print(f"Name: {machine.name}")
print(f"Type: {machine.get_machine_type_display()}")
print(f"Price: ₱{machine.current_price}")
print(f"Payment Type: {machine.rental_price_type}")
print(f"Allow Online Payment (GCash): {machine.allow_online_payment}")
print(f"Allow OTC Payment: {machine.allow_face_to_face_payment}")
print(f"Status: {machine.get_status_display()}")
print(f"{'='*50}")

# List all machines
all_machines = Machine.objects.all()
print(f"\nAll machines in database: {all_machines.count()}")
for m in all_machines:
    print(f"  - {m.id}. {m.name} (Online: {m.allow_online_payment}, OTC: {m.allow_face_to_face_payment})")
