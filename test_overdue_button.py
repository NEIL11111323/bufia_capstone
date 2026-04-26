#!/usr/bin/env python
"""
Test script to verify the overdue rentals button appears in the dashboard
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

import requests
from django.urls import reverse

def test_overdue_button():
    """Test if the overdue rentals button appears"""
    print("Testing overdue rentals button visibility...")
    
    try:
        # Test URL resolution
        url = reverse('machines:admin_overdue_rentals_report')
        print(f"✅ URL resolves correctly: {url}")
        
        # Test dashboard page
        dashboard_url = "http://127.0.0.1:8000/machines/admin/dashboard/"
        
        try:
            response = requests.get(dashboard_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Dashboard loads successfully (Status: {response.status_code})")
                
                # Check if the button HTML is in the response
                if 'admin_overdue_rentals_report' in response.text:
                    print("✅ Overdue Rentals button URL found in dashboard HTML")
                else:
                    print("❌ Overdue Rentals button URL NOT found in dashboard HTML")
                
                if 'Overdue Rentals' in response.text:
                    print("✅ 'Overdue Rentals' text found in dashboard")
                else:
                    print("❌ 'Overdue Rentals' text NOT found in dashboard")
                    
                if 'btn-outline-danger' in response.text:
                    print("✅ Danger button styling found in dashboard")
                else:
                    print("❌ Danger button styling NOT found in dashboard")
                    
            else:
                print(f"❌ Dashboard failed to load (Status: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to dashboard: {e}")
            print("Make sure the Django server is running on http://127.0.0.1:8000/")
        
        # Test overdue rentals page directly
        overdue_url = f"http://127.0.0.1:8000{url}"
        try:
            response = requests.get(overdue_url, timeout=5)
            print(f"✅ Overdue rentals page accessible (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not access overdue rentals page: {e}")
        
        print("\n🔧 Troubleshooting tips:")
        print("1. Hard refresh your browser (Ctrl+F5 or Cmd+Shift+R)")
        print("2. Clear browser cache")
        print("3. Check browser developer tools for any JavaScript errors")
        print("4. Make sure you're logged in as an admin user")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_overdue_button()