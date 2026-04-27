"""
Export machines from local database to JSON for import on Render
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Machine

machines = Machine.objects.all()

if not machines.exists():
    print("⚠️  No machines found in local database!")
else:
    machines_data = []
    
    for machine in machines:
        machine_dict = {
            'name': machine.name,
            'machine_type': machine.machine_type,
            'description': machine.description,
            'brand_name': machine.brand_name,
            'model_name': machine.model_name,
            'model_year': machine.model_year,
            'horsepower': str(machine.horsepower) if machine.horsepower else None,
            'acquisition_date': str(machine.acquisition_date) if machine.acquisition_date else None,
            'acquisition_amount': str(machine.acquisition_amount) if machine.acquisition_amount else None,
            'status': machine.status,
            'rental_fee_per_day': str(machine.rental_fee_per_day),
            'current_price': machine.current_price,
            'dryer_service_type': machine.dryer_service_type,
            'dryer_pricing_type': machine.dryer_pricing_type,
            'dryer_hourly_rate': str(machine.dryer_hourly_rate) if machine.dryer_hourly_rate else None,
            'rental_price_type': machine.rental_price_type,
            'allow_online_payment': machine.allow_online_payment,
            'allow_face_to_face_payment': machine.allow_face_to_face_payment,
            'settlement_type': machine.settlement_type,
            'in_kind_farmer_share': machine.in_kind_farmer_share,
            'in_kind_organization_share': machine.in_kind_organization_share,
            'stripe_payment_link': machine.stripe_payment_link,
        }
        machines_data.append(machine_dict)
    
    # Save to JSON file
    with open('machines_export.json', 'w') as f:
        json.dump(machines_data, f, indent=2)
    
    print(f"✓ Exported {len(machines_data)} machine(s) to machines_export.json")
    print("\nMachines exported:")
    for m in machines_data:
        print(f"  - {m['name']} ({m['machine_type']})")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Copy the machines_export.json file content")
    print("2. Create the same file on your Render server")
    print("3. Run: python import_machines.py")
    print("="*60)
