#!/usr/bin/env python3
"""
Test operator job start functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Rental
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("OPERATOR JOB START TEST")
print("=" * 60)

# Find rental #55
try:
    rental = Rental.objects.get(id=55)
    print(f"✅ Found Rental #{rental.id}")
    print(f"   Machine: {rental.machine.name}")
    print(f"   Status: {rental.status}")
    print(f"   Payment Status: {rental.payment_status}")
    print(f"   Payment Verified: {rental.payment_verified}")
    print(f"   Operator: {rental.assigned_operator}")
    
    # Check if it can be started
    can_start = (
        rental.status in ['approved', 'assigned'] and 
        rental.payment_status == 'paid' and
        rental.assigned_operator is not None
    )
    
    print(f"   Can Start: {can_start}")
    
    if can_start:
        print("\n✅ This job is ready to start!")
        print(f"   Operator URL: /machines/operator/jobs/{rental.id}/")
        print(f"   Start URL: POST /machines/operator/start/{rental.id}/")
    else:
        print("\n❌ Job cannot be started:")
        if rental.status not in ['approved', 'assigned']:
            print(f"   - Status must be 'approved' or 'assigned', got '{rental.status}'")
        if rental.payment_status != 'paid':
            print(f"   - Payment status must be 'paid', got '{rental.payment_status}'")
        if not rental.assigned_operator:
            print("   - No operator assigned")
    
    # Check if operator has ongoing jobs
    if rental.assigned_operator:
        ongoing_jobs = Rental.objects.filter(
            assigned_operator=rental.assigned_operator,
            status='ongoing'
        ).count()
        print(f"   Operator ongoing jobs: {ongoing_jobs}")
        
        if ongoing_jobs > 0:
            print("   ⚠️  Operator has ongoing jobs - cannot start new job")
    
except Rental.DoesNotExist:
    print("❌ Rental #55 not found")

print("\n" + "=" * 60)
print("TESTING OTHER READY JOBS")
print("=" * 60)

# Find all jobs ready to start
ready_jobs = Rental.objects.filter(
    status__in=['approved', 'assigned'],
    payment_status='paid',
    assigned_operator__isnull=False
).select_related('machine', 'assigned_operator')

print(f"✅ Found {ready_jobs.count()} job(s) ready to start:")

for job in ready_jobs:
    # Check if operator has ongoing jobs
    ongoing_count = Rental.objects.filter(
        assigned_operator=job.assigned_operator,
        status='ongoing'
    ).count()
    
    can_start = ongoing_count == 0
    
    print(f"   • Rental #{job.id} - {job.machine.name}")
    print(f"     Operator: {job.assigned_operator.get_full_name()}")
    print(f"     Can Start: {'✅ YES' if can_start else '❌ NO (has ongoing job)'}")
    print(f"     URL: /machines/operator/jobs/{job.id}/")

print("\n" + "=" * 60)