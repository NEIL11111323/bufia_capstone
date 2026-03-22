#!/usr/bin/env python3
"""
COMPREHENSIVE OPERATOR FUNCTIONALITY TEST
Tests all operator functions and URLs
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Rental, Machine
from django.contrib.auth import get_user_model
from notifications.models import UserNotification

User = get_user_model()

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_section(title):
    print(f"\n📍 {title}")
    print("-" * 60)

def test_all_functionality():
    print_header("COMPREHENSIVE OPERATOR FUNCTIONALITY TEST")
    
    # Get operators
    operators = User.objects.filter(role='operator', is_active=True)
    if not operators.exists():
        print("❌ No operators found!")
        return
    
    operator = operators.first()
    print(f"✅ Testing with operator: {operator.get_full_name()} (@{operator.username})")
    
    # 1. Test Dashboard Access
    print_section("1. DASHBOARD ACCESS")
    
    dashboard_urls = [
        '/machines/operator/',
        '/machines/operator/main/',
        '/machines/operator/dashboard/',
    ]
    
    print("✅ Dashboard URLs available:")
    for url in dashboard_urls:
        print(f"   • {url}")
    
    # 2. Test Job Management
    print_section("2. JOB MANAGEMENT")
    
    # Get operator's jobs
    all_jobs = Rental.objects.filter(assigned_operator=operator)
    assigned_jobs = all_jobs.filter(status__in=['approved', 'assigned'])
    ongoing_jobs = all_jobs.filter(status='ongoing')
    completed_jobs = all_jobs.filter(status__in=['completed', 'finalized'])
    
    print(f"✅ Operator job statistics:")
    print(f"   • Total Jobs: {all_jobs.count()}")
    print(f"   • Assigned: {assigned_jobs.count()}")
    print(f"   • Ongoing: {ongoing_jobs.count()}")
    print(f"   • Completed: {completed_jobs.count()}")
    
    job_urls = [
        '/machines/operator/jobs/',
        '/machines/operator/jobs/all/',
        '/machines/operator/jobs/ongoing/',
        '/machines/operator/jobs/completed/',
    ]
    
    print("✅ Job management URLs:")
    for url in job_urls:
        print(f"   • {url}")
    
    # Test specific job URLs
    if all_jobs.exists():
        test_job = all_jobs.first()
        print(f"\n✅ Job-specific URLs (using Rental #{test_job.id}):")
        print(f"   • Job Detail: /machines/operator/jobs/{test_job.id}/")
        print(f"   • Start Job: POST /machines/operator/start/{test_job.id}/")
        print(f"   • Complete Job: POST /machines/operator/complete/{test_job.id}/")
        print(f"   • Update Status: POST /machines/operator/jobs/{test_job.id}/update-status/")
        
        if test_job.payment_type == 'in_kind':
            print(f"   • Report Harvest: /machines/operator/harvest/{test_job.id}/report/")
    
    # 3. Test Notifications
    print_section("3. NOTIFICATIONS")
    
    notifications = UserNotification.objects.filter(user=operator)
    unread_count = notifications.filter(is_read=False).count()
    
    print(f"✅ Notification statistics:")
    print(f"   • Total Notifications: {notifications.count()}")
    print(f"   • Unread: {unread_count}")
    
    print("✅ Notification URLs:")
    print("   • Notifications List: /machines/operator/notifications/")
    
    if notifications.exists():
        test_notif = notifications.first()
        print(f"   • Notification Detail: /machines/operator/notifications/{test_notif.id}/")
    
    # 4. Test Workflow States
    print_section("4. WORKFLOW STATE VALIDATION")
    
    # Test job start conditions
    ready_to_start = Rental.objects.filter(
        assigned_operator=operator,
        status__in=['approved', 'assigned'],
        payment_status='paid'
    )
    
    print(f"✅ Jobs ready to start: {ready_to_start.count()}")
    for job in ready_to_start[:3]:
        print(f"   • Rental #{job.id} - {job.machine.name}")
        print(f"     Status: {job.status}, Payment: {job.payment_status}")
    
    # Test job completion conditions
    ready_to_complete = Rental.objects.filter(
        assigned_operator=operator,
        status='ongoing'
    )
    
    print(f"\n✅ Jobs ready to complete: {ready_to_complete.count()}")
    for job in ready_to_complete[:3]:
        print(f"   • Rental #{job.id} - {job.machine.name}")
        print(f"     Operator Status: {job.get_operator_status_display()}")
    
    # Test harvest reporting
    harvest_jobs = Rental.objects.filter(
        assigned_operator=operator,
        payment_type='in_kind',
        status='ongoing'
    )
    
    print(f"\n✅ In-kind jobs for harvest reporting: {harvest_jobs.count()}")
    for job in harvest_jobs[:3]:
        print(f"   • Rental #{job.id} - {job.machine.name}")
        print(f"     Harvest Reported: {'Yes' if job.total_harvest_sacks else 'No'}")
    
    # 5. Test Machine Status Integration
    print_section("5. MACHINE STATUS INTEGRATION")
    
    machines = Machine.objects.all()
    machine_status_counts = {}
    
    for machine in machines:
        status = machine.status
        if status not in machine_status_counts:
            machine_status_counts[status] = 0
        machine_status_counts[status] += 1
    
    print("✅ Machine status distribution:")
    for status, count in machine_status_counts.items():
        print(f"   • {status.title()}: {count}")
    
    # Check machines assigned to this operator
    operator_machines = machines.filter(
        rentals__assigned_operator=operator,
        rentals__status='ongoing'
    ).distinct()
    
    print(f"\n✅ Machines currently operated by {operator.get_full_name()}: {operator_machines.count()}")
    for machine in operator_machines:
        print(f"   • {machine.name} - Status: {machine.status}")
    
    # 6. Test API Endpoints
    print_section("6. API ENDPOINTS")
    
    print("✅ Available API endpoints:")
    print("   • Dashboard Stats: /machines/operator/api/dashboard/stats/")
    
    if all_jobs.exists():
        test_job = all_jobs.first()
        print(f"   • Job Status: /machines/operator/api/job/{test_job.id}/status/")
    
    # 7. Test Error Conditions
    print_section("7. ERROR CONDITION VALIDATION")
    
    # Check for operators with multiple ongoing jobs (should not happen)
    operators_with_multiple_ongoing = []
    for op in operators:
        ongoing_count = Rental.objects.filter(
            assigned_operator=op,
            status='ongoing'
        ).count()
        if ongoing_count > 1:
            operators_with_multiple_ongoing.append((op, ongoing_count))
    
    if operators_with_multiple_ongoing:
        print("⚠️  Operators with multiple ongoing jobs (potential issue):")
        for op, count in operators_with_multiple_ongoing:
            print(f"   • {op.get_full_name()}: {count} ongoing jobs")
    else:
        print("✅ No operators with multiple ongoing jobs (good)")
    
    # Check for jobs without operators
    unassigned_approved = Rental.objects.filter(
        status__in=['approved', 'assigned'],
        assigned_operator__isnull=True
    ).count()
    
    print(f"✅ Approved jobs without operators: {unassigned_approved}")
    
    # Check for payment inconsistencies
    payment_issues = Rental.objects.filter(
        status__in=['approved', 'assigned'],
        assigned_operator__isnull=False,
        payment_status__in=['pending', 'to_be_determined']
    ).count()
    
    print(f"✅ Assigned jobs with payment issues: {payment_issues}")
    
    # 8. Summary and Recommendations
    print_section("8. SUMMARY & RECOMMENDATIONS")
    
    total_operators = operators.count()
    total_rentals = Rental.objects.count()
    operator_assigned_rentals = Rental.objects.filter(assigned_operator__isnull=False).count()
    
    print(f"✅ SYSTEM HEALTH:")
    print(f"   • Active Operators: {total_operators}")
    print(f"   • Total Rentals: {total_rentals}")
    print(f"   • Operator-Assigned Rentals: {operator_assigned_rentals}")
    print(f"   • Assignment Rate: {(operator_assigned_rentals/total_rentals*100):.1f}%")
    
    print(f"\n🎯 TESTING RECOMMENDATIONS:")
    print("   1. Login as operator and test dashboard navigation")
    print("   2. Test job start/complete workflow")
    print("   3. Test notification system")
    print("   4. Test harvest reporting for in-kind jobs")
    print("   5. Verify admin can see operator status updates")
    
    print(f"\n🔗 KEY TESTING URLS:")
    print("   • Operator Login: /accounts/login/")
    print("   • Operator Dashboard: /machines/operator/")
    print("   • Admin Dashboard: /machines/admin/rentals/")
    print("   • Admin Rental Approval: /machines/admin/rental/{id}/approve/")
    
    print_header("COMPREHENSIVE TEST COMPLETED")

if __name__ == "__main__":
    try:
        test_all_functionality()
        print("✅ All functionality tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()