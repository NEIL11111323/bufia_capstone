"""
Test script to verify notification system functionality for admin and operators
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import UserNotification
from notifications.operator_notifications import (
    notify_operator_job_assigned,
    notify_operator_job_updated,
    notify_operator_harvest_approved,
    get_operator_notification_count,
    notify_all_operators_announcement
)
from machines.models import Rental
from django.utils import timezone

User = get_user_model()

def test_notification_system():
    """Test notification system for admin and operators"""
    
    print("=" * 80)
    print("NOTIFICATION SYSTEM TEST")
    print("=" * 80)
    
    # 1. Check admin users
    print("\n1. CHECKING ADMIN USERS")
    print("-" * 80)
    admins = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True, role='admin')
    print(f"Found {admins.count()} admin user(s):")
    for admin in admins:
        unread_count = UserNotification.objects.filter(user=admin, is_read=False).count()
        total_count = UserNotification.objects.filter(user=admin).count()
        print(f"  - {admin.username} ({admin.get_full_name()})")
        print(f"    Unread: {unread_count} | Total: {total_count}")
    
    # 2. Check operators
    print("\n2. CHECKING OPERATORS")
    print("-" * 80)
    operators = User.objects.filter(is_staff=True, role='operator')
    print(f"Found {operators.count()} operator(s):")
    for operator in operators:
        unread_count = get_operator_notification_count(operator)
        total_count = UserNotification.objects.filter(user=operator).count()
        active_jobs = Rental.objects.filter(
            assigned_operator=operator,
            status='approved'
        ).exclude(workflow_state='completed').count()
        print(f"  - {operator.username} ({operator.get_full_name()})")
        print(f"    Unread: {unread_count} | Total: {total_count} | Active Jobs: {active_jobs}")
    
    # 3. Check notification types
    print("\n3. NOTIFICATION TYPES BREAKDOWN")
    print("-" * 80)
    notification_types = UserNotification.objects.values('notification_type').distinct()
    for nt in notification_types:
        count = UserNotification.objects.filter(notification_type=nt['notification_type']).count()
        print(f"  - {nt['notification_type']}: {count}")
    
    # 4. Check recent notifications
    print("\n4. RECENT NOTIFICATIONS (Last 10)")
    print("-" * 80)
    recent = UserNotification.objects.all().order_by('-timestamp')[:10]
    for notif in recent:
        status = "✓ Read" if notif.is_read else "✉ Unread"
        print(f"  [{status}] {notif.user.username} - {notif.notification_type}")
        print(f"      {notif.message[:80]}...")
        print(f"      {notif.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # 5. Test operator notifications
    print("\n5. TESTING OPERATOR NOTIFICATION FUNCTIONS")
    print("-" * 80)
    
    if operators.exists():
        test_operator = operators.first()
        print(f"Testing with operator: {test_operator.username}")
        
        # Get a rental assigned to this operator
        test_rental = Rental.objects.filter(assigned_operator=test_operator).first()
        
        if test_rental:
            print(f"  Using rental: #{test_rental.id} - {test_rental.machine.name}")
            
            # Test job update notification
            print("  Testing job update notification...")
            notify_operator_job_updated(test_operator, test_rental, 'assigned', 'traveling')
            print("  ✓ Job update notification created")
            
            # Check if notification was created
            latest_notif = UserNotification.objects.filter(
                user=test_operator,
                notification_type='operator_job_updated'
            ).order_by('-timestamp').first()
            
            if latest_notif:
                print(f"  ✓ Notification verified: {latest_notif.message[:60]}...")
            else:
                print("  ✗ Notification not found")
        else:
            print("  No rental found for this operator")
    else:
        print("  No operators found to test")
    
    # 6. Test broadcast notification
    print("\n6. TESTING BROADCAST NOTIFICATION")
    print("-" * 80)
    if operators.exists():
        print(f"Sending test announcement to {operators.count()} operator(s)...")
        notify_all_operators_announcement(
            "System test: Notification system is functioning correctly.",
            "general"
        )
        print("  ✓ Broadcast notification sent")
    else:
        print("  No operators to broadcast to")
    
    # 7. Check notification routing
    print("\n7. NOTIFICATION ROUTING TEST")
    print("-" * 80)
    test_notifications = UserNotification.objects.all()[:5]
    for notif in test_notifications:
        redirect_url = notif.get_redirect_url()
        print(f"  Type: {notif.notification_type}")
        print(f"  Redirect: {redirect_url or 'None (stays on page)'}")
        print()
    
    # 8. Statistics
    print("\n8. OVERALL STATISTICS")
    print("-" * 80)
    total_notifications = UserNotification.objects.count()
    total_unread = UserNotification.objects.filter(is_read=False).count()
    total_read = UserNotification.objects.filter(is_read=True).count()
    
    rental_notifs = UserNotification.objects.filter(notification_type__icontains='rental').count()
    operator_notifs = UserNotification.objects.filter(notification_type__icontains='operator').count()
    appointment_notifs = UserNotification.objects.filter(notification_type__icontains='appointment').count()
    irrigation_notifs = UserNotification.objects.filter(notification_type__icontains='irrigation').count()
    
    print(f"  Total Notifications: {total_notifications}")
    print(f"  Unread: {total_unread} ({(total_unread/total_notifications*100) if total_notifications > 0 else 0:.1f}%)")
    print(f"  Read: {total_read} ({(total_read/total_notifications*100) if total_notifications > 0 else 0:.1f}%)")
    print()
    print(f"  By Category:")
    print(f"    - Rental: {rental_notifs}")
    print(f"    - Operator: {operator_notifs}")
    print(f"    - Appointment: {appointment_notifs}")
    print(f"    - Irrigation: {irrigation_notifs}")
    
    # 9. Check for issues
    print("\n9. SYSTEM HEALTH CHECK")
    print("-" * 80)
    issues = []
    
    # Check for notifications without users
    orphaned = UserNotification.objects.filter(user__isnull=True).count()
    if orphaned > 0:
        issues.append(f"Found {orphaned} orphaned notifications (no user)")
    
    # Check for very old unread notifications
    from datetime import timedelta
    old_date = timezone.now() - timedelta(days=30)
    old_unread = UserNotification.objects.filter(is_read=False, timestamp__lt=old_date).count()
    if old_unread > 0:
        issues.append(f"Found {old_unread} unread notifications older than 30 days")
    
    # Check for operators without notifications
    operators_without_notifs = []
    for operator in operators:
        if UserNotification.objects.filter(user=operator).count() == 0:
            operators_without_notifs.append(operator.username)
    
    if operators_without_notifs:
        issues.append(f"Operators without notifications: {', '.join(operators_without_notifs)}")
    
    if issues:
        print("  ⚠ Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✓ No issues found - system is healthy")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return {
        'total_notifications': total_notifications,
        'unread': total_unread,
        'admins': admins.count(),
        'operators': operators.count(),
        'issues': len(issues)
    }

if __name__ == '__main__':
    results = test_notification_system()
    
    print("\nSUMMARY:")
    print(f"  Admins: {results['admins']}")
    print(f"  Operators: {results['operators']}")
    print(f"  Total Notifications: {results['total_notifications']}")
    print(f"  Unread: {results['unread']}")
    print(f"  Issues: {results['issues']}")
    
    if results['issues'] == 0:
        print("\n✓ Notification system is functioning correctly!")
    else:
        print(f"\n⚠ Found {results['issues']} issue(s) that need attention")
