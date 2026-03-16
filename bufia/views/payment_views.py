from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from machines.models import Rental, RiceMillAppointment
from irrigation.models import WaterIrrigationRequest

# Import and configure Stripe
try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None
    print("WARNING: Stripe module not found. Payment features will not work.")
except Exception as e:
    stripe = None
    print(f"WARNING: Error configuring Stripe: {e}")


@login_required
def create_rental_payment(request, rental_id):
    """Create a Stripe Checkout session for rental payment"""
    rental = get_object_or_404(Rental, pk=rental_id, user=request.user)

    if rental.payment_type == 'in_kind':
        messages.info(request, 'This rental uses IN-KIND settlement. Online payment is not required.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.payment_method != 'online':
        messages.info(request, 'This rental is configured for face-to-face payment, not online checkout.')
        return redirect('machines:rental_detail', pk=rental_id)
    
    # Check if Stripe is available
    if stripe is None:
        messages.error(request, 'Payment system is not configured. Please contact administrator.')
        return redirect('machines:rental_detail', pk=rental_id)
    
    if rental.status != 'approved':
        messages.info(request, 'Online payment becomes available after the rental is approved by admin.')
        return redirect('machines:rental_detail', pk=rental_id)

    if rental.payment_verified or rental.payment_status == 'paid':
        messages.info(request, 'This rental payment has already been verified.')
        return redirect('machines:rental_detail', pk=rental_id)

    try:
        # Calculate amount based on rental details
        recalculated_amount = rental.calculate_payment_amount()
        
        if recalculated_amount <= 0:
            messages.error(request, 'Unable to calculate rental amount. Please contact administrator.')
            return redirect('machines:rental_detail', pk=rental_id)

        if rental.payment_amount != recalculated_amount:
            rental.payment_amount = recalculated_amount
            rental.save(update_fields=['payment_amount'])
        
        # Create Payment record with internal transaction ID before Stripe checkout
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        
        content_type = ContentType.objects.get_for_model(Rental)
        payment_obj, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=rental.id,
            defaults={
                'user': request.user,
                'payment_type': 'rental',
                'amount': rental.payment_amount or recalculated_amount,
                'currency': 'PHP',
                'status': 'pending',
            }
        )
        
        # Update existing payment if needed
        if not created and payment_obj.status == 'pending':
            payment_obj.amount = rental.payment_amount or recalculated_amount
            payment_obj.save(update_fields=['amount'])

        # Legacy parser retained for backward compatibility with old records.
        # The checkout amount now uses rental.payment_amount/recalculated_amount.
        try:
            # Remove currency symbols and extract numbers
            price_str = str(rental.machine.current_price).replace('₱', '').replace('$', '').replace(',', '').strip()
            # Extract first number found
            import re
            price_match = re.search(r'\d+\.?\d*', price_str)
            if price_match:
                price_value = float(price_match.group())
            else:
                # Default price if can't parse
                price_value = 100.0
        except:
            price_value = 100.0
        
        amount = int(Decimal(str(rental.payment_amount or recalculated_amount)) * 100)  # Convert to centavos
        
        # Create Stripe Checkout Session with proper redirect configuration
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=rental&id={rental_id}&transaction_id={payment_obj.internal_transaction_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=rental&id={rental_id}'
        
        # Debug: Print URLs
        print(f"Success URL: {success_url}")
        print(f"Cancel URL: {cancel_url}")
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'php',  # Changed to PHP for Philippine Peso
                    'unit_amount': amount,  # Amount in centavos
                    'product_data': {
                        'name': f'Machine Rental: {rental.machine.name}',
                        'description': f'Rental from {rental.start_date} to {rental.end_date} - {rental.area} hectares' if rental.area else f'Rental from {rental.start_date} to {rental.end_date}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'rental_id': rental_id,
                'user_id': request.user.id,
                'type': 'rental',
                'area': str(rental.area) if rental.area else '0',
                'amount': str(rental.payment_amount or recalculated_amount or '0'),
                'internal_transaction_id': payment_obj.internal_transaction_id,
            },
            # Configure to show success page briefly then redirect
            submit_type='pay',
        )
        
        # Store Stripe session_id in Payment record immediately after creation
        payment_obj.stripe_session_id = checkout_session.id
        payment_obj.save(update_fields=['stripe_session_id'])
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f'Error creating payment session: {str(e)}')
        return redirect('machines:rental_detail', pk=rental_id)


@login_required
def create_irrigation_payment(request, irrigation_id):
    """Create a Stripe Checkout session for irrigation request payment"""
    irrigation_request = get_object_or_404(WaterIrrigationRequest, pk=irrigation_id, farmer=request.user)
    
    # Check if Stripe is available
    if stripe is None:
        messages.error(request, 'Payment system is not configured. Please contact administrator.')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)
    
    # Check if request is already paid or approved
    if irrigation_request.status == 'approved':
        messages.info(request, 'This irrigation request has already been approved.')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)
    
    try:
        # Calculate amount based on area size and duration
        # Example: $10 per hectare per hour
        amount_usd = irrigation_request.area_size * irrigation_request.duration_hours * 10
        amount = int(amount_usd * 100)  # Convert to cents
        
        # Create Payment record with internal transaction ID before Stripe checkout
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        
        content_type = ContentType.objects.get_for_model(WaterIrrigationRequest)
        payment_obj, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=irrigation_request.id,
            defaults={
                'user': request.user,
                'payment_type': 'irrigation',
                'amount': amount_usd,
                'currency': 'USD',
                'status': 'pending',
            }
        )
        
        # Update existing payment if needed
        if not created and payment_obj.status == 'pending':
            payment_obj.amount = amount_usd
            payment_obj.save(update_fields=['amount'])
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=irrigation&id={irrigation_id}&transaction_id={payment_obj.internal_transaction_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=irrigation&id={irrigation_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': amount,
                    'product_data': {
                        'name': f'Irrigation Service',
                        'description': f'{irrigation_request.area_size} hectares for {irrigation_request.duration_hours} hours on {irrigation_request.requested_date}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'irrigation_id': irrigation_id,
                'user_id': request.user.id,
                'type': 'irrigation',
                'internal_transaction_id': payment_obj.internal_transaction_id,
            }
        )
        
        # Store Stripe session_id in Payment record immediately after creation
        payment_obj.stripe_session_id = checkout_session.id
        payment_obj.save(update_fields=['stripe_session_id'])
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f'Error creating payment session: {str(e)}')
        return redirect('irrigation:irrigation_request_detail', pk=irrigation_id)


@login_required
def create_appointment_payment(request, appointment_id):
    """Create a Stripe Checkout session for rice mill appointment payment"""
    appointment = get_object_or_404(RiceMillAppointment, pk=appointment_id, user=request.user)
    
    # Check if Stripe is available
    if stripe is None:
        messages.error(request, 'Payment system is not configured. Please contact administrator.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)
    
    # Check if appointment is already paid or approved
    if appointment.status == 'approved':
        messages.info(request, 'This appointment has already been approved.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)
    
    try:
        # Calculate amount based on rice quantity
        # Rate: 150 PHP per kilogram
        amount_php = float(appointment.rice_quantity) * 150
        amount_cents = int(amount_php * 100)  # Convert to centavos
        
        # Create Payment record with internal transaction ID before Stripe checkout
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        
        content_type = ContentType.objects.get_for_model(RiceMillAppointment)
        payment_obj, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=appointment.id,
            defaults={
                'user': request.user,
                'payment_type': 'appointment',
                'amount': amount_php,
                'currency': 'PHP',
                'status': 'pending',
            }
        )
        
        # Update existing payment if needed
        if not created and payment_obj.status == 'pending':
            payment_obj.amount = amount_php
            payment_obj.save(update_fields=['amount'])
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=appointment&id={appointment_id}&transaction_id={payment_obj.internal_transaction_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=appointment&id={appointment_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'php',  # Philippine Peso
                    'unit_amount': amount_cents,
                    'product_data': {
                        'name': f'Rice Mill Service: {appointment.machine.name}',
                        'description': f'{appointment.rice_quantity} kg @ ₱150/kg on {appointment.appointment_date} ({appointment.get_time_slot_display()})',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'appointment_id': appointment_id,
                'user_id': request.user.id,
                'type': 'appointment',
                'internal_transaction_id': payment_obj.internal_transaction_id,
            }
        )
        
        # Store Stripe session_id in Payment record immediately after creation
        payment_obj.stripe_session_id = checkout_session.id
        payment_obj.save(update_fields=['stripe_session_id'])
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f'Error creating payment session: {str(e)}')
        return redirect('machines:ricemill_appointment_detail', pk=appointment_id)


@login_required
def payment_success(request):
    """Handle successful payment"""
    session_id = request.GET.get('session_id')
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')
    transaction_id = request.GET.get('transaction_id')  # Get internal transaction ID
    
    if not session_id:
        messages.error(request, 'Invalid payment session.')
        return redirect('dashboard')
    
    context = {
        'transaction_id': transaction_id,
        'payment_type': payment_type,
        'item_id': item_id,
    }
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Try to get the Payment record
        from bufia.models import Payment
        payment = Payment.objects.filter(stripe_session_id=session_id).first()
        if payment:
            context['transaction_id'] = payment.internal_transaction_id
        
        # Verify payment was successful
        if session.payment_status == 'paid':
            paid_amount = (Decimal(str(session.get('amount_total', 0))) / Decimal('100')).quantize(Decimal('0.01'))
            # Update the corresponding record based on type
            if payment_type == 'rental':
                rental = get_object_or_404(Rental, pk=item_id, user=request.user)
                # Mark payment as verified but keep status as pending for admin approval
                rental.payment_verified = True
                rental.payment_method = 'online'
                rental.payment_date = timezone.now()
                rental.stripe_session_id = session_id
                rental.payment_status = 'paid'
                if paid_amount > 0:
                    rental.payment_amount = paid_amount
                rental.save()
                
                # Create Payment record if it doesn't exist
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                content_type = ContentType.objects.get_for_model(Rental)
                payment_obj, created = Payment.objects.get_or_create(
                    content_type=content_type,
                    object_id=rental.id,
                    defaults={
                        'user': request.user,
                        'payment_type': 'rental',
                        'amount': paid_amount if paid_amount > 0 else (rental.payment_amount or 0),
                        'currency': 'PHP',
                        'status': 'completed',
                        'stripe_session_id': session_id,
                        'stripe_payment_intent_id': session.get('payment_intent'),
                        'paid_at': timezone.now(),
                    }
                )
                
                # If payment already existed, update it
                if not created:
                    if paid_amount > 0:
                        payment_obj.amount = paid_amount
                    payment_obj.status = 'completed'
                    payment_obj.stripe_session_id = session_id
                    payment_obj.stripe_payment_intent_id = session.get('payment_intent')
                    payment_obj.paid_at = timezone.now()
                    payment_obj.save()
                
                # Get the transaction ID from the payment object
                if payment_obj:
                    context['transaction_id'] = payment_obj.internal_transaction_id
                
                context['rental'] = rental
                context['machine_name'] = rental.machine.name
                context['amount'] = rental.payment_amount if rental.payment_amount else None
                
                # Notify user
                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='rental_payment_completed',
                    message=f'Payment received for {rental.machine.name}. Your rental is now pending admin approval.',
                    related_object_id=rental.id
                )
                
                # Notify admins about paid rental waiting for approval
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='rental_payment_received',
                        message=f'Payment received for rental request from {request.user.get_full_name()} for {rental.machine.name}. Please review and approve.',
                        related_object_id=rental.id
                    )
                
                messages.success(request, f'✅ Payment successful! Your rental for {rental.machine.name} is now pending admin approval.')
                # Redirect to rental detail page with receipt display
                return redirect('machines:rental_detail', pk=rental.id)
                
            elif payment_type == 'irrigation':
                irrigation = get_object_or_404(WaterIrrigationRequest, pk=item_id, farmer=request.user)
                irrigation.status = 'approved'  # Auto-approve after payment
                irrigation.save()
                
                context['irrigation'] = irrigation
                context['amount'] = f'${irrigation.area_size * irrigation.duration_hours * 10:.2f}'
                
                messages.success(request, f'Payment successful! Your irrigation request has been approved.')
                return render(request, 'machines/payment_success.html', context)
                
            elif payment_type == 'appointment':
                appointment = get_object_or_404(RiceMillAppointment, pk=item_id, user=request.user)
                appointment.status = 'approved'  # Auto-approve after payment
                appointment.save()
                
                # Update the Payment record
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                content_type = ContentType.objects.get_for_model(RiceMillAppointment)
                payment_obj = Payment.objects.filter(
                    content_type=content_type,
                    object_id=appointment.id
                ).first()
                
                if payment_obj:
                    payment_obj.status = 'completed'
                    payment_obj.stripe_session_id = session_id
                    payment_obj.stripe_payment_intent_id = session.get('payment_intent')
                    payment_obj.paid_at = timezone.now()
                    payment_obj.save()
                    context['transaction_id'] = payment_obj.internal_transaction_id
                
                context['appointment'] = appointment
                amount_php = float(appointment.rice_quantity) * 150
                context['amount'] = f'₱{amount_php:,.2f}'
                
                # Notify user about successful payment
                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='appointment_payment_completed',
                    message=f'Payment successful! Your rice mill appointment for {appointment.appointment_date} has been approved.',
                    related_object_id=appointment.id
                )
                
                # Notify admins about approved appointment
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='appointment_approved',
                        message=f'Rice mill appointment approved for {request.user.get_full_name()} on {appointment.appointment_date}.',
                        related_object_id=appointment.id
                    )
                
                messages.success(request, f'Payment successful! Your rice mill appointment has been approved.')
                return render(request, 'machines/payment_success.html', context)
                
            elif payment_type == 'membership':
                from users.models import MembershipApplication
                membership = get_object_or_404(MembershipApplication, pk=item_id, user=request.user)
                membership.payment_status = 'paid'
                membership.payment_method = 'online'
                membership.payment_date = timezone.now()
                membership.save()
                
                # Generate transaction ID
                transaction_id = f'BUFIA-MEM-{membership.id:05d}'
                
                # Notify user about successful payment
                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='membership',
                    message=f'Payment successful! Your membership fee has been paid (Transaction ID: {transaction_id}). Your application is now pending admin approval.',
                    related_object_id=membership.pk
                )
                
                # Notify admins about paid membership application
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='membership',
                        message=f'Membership payment received from {request.user.get_full_name()} (Transaction ID: {transaction_id}). Application is ready for review.',
                        related_object_id=membership.pk
                    )
                
                # Also notify Hazel Osorio specifically
                try:
                    hazel = User.objects.filter(
                        first_name__icontains='hazel',
                        last_name__icontains='osorio'
                    ).first()
                    if hazel and hazel not in admins:
                        UserNotification.objects.create(
                            user=hazel,
                            notification_type='membership',
                            message=f'Membership payment received from {request.user.get_full_name()} (Transaction ID: {transaction_id}). Application is ready for review.',
                            related_object_id=membership.pk
                        )
                except Exception:
                    pass  # Silently fail if user not found
                
                messages.success(request, f'✅ Payment successful! Your ₱500 membership fee has been paid. Transaction ID: {transaction_id}. Your application is now pending admin approval.')
                # Redirect to dashboard instead of payment success page
                return redirect('dashboard')
        else:
            messages.warning(request, 'Payment is being processed. Please check back later.')
            
    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
    
    return redirect('dashboard')


@login_required
def payment_cancelled(request):
    """Handle cancelled payment"""
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')
    
    messages.warning(request, 'Payment was cancelled. You can try again when ready.')
    
    # Redirect back to the appropriate detail page
    if payment_type == 'rental':
        return redirect('machines:rental_detail', pk=item_id)
    elif payment_type == 'irrigation':
        return redirect('irrigation:irrigation_request_detail', pk=item_id)
    elif payment_type == 'appointment':
        return redirect('machines:ricemill_appointment_detail', pk=item_id)
    
    return redirect('dashboard')


@csrf_exempt
@csrf_exempt
def stripe_webhook(request):
    """
    Enhanced webhook handler that:
    1. Validates Stripe signature
    2. Extracts payment_intent and charge IDs
    3. Locates payment by stripe_payment_intent_id
    4. Updates payment status and stripe_charge_id
    5. Logs event with internal transaction ID
    """
    import logging
    
    logger = logging.getLogger('bufia.payments.webhook')
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload in webhook: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in webhook: {e}")
        return HttpResponse(status=400)

    # Log the webhook event
    logger.info(f"Received webhook event: {event['type']} - {event.get('id', 'unknown')}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        payment_type = metadata.get('type')
        
        # Extract payment_intent and charge IDs from webhook
        payment_intent_id = session.get('payment_intent')
        
        # Get charge ID from payment intent if available
        charge_id = None
        if payment_intent_id:
            try:
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                if payment_intent.charges and payment_intent.charges.data:
                    charge_id = payment_intent.charges.data[0].id
            except Exception as e:
                logger.warning(f"Could not retrieve charge ID for payment_intent {payment_intent_id}: {e}")

        # Locate Payment by stripe_payment_intent_id or session_id
        from bufia.models import Payment
        payment_record = None
        
        # First try to find by payment_intent_id (most reliable)
        if payment_intent_id:
            try:
                payment_record = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                logger.info(f"Found payment record {payment_record.internal_transaction_id} for payment_intent {payment_intent_id}")
            except Payment.DoesNotExist:
                logger.warning(f"No payment record found for payment_intent_id: {payment_intent_id}")
            except Payment.MultipleObjectsReturned:
                logger.error(f"Multiple payment records found for payment_intent_id: {payment_intent_id}")
                payment_record = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
        
        # If not found by payment_intent_id, try by session_id as fallback
        if not payment_record:
            session_id = session.get('id')
            if session_id:
                try:
                    payment_record = Payment.objects.get(stripe_session_id=session_id)
                    logger.info(f"Found payment record {payment_record.internal_transaction_id} for session_id {session_id}")
                    
                    # Update payment_intent_id if it was missing
                    if payment_intent_id and not payment_record.stripe_payment_intent_id:
                        payment_record.stripe_payment_intent_id = payment_intent_id
                        payment_record.save(update_fields=['stripe_payment_intent_id'])
                        logger.info(f"Updated payment {payment_record.internal_transaction_id} with payment_intent_id")
                        
                except Payment.DoesNotExist:
                    logger.warning(f"No payment record found for session_id: {session_id}")
                except Payment.MultipleObjectsReturned:
                    logger.error(f"Multiple payment records found for session_id: {session_id}")
                    payment_record = Payment.objects.filter(stripe_session_id=session_id).first()

        # Handle missing payment records gracefully
        if not payment_record:
            # Create alert for admin review
            logger.error(f"Payment record not found for webhook event - Payment Intent: {payment_intent_id}, Session: {session.get('id')}")
            
            # Try to create payment record from webhook data if we have enough information
            if payment_type and metadata.get('user_id'):
                try:
                    user = get_user_model().objects.get(pk=metadata.get('user_id'))
                    amount = (Decimal(str(session.get('amount_total', 0))) / Decimal('100')).quantize(Decimal('0.01'))
                    
                    # Create payment record from webhook
                    payment_record = Payment.objects.create(
                        user=user,
                        payment_type=payment_type,
                        amount=amount,
                        currency='PHP' if payment_type in ['rental', 'appointment', 'membership'] else 'USD',
                        status='completed',
                        stripe_session_id=session.get('id'),
                        stripe_payment_intent_id=payment_intent_id,
                        stripe_charge_id=charge_id,
                        paid_at=timezone.now(),
                    )
                    
                    logger.info(f"Created payment record from webhook - Transaction ID: {payment_record.internal_transaction_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create payment record from webhook: {e}")
                    return HttpResponse(status=200)  # Acknowledge webhook but log error

        # Update Payment with stripe_charge_id and status
        if payment_record:
            try:
                update_fields = []
                
                # Update charge ID if available
                if charge_id and payment_record.stripe_charge_id != charge_id:
                    payment_record.stripe_charge_id = charge_id
                    update_fields.append('stripe_charge_id')
                
                # Update status to completed
                if payment_record.status != 'completed':
                    payment_record.status = 'completed'
                    update_fields.append('status')
                
                # Update paid_at timestamp
                if not payment_record.paid_at:
                    payment_record.paid_at = timezone.now()
                    update_fields.append('paid_at')
                
                if update_fields:
                    payment_record.save(update_fields=update_fields)
                    logger.info(f"Updated payment {payment_record.internal_transaction_id}: {', '.join(update_fields)}")
                
                # Log webhook event with both internal and Stripe IDs
                logger.info(f"Webhook processed successfully - Internal ID: {payment_record.internal_transaction_id}, Stripe Payment Intent: {payment_intent_id}, Stripe Charge: {charge_id}")
                
            except Exception as e:
                logger.error(f"Error updating payment record {payment_record.internal_transaction_id}: {e}")

        # Handle payment type specific logic
        if payment_type == 'rental':
            rental_id = metadata.get('rental_id')
            user_id = metadata.get('user_id')
            if rental_id and user_id:
                try:
                    rental = Rental.objects.get(pk=rental_id)
                    user = get_user_model().objects.get(pk=user_id)
                    paid_amount = (Decimal(str(session.get('amount_total', 0))) / Decimal('100')).quantize(Decimal('0.01'))
                    
                    # Use the helper function to record payment
                    payment_obj = _record_rental_online_payment(
                        rental,
                        user,
                        session.get('id'),
                        payment_intent_id=payment_intent_id,
                        paid_amount=paid_amount,
                    )
                    
                    logger.info(f"Rental payment recorded - Transaction ID: {payment_obj.internal_transaction_id}, Rental ID: {rental_id}")
                    
                except (Rental.DoesNotExist, get_user_model().DoesNotExist) as e:
                    logger.error(f"Error processing rental webhook - rental_id: {rental_id}, user_id: {user_id}, error: {e}")

        elif payment_type == 'irrigation':
            irrigation_id = metadata.get('irrigation_id')
            if irrigation_id:
                try:
                    irrigation = WaterIrrigationRequest.objects.get(pk=irrigation_id)
                    irrigation.status = 'approved'
                    irrigation.save()
                    logger.info(f"Irrigation request approved - ID: {irrigation_id}")
                except WaterIrrigationRequest.DoesNotExist:
                    logger.error(f"Irrigation request not found - ID: {irrigation_id}")

        elif payment_type == 'appointment':
            appointment_id = metadata.get('appointment_id')
            if appointment_id:
                try:
                    appointment = RiceMillAppointment.objects.get(pk=appointment_id)
                    appointment.status = 'approved'
                    appointment.save()
                    logger.info(f"Appointment approved - ID: {appointment_id}")
                except RiceMillAppointment.DoesNotExist:
                    logger.error(f"Appointment not found - ID: {appointment_id}")

    elif event['type'] == 'payment_intent.payment_failed':
        # Handle payment failures
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent.get('id')
        
        if payment_intent_id:
            try:
                payment_record = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment_record.status = 'failed'
                payment_record.save(update_fields=['status'])
                
                logger.info(f"Payment failed - Internal ID: {payment_record.internal_transaction_id}, Stripe Payment Intent: {payment_intent_id}")
                
            except Payment.DoesNotExist:
                logger.warning(f"No payment record found for failed payment_intent_id: {payment_intent_id}")

    elif event['type'] == 'charge.dispute.created' or event['type'] == 'payment_intent.canceled':
        # Handle refunds/disputes/cancellations
        if event['type'] == 'charge.dispute.created':
            charge = event['data']['object']
            charge_id = charge.get('id')
            payment_intent_id = charge.get('payment_intent')
        else:  # payment_intent.canceled
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent.get('id')
            charge_id = None
        
        if payment_intent_id:
            try:
                payment_record = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment_record.status = 'refunded'
                payment_record.save(update_fields=['status'])
                
                logger.info(f"Payment disputed/refunded/canceled - Internal ID: {payment_record.internal_transaction_id}, Stripe Payment Intent: {payment_intent_id}")
                
            except Payment.DoesNotExist:
                logger.warning(f"No payment record found for disputed/canceled payment_intent_id: {payment_intent_id}")

    else:
        logger.info(f"Unhandled webhook event type: {event['type']}")

    return HttpResponse(status=200)


def _record_rental_online_payment(rental, user, session_id, payment_intent_id=None, paid_amount=None):
    """Persist a successful online rental payment while waiting for admin verification."""
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    rental.payment_verified = False  # Admin must verify
    rental.payment_method = 'online'
    rental.payment_date = timezone.now()
    rental.stripe_session_id = session_id
    rental.payment_status = 'pending'  # Pending admin verification
    if paid_amount and paid_amount > 0:
        rental.payment_amount = paid_amount
    rental.save()

    content_type = ContentType.objects.get_for_model(Rental)
    payment_obj, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=rental.id,
        defaults={
            'user': user,
            'payment_type': 'rental',
            'amount': paid_amount if paid_amount and paid_amount > 0 else (rental.payment_amount or 0),
            'currency': 'PHP',
            'status': 'pending',  # Pending admin verification
            'stripe_session_id': session_id,
            'stripe_payment_intent_id': payment_intent_id,
            'paid_at': timezone.now(),
        }
    )

    # Update if already exists
    if not created:
        update_fields = []
        if paid_amount and paid_amount > 0 and payment_obj.amount != paid_amount:
            payment_obj.amount = paid_amount
            update_fields.append('amount')
        if payment_obj.status != 'pending':
            payment_obj.status = 'pending'
            update_fields.append('status')
        if payment_obj.stripe_session_id != session_id:
            payment_obj.stripe_session_id = session_id
            update_fields.append('stripe_session_id')
        if payment_obj.stripe_payment_intent_id != payment_intent_id:
            payment_obj.stripe_payment_intent_id = payment_intent_id
            update_fields.append('stripe_payment_intent_id')
        if payment_obj.paid_at is None:
            payment_obj.paid_at = timezone.now()
            update_fields.append('paid_at')
        if update_fields:
            payment_obj.save(update_fields=update_fields)

    return payment_obj


@login_required
def payment_success(request):
    """Handle successful payment completion."""
    session_id = request.GET.get('session_id')
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')
    transaction_id = request.GET.get('transaction_id')

    if not session_id:
        messages.error(request, 'Invalid payment session.')
        return redirect('dashboard')

    context = {
        'transaction_id': transaction_id,
        'payment_type': payment_type,
        'item_id': item_id,
    }

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        from bufia.models import Payment
        payment = Payment.objects.filter(stripe_session_id=session_id).first()
        if payment:
            context['transaction_id'] = payment.internal_transaction_id

        if session.payment_status == 'paid':
            paid_amount = (Decimal(str(session.get('amount_total', 0))) / Decimal('100')).quantize(Decimal('0.01'))
            if payment_type == 'rental':
                rental = get_object_or_404(Rental, pk=item_id, user=request.user)
                payment_obj = _record_rental_online_payment(
                    rental,
                    request.user,
                    session_id,
                    payment_intent_id=session.get('payment_intent'),
                    paid_amount=paid_amount,
                )

                context['transaction_id'] = payment_obj.internal_transaction_id
                context['rental'] = rental
                context['machine_name'] = rental.machine.name
                context['amount'] = rental.payment_amount if rental.payment_amount else None

                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='rental_payment_completed',
                    message=f'Online payment recorded for {rental.machine.name}. Waiting for admin verification.',
                    related_object_id=rental.id
                )

                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='rental_payment_received',
                        message=(
                            f'Online payment received from {request.user.get_full_name()} '
                            f'for {rental.machine.name}. Please verify and complete the rental.'
                        ),
                        related_object_id=rental.id
                    )

                messages.success(request, f'Online payment recorded for {rental.machine.name}. Waiting for admin verification.')
                return redirect('machines:rental_detail', pk=rental.id)

            elif payment_type == 'irrigation':
                irrigation = get_object_or_404(WaterIrrigationRequest, pk=item_id, farmer=request.user)
                irrigation.status = 'approved'
                irrigation.save()

                context['irrigation'] = irrigation
                context['amount'] = f'${irrigation.area_size * irrigation.duration_hours * 10:.2f}'

                messages.success(request, 'Payment successful! Your irrigation request has been approved.')
                return render(request, 'machines/payment_success.html', context)

            elif payment_type == 'appointment':
                appointment = get_object_or_404(RiceMillAppointment, pk=item_id, user=request.user)
                appointment.status = 'approved'
                appointment.save()

                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                content_type = ContentType.objects.get_for_model(RiceMillAppointment)
                payment_obj = Payment.objects.filter(
                    content_type=content_type,
                    object_id=appointment.id
                ).first()

                if payment_obj:
                    payment_obj.status = 'completed'
                    payment_obj.stripe_session_id = session_id
                    payment_obj.stripe_payment_intent_id = session.get('payment_intent')
                    payment_obj.paid_at = timezone.now()
                    payment_obj.save()
                    context['transaction_id'] = payment_obj.internal_transaction_id

                context['appointment'] = appointment
                amount_php = float(appointment.rice_quantity) * 150
                context['amount'] = f'â‚±{amount_php:,.2f}'

                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='appointment_payment_completed',
                    message=f'Payment successful! Your rice mill appointment for {appointment.appointment_date} has been approved.',
                    related_object_id=appointment.id
                )

                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='appointment_approved',
                        message=f'Rice mill appointment approved for {request.user.get_full_name()} on {appointment.appointment_date}.',
                        related_object_id=appointment.id
                    )

                messages.success(request, 'Payment successful! Your rice mill appointment has been approved.')
                return render(request, 'machines/payment_success.html', context)

            elif payment_type == 'membership':
                from users.models import MembershipApplication
                membership = get_object_or_404(MembershipApplication, pk=item_id, user=request.user)
                membership.payment_status = 'paid'
                membership.payment_method = 'online'
                membership.payment_date = timezone.now()
                membership.save()

                transaction_id = f'BUFIA-MEM-{membership.id:05d}'

                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='membership',
                    message=f'Payment successful! Your membership fee has been paid (Transaction ID: {transaction_id}). Your application is now pending admin approval.',
                    related_object_id=membership.pk
                )

                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='membership',
                        message=f'Membership payment received from {request.user.get_full_name()} (Transaction ID: {transaction_id}). Application is ready for review.',
                        related_object_id=membership.pk
                    )

                try:
                    hazel = User.objects.filter(
                        first_name__icontains='hazel',
                        last_name__icontains='osorio'
                    ).first()
                    if hazel and hazel not in admins:
                        UserNotification.objects.create(
                            user=hazel,
                            notification_type='membership',
                            message=f'Membership payment received from {request.user.get_full_name()} (Transaction ID: {transaction_id}). Application is ready for review.',
                            related_object_id=membership.pk
                        )
                except Exception:
                    pass

                messages.success(request, f'âœ… Payment successful! Your â‚±500 membership fee has been paid. Transaction ID: {transaction_id}. Your application is now pending admin approval.')
                return redirect('dashboard')
        else:
            messages.warning(request, 'Payment is being processed. Please check back later.')

    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')

    return redirect('dashboard')





@login_required
def create_membership_payment(request, membership_id):
    """Create a Stripe Checkout session for membership fee payment"""
    from users.models import MembershipApplication
    
    membership = get_object_or_404(MembershipApplication, pk=membership_id, user=request.user)
    
    # Check if Stripe is available
    if stripe is None:
        messages.error(request, 'Payment system is not configured. Please contact administrator.')
        return redirect('profile')
    
    # Check if membership is already approved or paid
    if membership.is_approved:
        messages.info(request, 'Your membership has already been approved.')
        return redirect('profile')
    
    if membership.payment_status == 'paid':
        messages.info(request, 'Your membership fee has already been paid.')
        return redirect('profile')
    
    try:
        # Membership fee: ₱500 fixed
        amount = 50000  # ₱500.00 in centavos (500 * 100)
        
        # Create Payment record with internal transaction ID before Stripe checkout
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        
        content_type = ContentType.objects.get_for_model(membership)
        payment_obj, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=membership.id,
            defaults={
                'user': request.user,
                'payment_type': 'membership',
                'amount': 500.00,
                'currency': 'PHP',
                'status': 'pending',
            }
        )
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=membership&id={membership_id}&transaction_id={payment_obj.internal_transaction_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=membership&id={membership_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'php',  # Changed to PHP
                    'unit_amount': amount,  # ₱500 in centavos
                    'product_data': {
                        'name': 'BUFIA Membership Fee',
                        'description': f'Membership registration fee for {request.user.get_full_name()}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.user.email,
            metadata={
                'membership_id': membership_id,
                'user_id': request.user.id,
                'type': 'membership',
                'internal_transaction_id': payment_obj.internal_transaction_id,
            }
        )
        
        # Store Stripe session_id in Payment record immediately after creation
        payment_obj.stripe_session_id = checkout_session.id
        payment_obj.save(update_fields=['stripe_session_id'])
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f'Error creating payment session: {str(e)}')
        return redirect('profile')


# Admin Payment Management Views
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from bufia.models import Payment
from django.db.models import Q
import csv


@staff_member_required
def admin_payment_list(request):
    """Admin view to list all payments with transaction IDs"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_type_filter = request.GET.get('payment_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    payments = Payment.objects.select_related('user', 'content_type').order_by('-created_at')
    
    # Apply search filter (transaction ID, user name, email)
    if search_query:
        payments = payments.filter(
            Q(internal_transaction_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    # Apply payment type filter
    if payment_type_filter:
        payments = payments.filter(payment_type=payment_type_filter)
    
    # Apply date range filter
    if date_from:
        payments = payments.filter(created_at__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__lte=date_to)
    
    # Pagination
    paginator = Paginator(payments, 25)  # 25 payments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get related objects for each payment
    for payment in page_obj:
        payment.related_object = payment.content_object
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'payment_type_filter': payment_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Payment.PAYMENT_STATUS_CHOICES,
        'payment_type_choices': Payment.PAYMENT_TYPE_CHOICES,
        'total_count': paginator.count,
    }
    
    return render(request, 'payments/admin_payment_list.html', context)


@staff_member_required
def admin_payment_detail(request, payment_id):
    """Admin view to see detailed payment information"""
    payment = get_object_or_404(Payment, pk=payment_id)
    related_object = payment.content_object
    
    context = {
        'payment': payment,
        'related_object': related_object,
    }
    
    return render(request, 'payments/admin_payment_detail.html', context)


@staff_member_required
def export_payments(request):
    """Export payments to CSV"""
    # Get filter parameters (same as list view)
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_type_filter = request.GET.get('payment_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    payments = Payment.objects.select_related('user').order_by('-created_at')
    
    # Apply same filters as list view
    if search_query:
        payments = payments.filter(
            Q(internal_transaction_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    if payment_type_filter:
        payments = payments.filter(payment_type=payment_type_filter)
    
    if date_from:
        payments = payments.filter(created_at__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID',
        'Date',
        'Member Name',
        'Member Email',
        'Payment Type',
        'Amount',
        'Currency',
        'Status',
        'Payment Method',
        'Stripe Session ID',
    ])
    
    for payment in payments:
        writer.writerow([
            payment.internal_transaction_id or 'N/A',
            payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            payment.user.get_full_name(),
            payment.user.email,
            payment.get_payment_type_display(),
            payment.amount,
            payment.currency,
            payment.get_status_display(),
            'Stripe' if payment.stripe_session_id else 'N/A',
            payment.stripe_session_id or 'N/A',
        ])
    
    return response
