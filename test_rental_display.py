from machines.models import Rental
from django.db.models import Case, When, Value, IntegerField

# Get all rentals
all_rentals = Rental.objects.all()
print(f"Total rentals in database: {all_rentals.count()}")

# Check status breakdown
for status in ['pending', 'approved', 'rejected', 'cancelled']:
    count = Rental.objects.filter(status=status).count()
    print(f"{status.capitalize()}: {count}")

# Test the annotated query
rentals = Rental.objects.select_related('machine', 'user').all().annotate(
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

print(f"\nRentals with priority sorting: {rentals.count()}")
for r in rentals:
    print(f"ID: {r.id}, Status: {r.status}, Machine: {r.machine.name}, User: {r.user.username}, Priority: {r.status_priority}")
