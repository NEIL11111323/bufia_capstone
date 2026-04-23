"""
Enable online payment for all machines
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Machine

# Get all machines
machines = Machine.objects.all()

print(f"{'='*60}")
print(f"ENABLING ONLINE PAYMENT FOR ALL MACHINES")
print(f"{'='*60}\n")

if not machines.exists():
    print("⚠️  No machines found in database!")
    print("Please create machines first through the admin panel.")
else:
    updated_count = 0
    for machine in machines:
        needs_update = False
        
        # Only update cash payment machines
        if machine.rental_price_type == 'cash':
            if not machine.allow_online_payment:
                machine.allow_online_payment = True
                needs_update = True
            
            if not machine.allow_face_to_face_payment:
                machine.allow_face_to_face_payment = True
                needs_update = True
            
            if needs_update:
                machine.save()
                updated_count += 1
                print(f"✓ Updated: {machine.name}")
                print(f"  - Online Payment: {machine.allow_online_payment}")
                print(f"  - OTC Payment: {machine.allow_face_to_face_payment}\n")
            else:
                print(f"✓ Already enabled: {machine.name}\n")
        else:
            print(f"⊘ Skipped (in-kind): {machine.name}\n")
    
    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total machines: {machines.count()}")
    print(f"Updated: {updated_count}")
    print(f"{'='*60}")
