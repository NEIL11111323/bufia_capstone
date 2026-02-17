"""Simple test to verify rental notifications are working"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Machine, Rental
from notifications.models import UserNotification
from datetime import date, timedelta

User = get_user_model()

def main():
    print("\n" + "="*70)
    print("  RENTAL NOTIFICATIONS TEST")
    print("="*70 + "\n")
    
    # Get a test user and machine
    user = User.objects.filter(is_staff=False, is_active=True).first()
    machine = Machine.objects.first()
    admin = User.objects.filter(is_staff=True, is_active=True).first()
    
    if not user or not machine or not admin:
        print("❌ Missing required data (user, machine, or admin)")
        return
    
    print(f"Test User: {user.get_full_name()} ({user.username})")
    print(f"Test Machine: {machine.name}")
    print(f"Test Admin: {admin.get_full_name()}\n")
    
    # Count notifications before
    notif_count_before = UserNotification.objects.count()
    print(f"Notifications before test: {notif_count_before}")
    
    # Create a rental
    start_date = date.today() + timedelta(days=7)
    end_date = start_date + timedelta(days=3)
    
    print(f"\nCreating rental request...")
    print(f"  Dates: {start_date} to {end_date}")
    
    rental = Rental.objects.create(
        machine=machine,
        user=user,
        start_date=start_date,
        end_date=end_date,
        status='pending',
        payment_amount=1200.00
    )
    
    print(f"  ✓ Rental #{rental.id} created")
    
    # Check notifications after creation
    notif_count_after = UserNotification.objects.count()
    new_notifs = notif_count_after - notif_count_before
    
    print(f"\nNotifications after creation: {notif_count_after}")
    print(f"New notifications: {new_notifs}")
    
    # Check user notification
    user_notif = UserNotification.objects.filter(
        user=user,
        notification_type='rental_submitted',
        related_object_id=rental.id
    ).first()
    
    if user_notif:
        print(f"\n✅ User notification created:")
        print(f"   Type: {user_notif.notification_type}")
        print(f"   Message: {user_notif.message[:80]}...")
    else:
        print(f"\n❌ User notification NOT created")
    
    # Check admin notifications
    admin_notifs = UserNotification.objects.filter(
        notification_type='rental_new_request',
        related_object_id=rental.id
    )
    
    if admin_notifs.exists():
        print(f"\n✅ Admin notifications created: {admin_notifs.count()}")
        print(f"   Message: {admin_notifs.first().message[:80]}...")
    else:
        print(f"\n❌ Admin notifications NOT created")
    
    # Test approval
    print(f"\n\nApproving rental...")
    rental.status = 'approved'
    rental.save()
    
    approval_notif = UserNotification.objects.filter(
        user=user,
        notification_type='rental_approved',
        related_object_id=rental.id
    ).first()
    
    if approval_notif:
        print(f"✅ Approval notification created:")
        print(f"   Message: {approval_notif.message[:80]}...")
    else:
        print(f"❌ Approval notification NOT created")
    
    # Test conflict detection
    print(f"\n\nTesting conflict detection...")
    overlap_start = start_date + timedelta(days=1)
    overlap_end = end_date + timedelta(days=1)
    
    is_available, conflicts = Rental.check_availability(
        machine=machine,
        start_date=overlap_start,
        end_date=overlap_end
    )
    
    if not is_available and conflicts.exists():
        print(f"✅ Conflict detection working:")
        print(f"   Detected {conflicts.count()} conflicting rental(s)")
        print(f"   Dates {overlap_start} to {overlap_end} are blocked")
    else:
        print(f"❌ Conflict detection NOT working")
    
    # Summary
    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)
    
    final_count = UserNotification.objects.count()
    print(f"\nTotal notifications in system: {final_count}")
    print(f"Notifications created in this test: {final_count - notif_count_before}")
    
    print(f"\nTest rental ID: {rental.id}")
    print("To clean up, run: python manage.py shell")
    print(f">>> from machines.models import Rental")
    print(f">>> Rental.objects.get(id={rental.id}).delete()")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
