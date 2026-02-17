from machines.models import Rental
from bufia.models import Payment
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

rental = Rental.objects.get(id=40)
ct = ContentType.objects.get_for_model(rental)

# Create a test payment
payment = Payment.objects.create(
    user=rental.user,
    payment_type='rental',
    amount=Decimal('4000.00'),
    currency='PHP',
    status='completed',
    content_type=ct,
    object_id=rental.id
)

print(f'Payment created with Transaction ID: {payment.internal_transaction_id}')
print(f'You can now view it at: http://127.0.0.1:8000/machines/rentals/40/')
