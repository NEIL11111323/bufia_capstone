from machines.models import Rental
from bufia.models import Payment
from django.contrib.contenttypes.models import ContentType

rental = Rental.objects.get(id=40)
print(f'Rental ID: {rental.id}')
print(f'Machine: {rental.machine.name}')
print(f'User: {rental.user.get_full_name()}')
print(f'Status: {rental.status}')
print(f'Payment Verified: {rental.payment_verified}')

ct = ContentType.objects.get_for_model(rental)
payment = Payment.objects.filter(content_type=ct, object_id=rental.id).first()
print(f'Payment exists: {payment is not None}')
if payment:
    print(f'Transaction ID: {payment.internal_transaction_id}')
else:
    print('No payment record found for this rental')
