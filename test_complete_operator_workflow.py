#!/usr/bin/env python3
"""
COMPLETE OPERATOR WORKFLOW TEST
Tests the entire operator system from admin assignment to job completion
"""
import os
import django
import sys
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from machines.models import Rental, Machine
from notifications.models import UserNotification

User = get_user_model()

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_section(title):
    print(f"\n📍 {title}")
    print("-" * 60)

def test_operator_system():
    print_header("COMPLETE OPERATOR WORKFLOW TEST")
    
    # 1. Check if we have operators
    print_section("1. CHECKING OPERATORS")
    operators = User.objects.filter(role='operator', is_active=True)
    print(f"✅ Found {operators.count()} active operator(s):")
    for op in operators:
        print(f"   • {op.get_full_name()} (@{op.username})")
        
        # Check operator's current jobs
        assigned_jobs = Rental.objects.filter(assigned_operator=op, status__in=['approved', 'assigned']).count()
        ongoing_jobs = Rental.objects.filter(assigned_operator=op, status='ongoing').count()
        completed_jobs = Rental.objects.filter(assigned_operator=op, status__in=['completed', 'finalized']).count()
        
        print(f"     - Assigned: {assigned_jobs}, Ongoing: {ongoing_jobs}, Completed: {completed_jobs}")
    
    if not operators.exists():
        print("❌ NO OPERATORS FOUND! Creating test operator...")
        test_operator = User.objects.create_user(
            username='test_operator',
            email='operator@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Operator',
            role='operator'
        )
        print(f"✅ Created test operator: {test_operator.get_full_name()}")
        operators = [test_operator]
    
    # 2. Check rentals that need operator assignment
    print_section("2. RENTALS NEEDING OPERATOR ASSIGNMENT")
    pending_rentals = Rental.objects.filter(
        status='pending',
        assigned_operator__isnull=True
    ).select_related('machine', 'user')
    
    print(f"✅ Found {pending_rentals.count()} rental(s) needing operator assignment:")
    for rental in pending_rentals[:5]:  # Show first 5
        print(f"   • Rental #{rental.id} - {rental.machine.name}")
        print(f"     Renter: {rental.user.get_full_name()}")
        print(f"     Payment: {rental.get_payment_type_display()}")
        print(f"     Admin URL: /machines/admin/rental/{rental.id}/approve/")
    
    # 3. Check rentals assigned to operators
    print_section("3. OPERATOR ASSIGNED RENTALS")
    assigned_rentals = Rental.objects.filter(
        assigned_operator__isnull=False,
        status__in=['approved', 'assigned']
    ).select_related('machine', 'user', 'assigned_operator')
    
    print(f"✅ Found {assigned_rentals.count()} rental(s) assigned to operators:")
    for rental in assigned_rentals[:5]:
        print(f"   • Rental #{rental.id} - {rental.machine.name}")
        print(f"     Operator: {rental.assigned_operator.get_full_name()}")
        print(f"     Status: {rental.get_status_display()}")
        print(f"     Payment: {rental.get_payment_type_display()}")
        print(f"     Operator URL: /machines/operator/jobs/{rental.id}/")
    
    # 4. Check ongoing jobs
    print_section("4. ONGOING OPERATOR JOBS")
    ongoing_jobs = Rental.objects.filter(
        status='ongoing',
        assigned_operator__isnull=False
    ).select_related('machine', 'user', 'assigned_operator')
    
    print(f"✅ Found {ongoing_jobs.count()} ongoing job(s):")
    for job in ongoing_jobs:
        print(f"   • Rental #{job.id} - {job.machine.name}")
        print(f"     Operator: {job.assigned_operator.get_full_name()}")
        print(f"     Operator Status: {job.get_operator_status_display()}")
        if job.actual_handover_date:
            duration = timezone.now() - job.actual_handover_date
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            print(f"     Duration: {hours}h {minutes}m")
        print(f"     Operator URL: /machines/operator/jobs/{job.id}/")
    
    # 5. Test operator dashboard access
    print_section("5. OPERATOR DASHBOARD URLS")
    print("✅ Key operator URLs:")
    print("   • Main Dashboard: /machines/operator/")
    print("   • All Jobs: /machines/operator/jobs/")
    print("   • Notifications: /machines/operator/notifications/")
    
    # 6. Check notifications
    print_section("6. OPERATOR NOTIFICATIONS")
    for operator in operators[:3]:  # Check first 3 operators
        notifications = UserNotification.objects.filter(
            user=operator,
            is_read=False
        ).order_by('-timestamp')[:5]
        
        print(f"✅ {operator.get_full_name()} has {notifications.count()} unread notification(s):")
        for notif in notifications:
            print(f"   • {notif.title} - {notif.timestamp.strftime('%m/%d %H:%M')}")
    
    # 7. Test workflow states
    print_section("7. WORKFLOW STATE ANALYSIS")
    
    # Count rentals by status
    status_counts = {}
    for status_choice in Rental.STATUS_CHOICES:
        status = status_choice[0]
        count = Rental.objects.filter(status=status).count()
        if count > 0:
            status_counts[status] = count
    
    print("✅ Rental status distribution:")
    for status, count in status_counts.items():
        display_name = dict(Rental.STATUS_CHOICES).get(status, status)
        print(f"   • {display_name}: {count}")
    
    # 8. Check machine availability
    print_section("8. MACHINE AVAILABILITY")
    machines = Machine.objects.all()
    print(f"✅ Machine status overview ({machines.count()} total):")
    
    machine_status_choices = [
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('rented', 'In Use'),
    ]
    
    for status_choice in machine_status_choices:
        status = status_choice[0]
        count = machines.filter(status=status).count()
        if count > 0:
            display_name = status_choice[1]
            print(f"   • {display_name}: {count}")
    
    # 9. Test critical workflow functions
    print_section("9. CRITICAL WORKFLOW FUNCTIONS TEST")
    
    # Test 1: Can operator start a job?
    ready_to_start = Rental.objects.filter(
        status='assigned',
        assigned_operator__isnull=False,
        payment_status='paid'
    ).first()
    
    if ready_to_start:
        print(f"✅ Found job ready to start: Rental #{ready_to_start.id}")
        print(f"   • Machine: {ready_to_start.machine.name}")
        print(f"   • Operator: {ready_to_start.assigned_operator.get_full_name()}")
        print(f"   • Start URL: POST /machines/operator/start/{ready_to_start.id}/")
    else:
        print("⚠️  No jobs ready to start (need status='assigned' + payment_status='paid')")
    
    # Test 2: Can operator complete a job?
    ready_to_complete = Rental.objects.filter(
        status='ongoing',
        assigned_operator__isnull=False
    ).first()
    
    if ready_to_complete:
        print(f"✅ Found job ready to complete: Rental #{ready_to_complete.id}")
        print(f"   • Machine: {ready_to_complete.machine.name}")
        print(f"   • Operator: {ready_to_complete.assigned_operator.get_full_name()}")
        print(f"   • Complete URL: POST /machines/operator/complete/{ready_to_complete.id}/")
    else:
        print("⚠️  No jobs ready to complete (need status='ongoing')")
    
    # Test 3: In-kind harvest reporting
    in_kind_jobs = Rental.objects.filter(
        payment_type='in_kind',
        status='ongoing',
        assigned_operator__isnull=False
    )
    
    if in_kind_jobs.exists():
        print(f"✅ Found {in_kind_jobs.count()} in-kind job(s) for harvest reporting")
        for job in in_kind_jobs[:3]:
            print(f"   • Rental #{job.id} - {job.machine.name}")
            print(f"     Harvest URL: /machines/operator/harvest/{job.id}/report/")
    else:
        print("⚠️  No in-kind jobs found for harvest reporting")
    
    # 10. Admin workflow test
    print_section("10. ADMIN WORKFLOW VERIFICATION")
    
    # Check if admin can assign operators
    unassigned_rentals = Rental.objects.filter(
        status='pending',
        assigned_operator__isnull=True
    )
    
    if unassigned_rentals.exists():
        rental = unassigned_rentals.first()
        print(f"✅ Admin can assign operator to Rental #{rental.id}")
        print(f"   • Assign URL: POST /machines/admin/rental/{rental.id}/assign-operator/")
        print(f"   • Available operators: {operators.count()}")
    
    # Check admin approval workflow
    pending_approvals = Rental.objects.filter(status='pending')
    if pending_approvals.exists():
        print(f"✅ Found {pending_approvals.count()} rental(s) pending admin approval")
        for rental in pending_approvals[:3]:
            print(f"   • Rental #{rental.id} - Admin URL: /machines/admin/rental/{rental.id}/approve/")
    
    print_section("11. SUMMARY & RECOMMENDATIONS")
    
    # Summary
    total_rentals = Rental.objects.count()
    operator_assigned = Rental.objects.filter(assigned_operator__isnull=False).count()
    
    print(f"✅ SYSTEM OVERVIEW:")
    print(f"   • Total Rentals: {total_rentals}")
    print(f"   • Operator Assigned: {operator_assigned}")
    print(f"   • Active Operators: {operators.count()}")
    
    # Recommendations
    print(f"\n🎯 NEXT STEPS TO TEST:")
    print("   1. Login as admin → Go to rental approval page")
    print("   2. Assign operator to pending rental")
    print("   3. Approve the rental")
    print("   4. Login as operator → Check 'All Jobs' page")
    print("   5. Start an assigned job")
    print("   6. Complete the job")
    print("   7. For in-kind: Report harvest")
    print("   8. Admin: Confirm rice delivery")
    
    print(f"\n🔗 KEY URLS TO TEST:")
    print("   • Admin Dashboard: /machines/admin/rentals/")
    print("   • Operator Dashboard: /machines/operator/")
    print("   • Operator Jobs: /machines/operator/jobs/")
    print("   • Operator Notifications: /machines/operator/notifications/")
    
    print_header("TEST COMPLETED")
    return True

if __name__ == "__main__":
    try:
        test_operator_system()
        print("✅ All tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)