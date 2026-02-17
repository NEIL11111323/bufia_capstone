"""
Debug script to test the rental dashboard view logic
Run with: python manage.py shell < debug_rental_view.py
"""
from machines.models import Rental
from django.db.models import Q, Case, When, Value, IntegerField

print("=" * 60)
print("RENTAL DASHBOARD DEBUG")
print("=" * 60)

# Simulate the view logic
status_filter = 'all'
payment_filter = 'all'
search_query = ''

# Base queryset
rentals = Rental.objects.select_related('machine', 'user').all()
print(f"\n1. Base queryset count: {rentals.count()}")

# Apply filters
if status_filter and status_filter != 'all':
    rentals = rentals.filter(status=status_filter)
    print(f"2. After status filter: {rentals.count()}")
else:
    print(f"2. No status filter applied (showing all)")

if payment_filter == 'verified':
    rentals = rentals.filter(payment_verified=True)
elif payment_filter == 'unverified':
    rentals = rentals.filter(payment_verified=False)
elif payment_filter == 'with_proof':
    rentals = rentals.exclude(payment_slip='')

print(f"3. After payment filter: {rentals.count()}")

# Apply annotation and ordering
rentals = rentals.annotate(
    status_priority=Case(
        When(status='pending', payment_verified=True, then=Value(1)),
        When(status='pending', payment_verified=False, then=Value(2)),
        When(status='approved', then=Value(3)),
        When(status='rejected', then=Value(4)),
        When(status='cancelled', then=Value(5)),
        default=Value(6),
        output_field=IntegerField()
    )
).order_by('status_priority', '-created_at')

print(f"4. After annotation and ordering: {rentals.count()}")

# Get statistics
stats = {
    'total_pending': Rental.objects.filter(status='pending').count(),
    'paid_pending': Rental.objects.filter(
        status='pending',
        payment_verified=True
    ).count(),
    'unpaid_pending': Rental.objects.filter(
        status='pending',
        payment_verified=False
    ).count(),
    'with_payment_proof': Rental.objects.filter(
        status='pending'
    ).exclude(payment_slip='').count(),
    'confirmed_requests': Rental.objects.filter(status='approved').count(),
    'total_requests': Rental.objects.all().count(),
}

print("\n" + "=" * 60)
print("STATISTICS")
print("=" * 60)
for key, value in stats.items():
    print(f"{key}: {value}")

print("\n" + "=" * 60)
print("RENTALS TO DISPLAY")
print("=" * 60)
for rental in rentals:
    print(f"\nID: {rental.id}")
    print(f"  Machine: {rental.machine.name}")
    print(f"  User: {rental.user.username}")
    print(f"  Status: {rental.status}")
    print(f"  Payment Verified: {rental.payment_verified}")
    print(f"  Priority: {rental.status_priority}")
    print(f"  Created: {rental.created_at}")

print("\n" + "=" * 60)
print(f"TOTAL RENTALS TO DISPLAY: {rentals.count()}")
print("=" * 60)
