"""
Test script to verify operator setup
Run with: python manage.py shell < test_operator_setup.py
"""

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

def test_operator_setup():
    """Test operator account and dashboard access"""
    
    print("\n" + "=" * 60)
    print("🧪 TESTING OPERATOR SETUP")
    print("=" * 60)
    
    # Test 1: Check if operator exists
    print("\n1️⃣  Checking operator account...")
    try:
        operator = User.objects.get(username='operator1')
        print(f"   ✅ Operator found: {operator.get_full_name()}")
        print(f"   📧 Email: {operator.email}")
        print(f"   👤 Staff: {operator.is_staff}")
        print(f"   🔐 Active: {operator.is_active}")
    except User.DoesNotExist:
        print("   ❌ Operator 'operator1' not found!")
        print("   💡 Run: python manage.py shell < create_operator_account.py")
        return
    
    # Test 2: Check permissions
    print("\n2️⃣  Checking permissions...")
    if operator.is_staff and not operator.is_superuser:
        print("   ✅ Correct permissions (staff, not superuser)")
    elif operator.is_superuser:
        print("   ⚠️  Warning: Operator is superuser (should be staff only)")
    else:
        print("   ❌ Missing staff permission")
        print("   💡 Fix: operator.is_staff = True; operator.save()")
    
    # Test 3: Check assigned jobs
    print("\n3️⃣  Checking assigned jobs...")
    assigned_jobs = Rental.objects.filter(assigned_operator=operator)
    if assigned_jobs.exists():
        print(f"   ✅ {assigned_jobs.count()} job(s) assigned")
        for rental in assigned_jobs[:3]:
            print(f"      • {rental.machine.name} - {rental.user.get_full_name()}")
    else:
        print("   ℹ️  No jobs assigned yet")
        print("   💡 Admin needs to assign IN-KIND rentals to operator")
    
    # Test 4: Check IN-KIND rentals available for assignment
    print("\n4️⃣  Checking available IN-KIND rentals...")
    available_rentals = Rental.objects.filter(
        payment_type='in_kind',
        status='approved',
        assigned_operator__isnull=True
    )
    if available_rentals.exists():
        print(f"   ✅ {available_rentals.count()} IN-KIND rental(s) available for assignment")
        for rental in available_rentals[:3]:
            print(f"      • {rental.machine.name} - {rental.user.get_full_name()}")
    else:
        print("   ℹ️  No IN-KIND rentals available for assignment")
    
    # Test 5: Dashboard URL
    print("\n5️⃣  Dashboard access...")
    print("   📍 URL: /machines/operator/dashboard/")
    print("   🔑 Login with:")
    print("      Username: operator1")
    print("      Password: operator123")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Operator Account: {'✅ Ready' if operator.is_staff else '❌ Needs setup'}")
    print(f"Assigned Jobs: {assigned_jobs.count()}")
    print(f"Available Jobs: {available_rentals.count()}")
    print("\n💡 NEXT STEPS:")
    if not assigned_jobs.exists() and available_rentals.exists():
        print("   1. Login as admin")
        print("   2. Go to /machines/admin/dashboard/")
        print("   3. Open an IN-KIND rental")
        print("   4. Assign 'Juan Operator' to the job")
    elif assigned_jobs.exists():
        print("   1. Login as operator1")
        print("   2. Go to /machines/operator/dashboard/")
        print("   3. Update job status and submit harvest")
    else:
        print("   1. Create an IN-KIND rental request")
        print("   2. Admin approves the rental")
        print("   3. Admin assigns operator to the job")
    print("=" * 60 + "\n")

# Run the test
if __name__ == '__main__':
    test_operator_setup()
else:
    test_operator_setup()
