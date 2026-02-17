"""
Test script to verify notification signals are working
Run with: python manage.py shell < test_notifications.py
"""

from django.contrib.auth import get_user_model
from machines.models import Rental, RiceMillAppointment, Machine
from irrigation.models import WaterIrrigationRequest
from notifications.models import UserNotification
from datetime import date, timedelta

User = get_user_model()

print("=" * 60)
print("Testing Notification Signals")
print("=" * 60)

# Get a test user (assuming there's at least one user)
try:
    test_user = User.objects.filter(is_verified=True).first()
    if not test_user:
        test_user = User.objects.first()
    
    if not test_user:
        print("ERROR: No users found in database")
        exit()
    
    print(f"\nUsing test user: {test_user.username}")
    
    # Count notifications before
    before_count = UserNotification.objects.filter(user=test_user).count()
    print(f"Notifications before test: {before_count}")
    
    # Test 1: Check if there are any pending rentals to approve
    pending_rentals = Rental.objects.filter(status='pending')
    if pending_rentals.exists():
        rental = pending_rentals.first()
        print(f"\nTest 1: Approving rental #{rental.id}")
        print(f"  Machine: {rental.machine.name}")
        print(f"  User: {rental.user.username}")
        
        # Approve the rental
        rental.status = 'approved'
        rental.save()
        
        # Check if notification was created
        new_notifications = UserNotification.objects.filter(
            user=rental.user,
            notification_type='rental_approved'
        ).order_by('-timestamp')
        
        if new_notifications.exists():
            print(f"  ✓ Notification created: {new_notifications.first().message}")
        else:
            print(f"  ✗ No notification created")
    else:
        print("\nTest 1: No pending rentals found to test")
    
    # Test 2: Check if there are any pending rice mill appointments
    pending_appointments = RiceMillAppointment.objects.filter(status='pending')
    if pending_appointments.exists():
        appointment = pending_appointments.first()
        print(f"\nTest 2: Approving rice mill appointment #{appointment.id}")
        print(f"  Machine: {appointment.machine.name}")
        print(f"  User: {appointment.user.username}")
        print(f"  Date: {appointment.appointment_date}")
        
        # Approve the appointment
        appointment.status = 'approved'
        appointment.save()
        
        # Check if notification was created
        new_notifications = UserNotification.objects.filter(
            user=appointment.user,
            notification_type='appointment_approved'
        ).order_by('-timestamp')
        
        if new_notifications.exists():
            print(f"  ✓ Notification created: {new_notifications.first().message}")
        else:
            print(f"  ✗ No notification created")
    else:
        print("\nTest 2: No pending rice mill appointments found to test")
    
    # Test 3: Check if there are any pending irrigation requests
    pending_irrigation = WaterIrrigationRequest.objects.filter(status='pending')
    if pending_irrigation.exists():
        irrigation = pending_irrigation.first()
        print(f"\nTest 3: Approving irrigation request #{irrigation.id}")
        print(f"  Farmer: {irrigation.farmer.username}")
        print(f"  Date: {irrigation.requested_date}")
        
        # Approve the irrigation request
        irrigation.status = 'approved'
        irrigation.save()
        
        # Check if notification was created
        new_notifications = UserNotification.objects.filter(
            user=irrigation.farmer,
            notification_type='irrigation_approved'
        ).order_by('-timestamp')
        
        if new_notifications.exists():
            print(f"  ✓ Notification created: {new_notifications.first().message}")
        else:
            print(f"  ✗ No notification created")
    else:
        print("\nTest 3: No pending irrigation requests found to test")
    
    # Count notifications after
    after_count = UserNotification.objects.count()
    print(f"\n" + "=" * 60)
    print(f"Total notifications in system: {after_count}")
    print("=" * 60)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
