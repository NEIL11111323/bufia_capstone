#!/usr/bin/env python3
"""
COMPLETE WORKFLOW SIMULATION TEST
Simulates the entire admin-operator workflow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Rental
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_section(title):
    print(f"\n📍 {title}")
    print("-" * 60)

def simulate_operator_start_job(rental_id):
    """Simulate operator starting a job"""
    try:
        rental = Rental.objects.get(id=rental_id)
        
        print(f"🔄 Simulating operator starting Rental #{rental.id}...")
        
        # Check preconditions
        if rental.status not in ['approved', 'assigned']:
            print(f"❌ Cannot start: status is '{rental.status}', need 'approved' or 'assigned'")
            return False
            
        if rental.payment_status != 'paid':
            print(f"❌ Cannot start: payment_status is '{rental.payment_status}', need 'paid'")
            return False
            
        if not rental.assigned_operator:
            print("❌ Cannot start: no operator assigned")
            return False
            
        # Check for ongoing jobs
        ongoing_jobs = Rental.objects.filter(
            assigned_operator=rental.assigned_operator,
            status='ongoing'
        ).count()
        
        if ongoing_jobs > 0:
            print(f"❌ Cannot start: operator has {ongoing_jobs} ongoing job(s)")
            return False
        
        # Start the job (simulate the operator_start_job view)
        rental.status = 'ongoing'
        rental.operator_status = 'traveling'
        rental.actual_handover_date = timezone.now()
        rental.save()
        
        # Update machine status
        rental.machine.status = 'rented'
        rental.machine.save()
        
        print(f"✅ Job started successfully!")
        print(f"   Status: {rental.status}")
        print(f"   Operator Status: {rental.operator_status}")
        print(f"   Started At: {rental.actual_handover_date}")
        print(f"   Machine Status: {rental.machine.status}")
        
        return True
        
    except Rental.DoesNotExist:
        print(f"❌ Rental #{rental_id} not found")
        return False
    except Exception as e:
        print(f"❌ Error starting job: {e}")
        return False

def simulate_operator_complete_job(rental_id):
    """Simulate operator completing a job"""
    try:
        rental = Rental.objects.get(id=rental_id)
        
        print(f"🔄 Simulating operator completing Rental #{rental.id}...")
        
        # Check preconditions
        if rental.status != 'ongoing':
            print(f"❌ Cannot complete: status is '{rental.status}', need 'ongoing'")
            return False
        
        # For in-kind jobs, check harvest report
        if rental.payment_type == 'in_kind' and not rental.total_harvest_sacks:
            print("❌ Cannot complete in-kind job without harvest report")
            return False
        
        # Complete the job (simulate the operator_complete_job view)
        rental.status = 'completed'
        rental.operator_status = 'completed'
        rental.actual_completion_time = timezone.now()
        rental.save()
        
        # Update machine status
        rental.machine.status = 'available'
        rental.machine.save()
        
        print(f"✅ Job completed successfully!")
        print(f"   Status: {rental.status}")
        print(f"   Operator Status: {rental.operator_status}")
        print(f"   Completed At: {rental.actual_completion_time}")
        print(f"   Machine Status: {rental.machine.status}")
        
        return True
        
    except Rental.DoesNotExist:
        print(f"❌ Rental #{rental_id} not found")
        return False
    except Exception as e:
        print(f"❌ Error completing job: {e}")
        return False

def main():
    print_header("COMPLETE WORKFLOW SIMULATION")
    
    # 1. Find a job ready to start
    print_section("1. FINDING JOB READY TO START")
    
    ready_jobs = Rental.objects.filter(
        status__in=['approved', 'assigned'],
        payment_status='paid',
        assigned_operator__isnull=False
    ).select_related('machine', 'assigned_operator')
    
    if not ready_jobs.exists():
        print("❌ No jobs ready to start found")
        return
    
    # Find a job where operator has no ongoing jobs
    test_job = None
    for job in ready_jobs:
        ongoing_count = Rental.objects.filter(
            assigned_operator=job.assigned_operator,
            status='ongoing'
        ).count()
        
        if ongoing_count == 0:
            test_job = job
            break
    
    if not test_job:
        print("❌ No jobs found with available operators")
        return
    
    print(f"✅ Selected job for testing:")
    print(f"   Rental #{test_job.id} - {test_job.machine.name}")
    print(f"   Operator: {test_job.assigned_operator.get_full_name()}")
    print(f"   Payment Type: {test_job.get_payment_type_display()}")
    
    # 2. Simulate operator starting the job
    print_section("2. OPERATOR STARTS JOB")
    
    if not simulate_operator_start_job(test_job.id):
        print("❌ Failed to start job")
        return
    
    # 3. Simulate operator updating status
    print_section("3. OPERATOR UPDATES STATUS")
    
    # Refresh the rental object
    test_job.refresh_from_db()
    
    print("🔄 Simulating status updates...")
    
    # Update to operating
    test_job.operator_status = 'operating'
    test_job.operator_notes = 'Work in progress'
    test_job.operator_last_update_at = timezone.now()
    test_job.save()
    
    print(f"✅ Status updated to: {test_job.get_operator_status_display()}")
    
    # 4. Handle harvest reporting for in-kind jobs
    if test_job.payment_type == 'in_kind':
        print_section("4. HARVEST REPORTING (IN-KIND JOB)")
        
        print("🔄 Simulating harvest report...")
        
        # Simulate harvest reporting
        total_harvest = 100.0  # 100 sacks
        bufia_share = total_harvest * 0.20  # 20% for BUFIA
        member_share = total_harvest - bufia_share
        
        test_job.total_harvest_sacks = total_harvest
        test_job.organization_share_required = bufia_share
        test_job.member_share = member_share
        test_job.operator_status = 'harvest_reported'
        test_job.operator_reported_at = timezone.now()
        test_job.settlement_status = 'waiting_for_delivery'
        test_job.save()
        
        print(f"✅ Harvest reported:")
        print(f"   Total Harvest: {total_harvest} sacks")
        print(f"   BUFIA Share: {bufia_share} sacks")
        print(f"   Member Share: {member_share} sacks")
        print(f"   Settlement Status: {test_job.get_settlement_status_display()}")
    
    # 5. Simulate operator completing the job
    print_section("5. OPERATOR COMPLETES JOB")
    
    if not simulate_operator_complete_job(test_job.id):
        print("❌ Failed to complete job")
        return
    
    # 6. Show final status
    print_section("6. FINAL STATUS")
    
    test_job.refresh_from_db()
    
    print(f"✅ Workflow completed successfully!")
    print(f"   Rental #{test_job.id} Status: {test_job.get_status_display()}")
    print(f"   Operator Status: {test_job.get_operator_status_display()}")
    print(f"   Machine Status: {test_job.machine.status}")
    
    if test_job.payment_type == 'in_kind':
        print(f"   Settlement Status: {test_job.get_settlement_status_display()}")
        print(f"   Total Harvest: {test_job.total_harvest_sacks} sacks")
        print(f"   BUFIA Share: {test_job.organization_share_required} sacks")
    
    # Calculate duration
    if test_job.actual_handover_date and test_job.actual_completion_time:
        duration = test_job.actual_completion_time - test_job.actual_handover_date
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        print(f"   Duration: {hours}h {minutes}m")
    
    print_section("7. NEXT STEPS FOR ADMIN")
    
    if test_job.payment_type == 'in_kind':
        print("🎯 Admin should now:")
        print("   1. Go to rental approval page")
        print(f"   2. URL: /machines/admin/rental/{test_job.id}/approve/")
        print("   3. Confirm rice delivery")
        print("   4. Complete the settlement")
    else:
        print("🎯 Admin should now:")
        print("   1. Verify the completed job")
        print(f"   2. URL: /machines/admin/rental/{test_job.id}/approve/")
        print("   3. Finalize the rental")
    
    print_header("SIMULATION COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()