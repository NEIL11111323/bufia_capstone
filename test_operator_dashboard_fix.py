#!/usr/bin/env python
"""
Test to verify the operator dashboard is using the correct template and context
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

def test_operator_dashboard():
    """Test operator dashboard template and context"""
    print("🧪 Testing Operator Dashboard Fix")
    print("=" * 40)
    
    # Get operator
    try:
        operator = User.objects.get(username='operator1')
        print(f"✅ Found operator: {operator.get_full_name()}")
    except User.DoesNotExist:
        print("❌ Operator 'operator1' not found")
        return
    
    # Create test client and login
    client = Client()
    login_success = client.login(username='operator1', password='operator123')
    
    if not login_success:
        print("❌ Failed to login as operator")
        return
    
    print("✅ Successfully logged in as operator")
    
    # Test dashboard URL
    dashboard_url = reverse('machines:operator_dashboard')
    print(f"📍 Dashboard URL: {dashboard_url}")
    
    try:
        response = client.get(dashboard_url)
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Dashboard loads successfully")
            
            # Check if using correct template
            template_names = [t.name for t in response.templates]
            print(f"📄 Templates used: {template_names}")
            
            if 'machines/operator/operator_dashboard_clean.html' in template_names:
                print("✅ Using correct clean template")
            else:
                print("❌ Not using clean template")
                print(f"   Expected: machines/operator/operator_dashboard_clean.html")
                print(f"   Found: {template_names}")
            
            # Check context variables
            context = response.context
            if context:
                print("📋 Context variables:")
                if 'stats' in context:
                    stats = context['stats']
                    print(f"   Stats: Active={stats.get('active', 'N/A')}, "
                          f"In Progress={stats.get('in_progress', 'N/A')}, "
                          f"Completed={stats.get('completed', 'N/A')}")
                
                if 'recent_jobs' in context:
                    recent_jobs = context['recent_jobs']
                    print(f"   Recent jobs: {len(recent_jobs)} jobs found")
                    for job in recent_jobs[:3]:  # Show first 3
                        print(f"     • {job.machine.name} for {job.user.get_full_name()}")
                else:
                    print("   ❌ 'recent_jobs' not found in context")
            
        else:
            print(f"❌ Dashboard failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
    
    print("\n🎯 Test Summary")
    print("=" * 40)
    print("The operator dashboard should now be using the clean template.")
    print("If you're still seeing the old interface, try:")
    print("1. Hard refresh the browser (Ctrl+Shift+R)")
    print("2. Clear browser cache")
    print("3. Open in incognito/private mode")

if __name__ == '__main__':
    test_operator_dashboard()