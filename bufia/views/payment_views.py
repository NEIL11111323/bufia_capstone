from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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
    
    # Check if Stripe is available
    if stripe is None:
        messages.error(request, 'Payment system is not configured. Please contact administrator.')
        return redirect('machines:rental_detail', pk=rental_id)
    
    # Check if rental is already paid or approved
    if rental.status == 'approved':
        messages.info(request, 'This rental has already been approved.')
        return redirect('machines:rental_detail', pk=rental_id)
    
    try:
        # Calculate amount based on rental details
        duration_days = rental.get_duration_days()
        
        # Try to extract numeric value from current_price (which is now a CharField)
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
        
        amount = int(price_value * duration_days * 100)  # Convert to cents
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=rental&id={rental_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=rental&id={rental_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': amount,
                    'product_data': {
                        'name': f'Machine Rental: {rental.machine.name}',
                        'description': f'Rental from {rental.start_date} to {rental.end_date} ({duration_days} days)',
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
                'type': 'rental'
            }
        )
        
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
        amount = int(irrigation_request.area_size * irrigation_request.duration_hours * 10 * 100)  # Convert to cents
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=irrigation&id={irrigation_id}'
        
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
                'type': 'irrigation'
            }
        )
        
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
        # Example: $0.15 per kg
        amount = int(float(appointment.rice_quantity) * 0.15 * 100)  # Convert to cents
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=appointment&id={appointment_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=appointment&id={appointment_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': amount,
                    'product_data': {
                        'name': f'Rice Mill Service: {appointment.machine.name}',
                        'description': f'{appointment.rice_quantity} kg on {appointment.appointment_date} ({appointment.get_time_slot_display()})',
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
                'type': 'appointment'
            }
        )
        
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
            # Update the corresponding record based on type
            if payment_type == 'rental':
                rental = get_object_or_404(Rental, pk=item_id, user=request.user)
                # Mark payment as verified but keep status as pending for admin approval
                rental.payment_verified = True
                rental.payment_method = 'online'
                rental.payment_date = timezone.now()
                rental.stripe_session_id = session_id
                rental.save()
                
                context['rental'] = rental
                context['machine_name'] = rental.machine.name
                
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
                return render(request, 'machines/payment_success.html', context)
                
            elif payment_type == 'irrigation':
                irrigation = get_object_or_404(WaterIrrigationRequest, pk=item_id, farmer=request.user)
                irrigation.status = 'approved'  # Auto-approve after payment
                irrigation.save()
                messages.success(request, f'Payment successful! Your irrigation request has been approved.')
                return redirect('irrigation:irrigation_request_detail', pk=item_id)
                
            elif payment_type == 'appointment':
                appointment = get_object_or_404(RiceMillAppointment, pk=item_id, user=request.user)
                appointment.status = 'approved'  # Auto-approve after payment
                appointment.save()
                messages.success(request, f'Payment successful! Your rice mill appointment has been approved.')
                return redirect('machines:ricemill_appointment_detail', pk=item_id)
                
            elif payment_type == 'membership':
                from users.models import MembershipApplication
                membership = get_object_or_404(MembershipApplication, pk=item_id, user=request.user)
                membership.payment_status = 'paid'
                membership.payment_method = 'online'
                membership.save()
                
                # Notify user about successful payment
                from notifications.models import UserNotification
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='membership',
                    message='Payment successful! Your membership fee has been paid. Your application is now pending admin approval.',
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
                        message=f'Membership payment received from {request.user.get_full_name()}. Application is ready for review.',
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
                            message=f'Membership payment received from {request.user.get_full_name()}. Application is ready for review.',
                            related_object_id=membership.pk
                        )
                except Exception:
                    pass  # Silently fail if user not found
                
                messages.success(request, 'Payment successful! Your membership fee has been paid. Your application is now pending admin approval.')
                return redirect('profile')
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
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get metadata
        metadata = session.get('metadata', {})
        payment_type = metadata.get('type')
        
        # Update status based on type
        if payment_type == 'rental':
            rental_id = metadata.get('rental_id')
            if rental_id:
                try:
                    from django.utils import timezone
                    rental = Rental.objects.get(pk=rental_id)
                    # Mark payment as verified but keep pending status for admin approval
                    rental.payment_verified = True
                    rental.payment_method = 'online'
                    rental.payment_date = timezone.now()
                    rental.stripe_session_id = session.get('id')
                    rental.save()
                except Rental.DoesNotExist:
                    pass
                    
        elif payment_type == 'irrigation':
            irrigation_id = metadata.get('irrigation_id')
            if irrigation_id:
                try:
                    irrigation = WaterIrrigationRequest.objects.get(pk=irrigation_id)
                    irrigation.status = 'approved'
                    irrigation.save()
                except WaterIrrigationRequest.DoesNotExist:
                    pass
                    
        elif payment_type == 'appointment':
            appointment_id = metadata.get('appointment_id')
            if appointment_id:
                try:
                    appointment = RiceMillAppointment.objects.get(pk=appointment_id)
                    appointment.status = 'approved'
                    appointment.save()
                except RiceMillAppointment.DoesNotExist:
                    pass
    
    return HttpResponse(status=200)


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
    
    try:
        # Membership fee: ₱500 = $10 USD (approximate conversion)
        amount = 1000  # $10.00 in cents
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=membership&id={membership_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=membership&id={membership_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': amount,
                    'product_data': {
                        'name': 'BUFIA Membership Fee',
                        'description': f'Membership application for {request.user.get_full_name()}',
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
                'type': 'membership'
            }
        )
        
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
