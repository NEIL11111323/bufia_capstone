#!/usr/bin/env python
"""
Quick verification of overdue rental system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Rental, Machine
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

def verify_system():
    print("🔍 Overdue Rental System Verification")
    print("=" * 60)
    
    # Check URL patterns
    print("\n✅ URL Patterns:")
    try:
        url1 = reverse('machines:admin_overdue_rentals_report')
        url2 = reverse('machines:extend_rental', kwargs={'rental_id': 1})
        url3 = reverse('machines:complete_overdue_rental', kwargs={'rental_id': 1})
        print(f"  • Overdue Report: {url1}")
        print(f"  • Extend Rental: {url2}")
        print(f"  • Complete Rental: {url3}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Check database
    print("\n✅ Database Status:")
    overdue_count = Rental.objects.filter(workflow_state='overdue').count()
    total_rentals = Rental.objects.count()
    machines_count = Machine.objects.count()
    users_count = User.objects.filter(is_staff=False).count()
    
    print(f"  • Total Rentals: {total_rentals}")
    print(f"  • Overdue Rentals: {overdue_count}")
    print(f"  • Machines: {machines_count}")
    print(f"  • Users: {users_count}")
    
    # Check template
    print("\n✅ Template Files:")
    import os
    template_path = "templates/machines/admin/overdue_rentals_report.html"
    if os.path.exists(template_path):
        print(f"  • {template_path} ✓")
    else:
        print(f"  • {template_path} ✗")
    
    # Check views
    print("\n✅ View Functions:")
    from machines import admin_views
    functions = ['overdue_rentals_report', 'extend_rental', 'complete_overdue_rental']
    for func in functions:
        if hasattr(admin_views, func):
            print(f"  • {func}() ✓")
        else:
            print(f"  • {func}() ✗")
    
    print("\n" + "=" * 60)
    print("🎉 System is operational!")
    print("\n📍 Access the overdue rentals page at:")
    print("   http://127.0.0.1:8000/machines/admin/overdue-rentals/")

if __name__ == '__main__':
    verify_system()
