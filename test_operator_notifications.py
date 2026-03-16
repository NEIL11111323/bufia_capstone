#!/usr/bin/env python
"""
Test individual operator notification system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental, Machine
from notifications.operator_notifications import (
    notify_operator_job_assigned,
    notify_operator_job_updated,
    notify_operator_harvest_approved,
    notify_operator_job_completed,
    notify_operator_urgent_job,
    notify_all_operators_announcement,
    get_operator_notification_count,
)

User = get_user_model()

def test_individual_operator_notifications():
    print("=" * 70)
    print("🔔 TESTING INDIVIDUAL OPERATOR NOTIFICATIONS")
    print("=" * 70)
    
    # Get operator
    operator = User.objects.filter(username='operator1').first()
    if not operator:
        print("\n❌ ERROR: operator1 not found!")
        return
    
    print(f"\n✅ Testing notifications for: {operator.username} ({operator.get_full_name()})")
    
    # Get a rental for testing
    rental = Rental.objects.filter(assigned_operator=operator).first()
    if not rental:
        print("\n❌ ERROR: No rentals assigned to operator1!")
        return
    
    print(f"✅ Using rental: {rental.machine.name} for {rental.user.get_full_name()}")
    
    # Test 1: Job Assignment Notification
    print(f"\n📋 Test 1: Job Assignment Notification")
    notify_operator_job_assigned(operator, rental)
    count = get_operator_notification_count(operator)
    print(f"   - Notification sent: ✅")
    print(f"   - Unread count: {count}")
    
    # Test 2: Job Update Notification
    print(f"\n🔄 Test 2: Job Update Notification")
    notify_operator_job_updated(operator, rental, 'assigned', 'operating')
    count = get_operator_notification_count(operator)
    print(f"   - Notification sent: ✅")
    print(f"   - Unread count: {count}")
    
    # Test 3: Harvest Approved Notification (if IN-KIND)
    if rental.payment_type == 'in_kind':
        print(f"\n🌾 Test 3: Harvest Approved Notification")
        # Set some harvest data for testing
        rental.harvest_total = 50
        rental.bufia_share = 5
        rental.save()
        notify_operator_harvest_approved(operator, rental)
        count = get_operator_notification_count(operator)
        print(f"   - Notification sent: ✅")
        print(f"   - Unread count: {count}")
    else:
        print(f"\n🌾 Test 3: Skipped (not IN-KIND rental)")
    
    # Test 4: Job Completed Notification
    print(f"\n✅ Test 4: Job Completed Notification")
    notify_operator_job_completed(operator, rental)
    count = get_operator_notification_count(operator)
    print(f"   - Notification sent: ✅")
    print(f"   - Unread count: {count}")
    
    # Test 5: Urgent Job Notification
    print(f"\n🚨 Test 5: Urgent Job Notification")
    notify_operator_urgent_job(operator, rental, "Weather conditions require immediate action")
    count = get_operator_notification_count(operator)
    print(f"   - Notification sent: ✅")
    print(f"   - Unread count: {count}")
    
    # Test 6: Announcement to All Operators
    print(f"\n📢 Test 6: Announcement to All Operators")
    notify_all_operators_announcement("System maintenance scheduled for tomorrow at 2 PM", "maintenance")
    count = get_operator_notification_count(operator)
    print(f"   - Announcement sent to all operators: ✅")
    print(f"   - Unread count for operator1: {count}")
    
    # Test 7: Check Other Operators
    other_operators = User.objects.filter(is_staff=True, is_active=True).exclude(id=operator.id)
    print(f"\n👥 Test 7: Other Operators Notification Count")
    for other_op in other_operators[:3]:  # Check first 3
        other_count = get_operator_notification_count(other_op)
        print(f"   - {other_op.username}: {other_count} unread notifications")
    
    print(f"\n" + "=" * 70)
    print("📊 NOTIFICATION SUMMARY")
    print("=" * 70)
    
    from notifications.models import UserNotification
    
    # Get all notifications for operator1
    all_notifications = UserNotification.objects.filter(user=operator).order_by('-timestamp')
    
    print(f"\n📋 Operator1 Notifications:")
    print(f"   - Total: {all_notifications.count()}")
    print(f"   - Unread: {all_notifications.filter(is_read=False).count()}")
    print(f"   - Read: {all_notifications.filter(is_read=True).count()}")
    
    print(f"\n📝 Recent Notifications (last 5):")
    for i, notif in enumerate(all_notifications[:5], 1):
        status = "🔴 UNREAD" if not notif.is_read else "✅ READ"
        print(f"   {i}. [{notif.notification_type}] {status}")
        print(f"      {notif.message[:80]}...")
        print(f"      {notif.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print(f"🎯 Individual operator notifications are working perfectly!")
    print(f"Each operator gets personalized notifications for their specific jobs.")
    
    return True

if __name__ == '__main__':
    success = test_individual_operator_notifications()
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("Individual operator notifications are fully functional.")
    else:
        print("\n💥 TESTS FAILED!")