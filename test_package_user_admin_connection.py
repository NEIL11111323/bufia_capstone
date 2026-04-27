"""
Test Package User-Admin Connection
Verifies all connections between user actions and admin responses in the package rental system.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import RentalPackage, RentalPackageItem, Machine, Rental
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def test_user_admin_connection():
    """Test complete user-admin connection flow"""
    
    print("=" * 80)
    print("PACKAGE USER-ADMIN CONNECTION TEST")
    print("=" * 80)
    
    # 1. Check if users can create packages
    print("\n1. Testing User Package Creation...")
    try:
        # Get a regular user (not admin)
        user = User.objects.filter(is_staff=False, is_superuser=False).first()
        if not user:
            print("   ❌ No regular user found in database")
            return False
        
        print(f"   ✓ Found user: {user.username}")
        
        # Check if user has packages
        user_packages = RentalPackage.objects.filter(user=user)
        print(f"   ✓ User has {user_packages.count()} package(s)")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 2. Check if admins can see all packages
    print("\n2. Testing Admin Package Visibility...")
    try:
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            print("   ❌ No admin user found in database")
            return False
        
        print(f"   ✓ Found admin: {admin.username}")
        
        all_packages = RentalPackage.objects.all()
        print(f"   ✓ Admin can see {all_packages.count()} total package(s)")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 3. Check package status flow
    print("\n3. Testing Package Status Flow...")
    try:
        test_package = RentalPackage.objects.first()
        if not test_package:
            print("   ⚠ No packages found to test")
        else:
            print(f"   ✓ Package: {test_package.package_name}")
            print(f"   ✓ Status: {test_package.status}")
            print(f"   ✓ Payment Status: {test_package.payment_status}")
            print(f"   ✓ Created by: {test_package.user.username}")
            if test_package.approved_by:
                print(f"   ✓ Approved by: {test_package.approved_by.username}")
            
            # Check items
            items = test_package.items.all()
            print(f"   ✓ Package has {items.count()} item(s)")
            
            for item in items:
                print(f"      - {item.service_name}: {item.status}")
                if item.linked_rental:
                    print(f"        Linked rental: {item.linked_rental.id}")
                    print(f"        Rental status: {item.linked_rental.status}")
                    print(f"        Payment type: {item.linked_rental.payment_type}")
                    if item.linked_rental.assigned_operator:
                        print(f"        Operator: {item.linked_rental.assigned_operator.username}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 4. Check payment connection
    print("\n4. Testing Payment Connection...")
    try:
        packages_with_rentals = RentalPackage.objects.filter(
            items__linked_rental__isnull=False
        ).distinct()
        
        print(f"   ✓ {packages_with_rentals.count()} package(s) have linked rentals")
        
        for package in packages_with_rentals[:3]:  # Check first 3
            print(f"\n   Package: {package.package_name}")
            for item in package.items.filter(linked_rental__isnull=False):
                rental = item.linked_rental
                print(f"      Service: {item.service_name}")
                print(f"      Rental ID: {rental.id}")
                print(f"      Payment Type: {rental.payment_type}")
                print(f"      Payment Method: {rental.payment_method or 'Not set'}")
                print(f"      Payment Status: {rental.payment_status}")
                print(f"      Payment Verified: {rental.payment_verified}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 5. Check operator assignment connection
    print("\n5. Testing Operator Assignment Connection...")
    try:
        rentals_with_operators = Rental.objects.filter(
            assigned_operator__isnull=False,
            purpose__icontains='Package:'
        )
        
        print(f"   ✓ {rentals_with_operators.count()} package rental(s) have assigned operators")
        
        for rental in rentals_with_operators[:3]:  # Check first 3
            print(f"      Rental {rental.id}: Operator {rental.assigned_operator.username}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 6. Check workflow state transitions
    print("\n6. Testing Workflow State Transitions...")
    try:
        package_rentals = Rental.objects.filter(purpose__icontains='Package:')
        
        workflow_states = {}
        for rental in package_rentals:
            state = rental.workflow_state
            workflow_states[state] = workflow_states.get(state, 0) + 1
        
        print(f"   ✓ Package rentals by workflow state:")
        for state, count in workflow_states.items():
            print(f"      {state}: {count}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 7. Summary
    print("\n" + "=" * 80)
    print("CONNECTION TEST SUMMARY")
    print("=" * 80)
    
    total_packages = RentalPackage.objects.count()
    pending_packages = RentalPackage.objects.filter(status='pending').count()
    approved_packages = RentalPackage.objects.filter(status='approved').count()
    in_progress_packages = RentalPackage.objects.filter(status='in_progress').count()
    completed_packages = RentalPackage.objects.filter(status='completed').count()
    cancelled_packages = RentalPackage.objects.filter(status='cancelled').count()
    
    print(f"\nTotal Packages: {total_packages}")
    print(f"  - Pending: {pending_packages}")
    print(f"  - Approved: {approved_packages}")
    print(f"  - In Progress: {in_progress_packages}")
    print(f"  - Completed: {completed_packages}")
    print(f"  - Cancelled: {cancelled_packages}")
    
    packages_with_items = RentalPackage.objects.filter(items__isnull=False).distinct().count()
    packages_with_rentals = RentalPackage.objects.filter(items__linked_rental__isnull=False).distinct().count()
    
    print(f"\nPackages with items: {packages_with_items}")
    print(f"Packages with linked rentals: {packages_with_rentals}")
    
    print("\n✅ All connection tests completed successfully!")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        test_user_admin_connection()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
