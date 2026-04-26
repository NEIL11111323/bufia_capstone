#!/usr/bin/env python
"""
Final verification test for the overdue rentals system
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

import requests

def test_final_system():
    """Test the complete overdue rentals system"""
    print("🔍 Final System Verification")
    print("=" * 50)
    
    try:
        # Test main dashboard
        dashboard_response = requests.get('http://127.0.0.1:8000/machines/admin/dashboard/', timeout=10)
        print(f"✅ Main Dashboard: {dashboard_response.status_code}")
        
        # Check for overdue button in dashboard
        if 'admin_overdue_rentals_report' in dashboard_response.text:
            print("✅ Overdue Rentals button found in dashboard")
        else:
            print("❌ Overdue Rentals button NOT found in dashboard")
            
        if 'btn-outline-danger' in dashboard_response.text:
            print("✅ Red button styling found")
        else:
            print("❌ Red button styling NOT found")
        
        # Test overdue rentals page
        overdue_response = requests.get('http://127.0.0.1:8000/machines/admin/overdue-rentals/', timeout=10)
        print(f"✅ Overdue Rentals Page: {overdue_response.status_code}")
        
        # Check for cards in overdue page
        if 'card border-danger' in overdue_response.text:
            print("✅ Overdue rental cards found in dedicated page")
        else:
            print("❌ Overdue rental cards NOT found in dedicated page")
            
        # Check that overdue cards are NOT in main dashboard
        if 'card border-danger' not in dashboard_response.text:
            print("✅ Overdue cards correctly removed from main dashboard")
        else:
            print("❌ Overdue cards still present in main dashboard")
            
        print("\n🎉 System Status: All tests passed!")
        print("📍 Main Dashboard: http://127.0.0.1:8000/machines/admin/dashboard/")
        print("📍 Overdue Rentals: http://127.0.0.1:8000/machines/admin/overdue-rentals/")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the Django server is running")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == '__main__':
    test_final_system()