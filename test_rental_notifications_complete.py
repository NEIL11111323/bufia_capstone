"""
Comprehensive Test Script for Rental Request Notifications System

This script tests all four notification scenarios:
1. New rental request submitted
2. Approved rental request
3. Declined rental request
4. Rental schedule conflict detected

Run with: python manage.py shell < test_rental_notifications_complete.py
Or in Django shell: exec(open('test_rental_notifications_complete.py').read())
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

print("Loading Django models...")
from django.contrib.auth import get_user_model
from machines.models import Machine, Rental
from notifications.models import UserNotification
from datetime import date, timedelta
from django.utils import timezone

User = get_user_model()
print("Models loaded successfully!")

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_result(test_name, passed, message=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")

def cleanup_test_data():
    """Clean up test data"""
    print_section("CLEANUP: Removing Test Data")
    
    # Delete test notifications
    deleted_notifs = UserNotification.objects.filter(
        notification_type__in=[
            'rental_submitted',
            'rental_new_request',
            'rental_approved',
            'rental_rejected',
            'rental_conflict',
            'rental_conflict_broadcast',
            'rental_completed',
            'rental_cancelled'
        ]
    ).delete()
    
    print(f"Deleted {deleted_notifs[0]} test notifications")
    
    # Delete test rentals
    test_rentals = Rental.objects.filter(
        start_date__gte=date.today()
    )
    rental_count = test_rentals.count()
    test_rentals.delete()
    
    print(f"Deleted {rental_count} test rentals")

def test_scenario_1_new_rental():
    """Test Scenario 1: New Rental Request Submitted"""
    print_section("TEST SCENARIO 1: New Rental Request Submitted")
    
    try:
        # Get test user and machine
        user = User.objects.filter(is_staff=False, is_active=True).first()
        machine = Machine.objects.filter(is_active=True).first()
        
        if not user or not machine:
            print_result("Setup", False, "No active user or machine found")
            return False
        
        print(f"User: {user.get_full_name()} ({user.username})")
        print(f"Machine: {machine.name}")
        
        # Create rental request
        start_date = date.today() + timedelta(days=5)
        end_date = start_date + timedelta(days=3)
        
        rental = Rental.objects.create(
            machine=machine,
            user=user,
            start_date=start_date,
            end_date=end_date,
            status='pending',
            total_cost=1000.00
        )
        
        print(f"Created rental: {rental.id}")
        print(f"Dates: {start_date} to {end_date}")
        
        # Check user notification
        user_notif = UserNotification.objects.filter(
            user=user,
            notification_type='rental_submitted',
            related_object_id=rental.id
        ).first()
        
        print_result(
            "User Notification Created",
            user_notif is not None,
            f"Message: {user_notif.message if user_notif else 'Not found'}"
        )
        
        # Check admin notifications
        admin_notifs = UserNotification.objects.filter(
            notification_type='rental_new_request',
            related_object_id=rental.id
        )
        
        admin_count = admin_notifs.count()
        expected_admins = User.objects.filter(is_staff=True, is_active=True).count()
        
        print_result(
            "Admin Notifications Created",
            admin_count == expected_admins,
            f"Created {admin_count} notifications for {expected_admins} admins"
        )
        
        if admin_notifs.exists():
            print(f"    Sample message: {admin_notifs.first().message}")
        
        return rental
        
    except Exception as e:
        print_result("Test Execution", False, f"Error: {str(e)}")
        return None

def test_scenario_2_approve_rental(rental):
    """Test Scenario 2: Approved Rental Request"""
    print_section("TEST SCENARIO 2: Approved Rental Request")
    
    if not rental:
        print_result("Setup", False, "No rental provided")
        return False
    
    try:
        user = rental.user
        
        # Approve the rental
        rental.status = 'approved'
        rental.save()
        
        print(f"Approved rental: {rental.id}")
        
        # Check approval notification
        approval_notif = UserNotification.objects.filter(
            user=user,
            notification_type='rental_approved',
            related_object_id=rental.id
        ).first()
        
        print_result(
            "Approval Notification Created",
            approval_notif is not None,
            f"Message: {approval_notif.message if approval_notif else 'Not found'}"
        )
        
        return True
        
    except Exception as e:
        print_result("Test Execution", False, f"Error: {str(e)}")
        return False

def test_scenario_3_reject_rental():
    """Test Scenario 3: Declined Rental Request"""
    print_section("TEST SCENARIO 3: Declined Rental Request")
    
    try:
        # Get test user and machine
        user = User.objects.filter(is_staff=False, is_active=True).first()
        machine = Machine.objects.filter(is_active=True).first()
        
        if not user or not machine:
            print_result("Setup", False, "No active user or machine found")
            return False
        
        # Create rental request
        start_date = date.today() + timedelta(days=10)
        end_date = start_date + timedelta(days=2)
        
        rental = Rental.objects.create(
            machine=machine,
            user=user,
            start_date=start_date,
            end_date=end_date,
            status='pending',
            total_cost=800.00
        )
        
        print(f"Created rental: {rental.id}")
        
        # Reject the rental
        rental.status = 'rejected'
        rental.save()
        
        print(f"Rejected rental: {rental.id}")
        
        # Check rejection notification
        rejection_notif = UserNotification.objects.filter(
            user=user,
            notification_type='rental_rejected',
            related_object_id=rental.id
        ).first()
        
        print_result(
            "Rejection Notification Created",
            rejection_notif is not None,
            f"Message: {rejection_notif.message if rejection_notif else 'Not found'}"
        )
        
        return True
        
    except Exception as e:
        print_result("Test Execution", False, f"Error: {str(e)}")
        return False

def test_scenario_4_conflict_detection():
    """Test Scenario 4: Rental Schedule Conflict Detection"""
    print_section("TEST SCENARIO 4: Rental Schedule Conflict Detection")
    
    try:
        # Get test user and machine
        user = User.objects.filter(is_staff=False, is_active=True).first()
        machine = Machine.objects.filter(is_active=True).first()
        
        if not user or not machine:
            print_result("Setup", False, "No active user or machine found")
            return False
        
        # Create first rental (approved)
        start_date1 = date.today() + timedelta(days=15)
        end_date1 = start_date1 + timedelta(days=5)
        
        rental1 = Rental.objects.create(
            machine=machine,
            user=user,
            start_date=start_date1,
            end_date=end_date1,
            status='approved',
            total_cost=1500.00
        )
        
        print(f"Created first rental: {rental1.id}")
        print(f"Dates: {start_date1} to {end_date1}")
        
        # Test conflict detection
        start_date2 = start_date1 + timedelta(days=2)  # Overlaps
        end_date2 = end_date1 + timedelta(days=2)
        
        is_available, conflicts = Rental.check_availability(
            machine=machine,
            start_date=start_date2,
            end_date=end_date2
        )
        
        print_result(
            "Conflict Detection Works",
            not is_available and conflicts.exists(),
            f"Detected {conflicts.count()} conflicting rental(s)"
        )
        
        if conflicts.exists():
            conflict = conflicts.first()
            print(f"    Conflicting rental: {conflict.id}")
            print(f"    Dates: {conflict.start_date} to {conflict.end_date}")
        
        # Test same-day conflict
        same_day_available, same_day_conflicts = Rental.check_availability(
            machine=machine,
            start_date=start_date1,  # Same start date
            end_date=start_date1     # Same day
        )
        
        print_result(
            "Same-Day Conflict Detection",
            not same_day_available,
            "Same-day bookings are properly blocked"
        )
        
        # Test non-overlapping dates
        future_start = end_date1 + timedelta(days=2)
        future_end = future_start + timedelta(days=3)
        
        future_available, future_conflicts = Rental.check_availability(
            machine=machine,
            start_date=future_start,
            end_date=future_end
        )
        
        print_result(
            "Non-Overlapping Dates Available",
            future_available and not future_conflicts.exists(),
            f"Future dates ({future_start} to {future_end}) are available"
        )
        
        return True
        
    except Exception as e:
        print_result("Test Execution", False, f"Error: {str(e)}")
        return False

def run_all_tests():
    """Run all test scenarios"""
    print_section("RENTAL REQUEST NOTIFICATIONS - COMPREHENSIVE TEST SUITE")
    print("Testing all four notification scenarios...")
    
    # Run tests
    rental = test_scenario_1_new_rental()
    
    if rental:
        test_scenario_2_approve_rental(rental)
    
    test_scenario_3_reject_rental()
    test_scenario_4_conflict_detection()
    
    # Summary
    print_section("TEST SUMMARY")
    
    total_notifs = UserNotification.objects.filter(
        notification_type__in=[
            'rental_submitted',
            'rental_new_request',
            'rental_approved',
            'rental_rejected'
        ]
    ).count()
    
    print(f"Total notifications created: {total_notifs}")
    
    total_rentals = Rental.objects.filter(
        start_date__gte=date.today()
    ).count()
    
    print(f"Total test rentals created: {total_rentals}")
    
    print("\n" + "="*80)
    print("  TEST COMPLETE")
    print("="*80)
    print("\nTo clean up test data, run:")
    print(">>> cleanup_test_data()")

# Run tests automatically
run_all_tests()
