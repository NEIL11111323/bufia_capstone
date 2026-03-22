from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from machines.models import Rental
from notifications.notification_helpers import create_notification

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'superuser')

@login_required
@user_passes_test(is_admin)
def record_face_to_face_payment(request, rental_id):
    """
    Record face-to-face payment for a rental.
    This must be done before assigning operators or approving the rental.
    """
    rental = get_object_or_404(Rental, id=rental_id)
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    
    # Validate payment method
    if rental.payment_method != 'face_to_face':
        messages.error(request, 'This rental is not set for face-to-face payment.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    
    # Get form data - handle both form formats
    amount_received = request.POST.get('amount_received') or request.POST.get('payment_amount')
    payment_date = request.POST.get('payment_date')
    or_number = request.POST.get('or_number', '') or request.POST.get('receipt_number', '')
    notes = request.POST.get('notes', '')
    received_by = request.POST.get('received_by') or request.user.get_full_name() or request.user.username
    
    # Debug output
    print(f"DEBUG: All POST data: {dict(request.POST)}")
    print(f"DEBUG: amount_received from form: '{amount_received}'")
    print(f"DEBUG: amount_received type: {type(amount_received)}")
    print(f"DEBUG: amount_received bool: {bool(amount_received)}")
    
    # Validation
    if not amount_received:
        print("DEBUG: Validation failed - amount_received is falsy")
        messages.error(request, 'Payment amount is required.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
        
    try:
        amount_received = Decimal(amount_received)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount entered.')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    
    # Check if amount is sufficient
    required_amount = rental.payment_amount or Decimal('0')
    if amount_received < required_amount:
        messages.error(request, f'Insufficient payment! Required: PHP {required_amount}, Received: PHP {amount_received}')
        return redirect('machines:admin_approve_rental', rental_id=rental.id)
    
    # Record the payment
    rental.payment_verified = True
    rental.payment_date = payment_date
    rental.amount_paid = amount_received
    rental.or_number = or_number
    rental.payment_notes = f"Received by: {received_by}\n{notes}" if notes else f"Received by: {received_by}"
    rental.verification_date = timezone.now()
    rental.verified_by = request.user
    rental.save()
    
    # Create notification for the user
    create_notification(
        user=rental.user,
        notification_type='rental_payment_recorded',
        message=f'Your face-to-face payment of PHP {amount_received} for {rental.machine.name} has been recorded.',
        title='Payment Recorded',
        category='payment',
        priority='high',
        related_object_id=rental.id
    )
    
    messages.success(request, f'✅ Payment recorded successfully! Amount: PHP {amount_received}. You can now assign an operator and approve the rental.')
    return redirect('machines:admin_approve_rental', rental_id=rental.id)
