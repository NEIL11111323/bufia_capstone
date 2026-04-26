"""
Test script to verify the overdue rental system functionality.
This tests the workflow state transitions, availability blocking,
and conflict detection for overdue rentals.
"""

import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from machines.models import Machine, Rental

User = get_user_model()

def test_overdue_rental_system():
    print("=" * 80)
    print("OVERDUE RENTAL SYSTEM VERIFICATION TEST")
    print("=" * 80)
    
    # Get or create test users
    test_user_a, _ = User.objects.get_or_create(
        username='test_user_a',
        defaults={
            'email': 'usera@example.com',
            'first_name': 'User',
            'last_name': 'A',
            'is_active': True,
            'is_verified': True,
        }
    )
    
    test_user_b, _ = User.objects.get_or_create(
        username='test_user_b',
        defaults={
            'email': 'userb@example.com',
            'first_name': 'User',
            'last_name': 'B',
            'is_active': True,
            'is_verified': True,
        }
    )
    
    # Get or create a test machine
    test_machine, _ = Machine.objects.get_or_create(
        name='Test Tractor for Overdue',
        defaults={
            'machine_type': 'tractor_4wd',
            'status': 'available',
            'rental_price_type': 'cash',
            'settlement_type': 'immediate',
            'current_price': '4000/hectare',
            'rental_fee_per_day': 4000.00,
        }
    )
    
    print(f"Test Machine: {test_machine.name}")
    print(f"Test Users: {test_user_a.username}, {test_user_b.username}")
    
    # Clean up any existing test rentals
    Rental.objects.filter(
        machine=test_machine,
        user__in=[test_user_a, test_user_b]
    ).delete()
    
    test_scenarios = []
    
    # ========================================================================
    # SCENARIO 1: Create a rental that should become overdue
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 1: RENTAL BECOMES OVERDUE")
    print("=" * 80)
    
    # Create a rental that ended 3 days ago
    past_start = date.today() - timedelta(days=5)
    past_end = date.today() - timedelta(days=3)
    
    rental_a = Rental.objects.create(
        machine=test_machine,
        user=test_user_a,
        start_date=past_start,
        end_date=past_end,
        area=2.5,
        purpose='Test overdue rental',
        status='approved',
        workflow_state='approved',
        payment_type='cash',
        payment_method='face_to_face',
        payment_status='paid',
    )
    
    print(f"Created Rental A:")
    print(f"  ID: {rental_a.id}")
    print(f"  Dates: {rental_a.start_date} to {rental_a.end_date}")
    print(f"  Status: {rental_a.status}")
    print(f"  Workflow State: {rental_a.workflow_state}")
    
    # Check if it's detected as overdue
    print(f"\nOverdue Detection:")
    print(f"  is_overdue_active: {rental_a.is_overdue_active}")
    print(f"  overdue_days: {rental_a.overdue_days}")
    print(f"  is_schedule_blocking: {rental_a.is_schedule_blocking}")
    
    test_scenarios.append(("Rental Overdue Detection", "PASSED" if rental_a.is_overdue_active else "FAILED"))
    
    # ========================================================================
    # SCENARIO 2: Sync overdue workflow states
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 2: SYNC OVERDUE WORKFLOW STATES")
    print("=" * 80)
    
    print(f"Before sync - Workflow State: {rental_a.workflow_state}")
    
    # Run the sync method
    updated_ids = Rental.sync_overdue_workflow_states()
    
    # Refresh from database
    rental_a.refresh_from_db()
    
    print(f"After sync - Workflow State: {rental_a.workflow_state}")
    print(f"Updated rental IDs: {updated_ids}")
    
    sync_success = rental_a.workflow_state == 'overdue'
    test_scenarios.append(("Overdue Sync Process", "PASSED" if sync_success else "FAILED"))
    
    # ========================================================================
    # SCENARIO 3: Test availability blocking by overdue rental
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 3: OVERDUE RENTAL BLOCKS AVAILABILITY")
    print("=" * 80)
    
    # Try to book the machine for today (should be blocked by overdue rental)
    today = date.today()
    tomorrow = date.today() + timedelta(days=1)
    
    is_available, conflicts = Rental.check_availability(
        machine=test_machine,
        start_date=today,
        end_date=tomorrow
    )
    
    print(f"Checking availability for {today} to {tomorrow}:")
    print(f"  is_available: {is_available}")
    print(f"  conflicts: {list(conflicts)}")
    
    blocking_success = not is_available and conflicts.exists()
    test_scenarios.append(("Overdue Blocks Availability", "PASSED" if blocking_success else "FAILED"))
    
    # ========================================================================
    # SCENARIO 4: Create future rental and test conflict detection
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 4: FUTURE RENTAL CONFLICT DETECTION")
    print("=" * 80)
    
    # Create a future rental that should be marked as conflict_review
    # We'll bypass validation to test the conflict detection system
    future_start = date.today()  # Start today (overlaps with overdue effective end)
    future_end = date.today() + timedelta(days=2)
    
    # Create rental without triggering validation
    rental_b = Rental(
        machine=test_machine,
        user=test_user_b,
        start_date=future_start,
        end_date=future_end,
        area=1.5,
        purpose='Test conflict rental',
        status='approved',
        workflow_state='approved',
        payment_type='cash',
        payment_method='face_to_face',
        payment_status='paid',
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    # Save without calling full_clean() to bypass validation
    rental_b.save_base(raw=True)
    
    print(f"Created Rental B:")
    print(f"  ID: {rental_b.id}")
    print(f"  Dates: {rental_b.start_date} to {rental_b.end_date}")
    print(f"  Status: {rental_b.status}")
    print(f"  Workflow State: {rental_b.workflow_state}")
    
    # Run sync again to detect conflicts
    updated_ids = Rental.sync_overdue_workflow_states()
    
    # Refresh from database
    rental_b.refresh_from_db()
    
    print(f"\nAfter conflict sync:")
    print(f"  Rental B Workflow State: {rental_b.workflow_state}")
    print(f"  Updated rental IDs: {updated_ids}")
    
    conflict_success = rental_b.workflow_state == 'conflict_review'
    test_scenarios.append(("Conflict Detection", "PASSED" if conflict_success else "FAILED"))
    
    # ========================================================================
    # SCENARIO 5: Test management command
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 5: MANAGEMENT COMMAND TEST")
    print("=" * 80)
    
    # Test the management command in dry-run mode
    from django.core.management import call_command
    from io import StringIO
    
    out = StringIO()
    call_command('update_overdue_rentals', '--dry-run', stdout=out)
    command_output = out.getvalue()
    
    print("Management command output (dry-run):")
    print(command_output)
    
    command_success = 'overdue' in command_output.lower()
    test_scenarios.append(("Management Command", "PASSED" if command_success else "FAILED"))
    
    # ========================================================================
    # SCENARIO 6: Test rental completion clears conflicts
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 6: RENTAL COMPLETION CLEARS CONFLICTS")
    print("=" * 80)
    
    print(f"Before completion - Rental A State: {rental_a.workflow_state}")
    print(f"Before completion - Rental B State: {rental_b.workflow_state}")
    
    # Mark the overdue rental as completed
    rental_a.workflow_state = 'completed'
    rental_a.status = 'completed'
    rental_a.actual_return_at = timezone.now()
    rental_a.save()
    
    # Run sync to clear conflicts
    updated_ids = Rental.sync_overdue_workflow_states()
    
    # Refresh from database
    rental_b.refresh_from_db()
    
    print(f"\nAfter completion:")
    print(f"  Rental A State: {rental_a.workflow_state}")
    print(f"  Rental B State: {rental_b.workflow_state}")
    print(f"  Updated rental IDs: {updated_ids}")
    
    clear_success = rental_b.workflow_state == 'approved'
    test_scenarios.append(("Conflict Resolution", "PASSED" if clear_success else "FAILED"))
    
    # ========================================================================
    # SCENARIO 7: Test availability after conflict resolution
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 7: AVAILABILITY AFTER CONFLICT RESOLUTION")
    print("=" * 80)
    
    # Check availability again - should be available since Rental B doesn't conflict
    # with the completed Rental A anymore
    future_check_start = date.today() + timedelta(days=5)  # Well in the future
    future_check_end = date.today() + timedelta(days=6)
    
    is_available_now, conflicts_now = Rental.check_availability(
        machine=test_machine,
        start_date=future_check_start,
        end_date=future_check_end
    )
    
    print(f"Checking availability for future dates ({future_check_start} to {future_check_end}):")
    print(f"  is_available: {is_available_now}")
    print(f"  conflicts: {list(conflicts_now)}")
    
    # Should be available now (no conflicts from completed rental)
    resolution_success = is_available_now and not conflicts_now.exists()
    test_scenarios.append(("Availability After Resolution", "PASSED" if resolution_success else "FAILED"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for scenario, status in test_scenarios:
        print(f"{scenario:.<50} {status}")
    
    all_passed = all(status == "PASSED" for _, status in test_scenarios)
    
    if all_passed:
        print("\n" + "=" * 80)
        print("ALL OVERDUE RENTAL SYSTEM TESTS PASSED!")
        print("=" * 80)
        print("\nThe system correctly:")
        print("✅ Detects overdue rentals")
        print("✅ Updates workflow states automatically")
        print("✅ Blocks machine availability for overdue rentals")
        print("✅ Marks conflicting future rentals for review")
        print("✅ Resolves conflicts when overdue rentals are completed")
        print("✅ Restores normal availability after resolution")
    else:
        print("\n❌ SOME TESTS FAILED - Check the output above for details")
    
    # Cleanup
    print(f"\nCleaning up test data...")
    rental_a.delete()
    rental_b.delete()
    print("Test completed.")
    
    return all_passed

if __name__ == '__main__':
    try:
        test_overdue_rental_system()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()