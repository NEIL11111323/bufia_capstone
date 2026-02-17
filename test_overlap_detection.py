"""
Test script to verify overlap detection works correctly
Run with: python manage.py shell < test_overlap_detection.py
"""
from machines.models import Machine, Rental
from django.contrib.auth import get_user_model
from datetime import date, timedelta

User = get_user_model()

print("="*60)
print("OVERLAP DETECTION TEST")
print("="*60)

# Get or create test data
try:
    machine = Machine.objects.first()
    user = User.objects.first()
    
    if not machine or not user:
        print("❌ No machine or user found. Please create test data first.")
        exit()
    
    print(f"\n✅ Using Machine: {machine.name}")
    print(f"✅ Using User: {user.username}")
    
    # Test Case 1: Machine rented today, book tomorrow
    print("\n" + "="*60)
    print("TEST CASE 1: Machine rented today, book tomorrow")
    print("="*60)
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)
    
    print(f"\nExisting Rental: {today} to {today} (today only)")
    print(f"New Booking: {tomorrow} to {day_after} (tomorrow onwards)")
    
    # Check availability
    is_available, conflicts = Rental.check_availability(
        machine=machine,
        start_date=tomorrow,
        end_date=day_after
    )
    
    print(f"\nResult: {'✅ AVAILABLE' if is_available else '❌ BLOCKED'}")
    print(f"Conflicts found: {conflicts.count()}")
    
    if is_available:
        print("✅ CORRECT: User can book tomorrow even though machine is rented today")
    else:
        print("❌ WRONG: User should be able to book tomorrow")
    
    # Test Case 2: Machine rented today, try to book same day
    print("\n" + "="*60)
    print("TEST CASE 2: Machine rented today, try to book same day")
    print("="*60)
    
    print(f"\nExisting Rental: {today} to {today} (today only)")
    print(f"New Booking: {today} to {today} (same day)")
    
    # Check availability
    is_available, conflicts = Rental.check_availability(
        machine=machine,
        start_date=today,
        end_date=today
    )
    
    print(f"\nResult: {'✅ AVAILABLE' if is_available else '❌ BLOCKED'}")
    print(f"Conflicts found: {conflicts.count()}")
    
    if not is_available:
        print("✅ CORRECT: User cannot book same day")
    else:
        print("❌ WRONG: User should NOT be able to book same day")
    
    # Test Case 3: Machine rented Dec 2-5, try to book Dec 4-7
    print("\n" + "="*60)
    print("TEST CASE 3: Overlapping range")
    print("="*60)
    
    start1 = today
    end1 = today + timedelta(days=3)
    start2 = today + timedelta(days=2)
    end2 = today + timedelta(days=5)
    
    print(f"\nExisting Rental: {start1} to {end1}")
    print(f"New Booking: {start2} to {end2}")
    
    # Check availability
    is_available, conflicts = Rental.check_availability(
        machine=machine,
        start_date=start2,
        end_date=end2
    )
    
    print(f"\nResult: {'✅ AVAILABLE' if is_available else '❌ BLOCKED'}")
    print(f"Conflicts found: {conflicts.count()}")
    
    if not is_available:
        print("✅ CORRECT: Overlapping dates are blocked")
    else:
        print("❌ WRONG: Overlapping dates should be blocked")
    
    # Test Case 4: Adjacent days (no overlap)
    print("\n" + "="*60)
    print("TEST CASE 4: Adjacent days (no overlap)")
    print("="*60)
    
    start1 = today
    end1 = today + timedelta(days=1)
    start2 = today + timedelta(days=2)
    end2 = today + timedelta(days=3)
    
    print(f"\nExisting Rental: {start1} to {end1}")
    print(f"New Booking: {start2} to {end2}")
    
    # Check availability
    is_available, conflicts = Rental.check_availability(
        machine=machine,
        start_date=start2,
        end_date=end2
    )
    
    print(f"\nResult: {'✅ AVAILABLE' if is_available else '❌ BLOCKED'}")
    print(f"Conflicts found: {conflicts.count()}")
    
    if is_available:
        print("✅ CORRECT: Adjacent days don't overlap")
    else:
        print("❌ WRONG: Adjacent days should not overlap")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
