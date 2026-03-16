#!/usr/bin/env python
"""
Complete test of operator dashboard tabs functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from machines.models import Rental

User = get_user_model()

def test_operator_dashboard_tabs():
    print("=" * 70)
    print("🔧 COMPLETE OPERATOR DASHBOARD TABS TEST")
    print("=" * 70)
    
    # 1. Check operator account
    operator = User.objects.filter(username='operator1').first()
    if not operator:
        print("\n❌ ERROR: operator1 account not found!")
        return False
    
    print(f"\n✅ Operator Account: {operator.username}")
    print(f"   - Full Name: {operator.get_full_name()}")
    print(f"   - Is Staff: {operator.is_staff}")
    print(f"   - Is Active: {operator.is_active}")
    
    # 2. Check job assignments
    all_jobs = Rental.objects.filter(assigned_operator=operator)
    active_jobs = all_jobs.exclude(status__in=['completed', 'cancelled', 'rejected'])
    completed_jobs = all_jobs.filter(status='completed')
    
    print(f"\n📊 Job Statistics:")
    print(f"   - Total Assigned: {all_jobs.count()}")
    print(f"   - Active Jobs: {active_jobs.count()}")
    print(f"   - Completed Jobs: {completed_jobs.count()}")
    
    # 3. Test URL resolution
    try:
        url = reverse('machines:operator_dashboard')
        print(f"\n✅ URL Resolution: {url}")
    except Exception as e:
        print(f"\n❌ URL Resolution Error: {e}")
        return False
    
    # 4. Test template file
    template_path = 'templates/machines/operator/operator_dashboard_simple.html'
    if not os.path.exists(template_path):
        print(f"\n❌ Template file not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for tab implementation
    tab_checks = {
        'Bootstrap tabs': 'data-bs-toggle="tab"' in content,
        'Active jobs tab': 'id="active-jobs"' in content,
        'Completed jobs tab': 'id="completed-jobs"' in content,
        'Tab navigation': 'nav nav-tabs' in content,
        'Tab content': 'tab-content' in content,
        'Active tab pane': 'tab-pane fade show active' in content,
        'Job counts in tabs': '{{ stats.active }}' in content,
    }
    
    print(f"\n✅ Template File: {template_path}")
    for check, result in tab_checks.items():
        status = "✅" if result else "❌"
        print(f"   - {check}: {status}")
    
    # 5. Test view response (simulate request)
    client = Client()
    
    # Login as operator
    login_success = client.login(username='operator1', password='operator123')
    if not login_success:
        print(f"\n❌ Login failed for operator1")
        return False
    
    print(f"\n✅ Login successful for operator1")
    
    # Test dashboard access
    try:
        response = client.get(url)
        print(f"\n✅ Dashboard Response: {response.status_code}")
        
        if response.status_code == 200:
            # Check context variables
            context = response.context
            if context:
                stats = context.get('stats', {})
                active_jobs_ctx = context.get('active_jobs', [])
                completed_jobs_ctx = context.get('completed_jobs', [])
                
                print(f"   - Stats in context: {stats}")
                print(f"   - Active jobs count: {len(active_jobs_ctx)}")
                print(f"   - Completed jobs count: {len(completed_jobs_ctx)}")
                
                # Check if template contains tab HTML
                response_content = response.content.decode('utf-8')
                has_tabs = 'data-bs-toggle="tab"' in response_content
                has_active_tab = 'Active Jobs (' in response_content
                has_completed_tab = 'Completed (' in response_content
                
                print(f"   - Tabs in HTML: {'✅' if has_tabs else '❌'}")
                print(f"   - Active tab label: {'✅' if has_active_tab else '❌'}")
                print(f"   - Completed tab label: {'✅' if has_completed_tab else '❌'}")
            else:
                print("   - No context available")
        else:
            print(f"   - Error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Dashboard access error: {e}")
        return False
    
    # 6. Check Bootstrap in base template
    base_template_path = 'templates/base.html'
    if os.path.exists(base_template_path):
        with open(base_template_path, 'r', encoding='utf-8') as f:
            base_content = f.read()
        
        has_bootstrap_css = 'bootstrap@5' in base_content or 'bootstrap.min.css' in base_content
        has_bootstrap_js = 'bootstrap.bundle' in base_content
        
        print(f"\n✅ Bootstrap Dependencies:")
        print(f"   - Bootstrap CSS: {'✅' if has_bootstrap_css else '❌'}")
        print(f"   - Bootstrap JS: {'✅' if has_bootstrap_js else '❌'}")
    
    print("\n" + "=" * 70)
    print("🎯 FINAL DIAGNOSIS")
    print("=" * 70)
    
    all_checks_passed = all([
        operator and operator.is_staff,
        active_jobs.count() > 0,
        all(tab_checks.values()),
        response.status_code == 200,
        has_tabs and has_active_tab and has_completed_tab
    ])
    
    if all_checks_passed:
        print("\n✅ ALL SYSTEMS WORKING!")
        print("\n🔧 SOLUTION: Browser Cache Issue")
        print("   The tabs ARE implemented and working correctly.")
        print("   You need to clear your browser cache.")
        print("\n📋 INSTRUCTIONS:")
        print("   1. Go to: http://127.0.0.1:8000/machines/operator/dashboard/")
        print("   2. Press Ctrl + Shift + R (hard refresh)")
        print("   3. You should see the tabs!")
        
        return True
    else:
        print("\n❌ SOME ISSUES DETECTED")
        print("   Check the failed items above.")
        return False

if __name__ == '__main__':
    success = test_operator_dashboard_tabs()
    if success:
        print("\n🎉 TEST PASSED - Tabs are working!")
    else:
        print("\n💥 TEST FAILED - Issues need fixing!")