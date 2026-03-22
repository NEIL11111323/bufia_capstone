from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Machine, Rental, Maintenance, PriceHistory, MachineImage, RiceMillAppointment, DryerRental
from .forms import (MachineForm, MachineImageForm, MachineImageFormSet, RentalForm, 
                   MaintenanceForm, PriceHistoryForm, RiceMillAppointmentForm, DryerRentalForm, AdminRentalForm)
import json
from django.utils.safestring import mark_safe
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import HttpResponse, HttpResponseForbidden, Http404, JsonResponse, HttpResponseRedirect
from django.utils.crypto import get_random_string
import os
from django.conf import settings
from django.utils.text import slugify
from notifications.models import UserNotification
from django.contrib.auth import get_user_model
from users.decorators import verified_member_required
from datetime import datetime
from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch
from django.contrib.auth import get_user_model

# Simple notification function (temporary)
def create_notification(user, title, message, category, reference_object=None):
    """Create a user notification - temporary implementation until proper notification system is integrated"""
    # Log the notification details for debugging
    print(f"NOTIFICATION - User: {user}, Title: {title}, Message: {message}")
    # In a real implementation, this would save to a notifications model
    # For now, we'll just use Django messages
    return True


RICE_MILL_LOCKED_STATUSES = ['approved', 'paid', 'confirmed', 'ongoing']
DRYER_LOCKED_STATUSES = ['approved', 'paid', 'confirmed', 'ongoing']


def _machine_rental_queryset():
    return Machine.objects.exclude(machine_type__in=['rice_mill', 'flatbed_dryer'])


def _get_appointment_payment(appointment):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=appointment.id
    ).first()


def _get_dryer_payment(dryer_rental):
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(DryerRental)
    return Payment.objects.filter(
        content_type=content_type,
        object_id=dryer_rental.id
    ).first()

@login_required
def machine_list(request):
    machines = _machine_rental_queryset()
    
    # Add pagination
    from django.core.paginator import Paginator
    
    paginator = Paginator(machines, 12)  # 12 machines per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_machines = machines.count()
    available_machines = machines.filter(status='available').count()
    in_use_machines = machines.filter(status='rented').count()
    machine_types = machines.values('machine_type').distinct().count()
    
    # Check user permissions
    context = {
        'machines': page_obj,
        'page_obj': page_obj,
        'total_machines': total_machines,
        'available_machines': available_machines,
        'in_use_machines': in_use_machines,
        'machine_types': machine_types,
    }
    return render(request, 'machines/machine_list.html', context)

@login_required
def machine_detail(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    rentals = machine.rentals.all().order_by('-start_date')
    maintenance_records = machine.maintenance_records.all().order_by('-start_date')
    price_history = machine.price_history.all().order_by('-start_date')
    images = machine.images.all()
    
    # Calculate rental statistics
    approved_rentals = rentals.filter(status='approved').count()
    pending_rentals = rentals.filter(status='pending').count()
    rejected_rentals = rentals.filter(status='rejected').count()
    total_rentals = rentals.count()
    
    # Get similar machines based on machine type
    similar_machines = Machine.objects.filter(
        machine_type=machine.machine_type
    ).exclude(
        pk=machine.pk
    ).order_by('-created_at')[:5]
    
    # Create calendar events data
    calendar_events = []
    
    # Add rental events
    for rental in rentals:
        color = '#dc3545' if rental.status == 'approved' else '#ffc107'
        calendar_events.append({
            'title': 'Rented',
            'start': rental.start_date.strftime('%Y-%m-%d'),
            'end': rental.end_date.strftime('%Y-%m-%d'),
            'color': color
        })
    
    # Add maintenance events
    for record in maintenance_records:
        if record.end_date:
            end_date = record.end_date.strftime('%Y-%m-%d')
        else:
            end_date = None
            
        calendar_events.append({
            'title': 'Maintenance',
            'start': record.start_date.strftime('%Y-%m-%d'),
            'end': end_date,
            'color': '#fd7e14'
        })
    
    context = {
        'machine': machine,
        'rentals': rentals,
        'maintenance_records': maintenance_records,
        'price_history': price_history,
        'images': images,
        'similar_machines': similar_machines,
        'calendar_events_json': mark_safe(json.dumps(calendar_events)),
        'approved_rentals': approved_rentals,
        'pending_rentals': pending_rentals,
        'rejected_rentals': rejected_rentals,
        'total_rentals': total_rentals,
    }
    return render(request, 'machines/machine_detail.html', context)

@login_required
def machine_create(request):
    if request.method == 'POST':
        form = MachineForm(request.POST)
        formset = MachineImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            machine = form.save()
            
            # Process the formset
            image_instances = formset.save(commit=False)
            for image in image_instances:
                image.machine = machine
                image.save()
            
            # Handle deleted images
            for obj in formset.deleted_objects:
                obj.delete()
                
            # Ensure there's at least one primary image if images exist
            images = machine.images.all()
            if images.exists() and not images.filter(is_primary=True).exists():
                first_image = images.first()
                first_image.is_primary = True
                first_image.save()
                
            messages.success(request, 'Machine created successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MachineForm()
        formset = MachineImageFormSet()
    
    return render(request, 'machines/machine_form.html', {
        'form': form, 
        'formset': formset,
        'action': 'Create'
    })

@login_required
def machine_update(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        form = MachineForm(request.POST, instance=machine)
        formset = MachineImageFormSet(request.POST, request.FILES, instance=machine)
        
        if form.is_valid() and formset.is_valid():
            machine = form.save()
            
            # Process the formset
            image_instances = formset.save(commit=False)
            for image in image_instances:
                image.machine = machine
                image.save()
            
            # Handle deleted images
            for obj in formset.deleted_objects:
                obj.delete()
            
            # Ensure there's always a primary image if images exist
            images = machine.images.all()
            if images.exists() and not images.filter(is_primary=True).exists():
                first_image = images.first()
                first_image.is_primary = True
                first_image.save()
                
            messages.success(request, 'Machine updated successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MachineForm(instance=machine)
        formset = MachineImageFormSet(instance=machine)
    
    return render(request, 'machines/machine_form.html', {
        'form': form, 
        'formset': formset,
        'action': 'Update'
    })

# Old function-based view - replaced by MachineDeleteView class-based view
# @login_required
# def machine_delete(request, pk):
#     machine = get_object_or_404(Machine, pk=pk)
#     if request.method == 'POST':
#         machine.delete()
#         messages.success(request, 'Machine deleted successfully.')
#         return redirect('machines:machine_list')
#     
#     return render(request, 'machines/machine_confirm_delete.html', {'machine': machine})

@login_required
@verified_member_required
def rental_create(request, machine_pk=None):
    if machine_pk:
        selected_machine = get_object_or_404(Machine, pk=machine_pk)
        if selected_machine.machine_type == 'flatbed_dryer':
            messages.info(request, 'Flatbed dryer uses a separate dryer rental process.')
            return redirect('machines:dryer_rental_create_for_machine', machine_id=selected_machine.pk)
        if selected_machine.machine_type == 'rice_mill':
            messages.info(request, 'Rice mill uses a separate milling appointment process.')
            return redirect('machines:ricemill_appointment_create_for_machine', machine_id=selected_machine.pk)

    if request.method == 'POST':
        form = RentalForm(request.POST, user=request.user)
        if form.is_valid():
            rental = form.save(commit=False)
            rental.user = request.user
            
            # Calculate payment amount from admin-configured machine pricing
            rental.payment_amount = rental.calculate_payment_amount()
            
            # Capture requester name from the form (not part of model fields)
            requester_name = request.POST.get('requester_name') or request.user.get_full_name() or request.user.username
            if requester_name:
                if rental.purpose:
                    rental.purpose = f"Requester: {requester_name}\n\n{rental.purpose}"
                else:
                    rental.purpose = f"Requester: {requester_name}"
            
            # Save the rental
            rental.save()
            
            if rental.payment_type == 'cash':
                # Create the linked payment record, but approval still comes first.
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                
                content_type = ContentType.objects.get_for_model(rental)
                Payment.objects.get_or_create(
                    content_type=content_type,
                    object_id=rental.id,
                    defaults={
                        'user': request.user,
                        'payment_type': 'rental',
                        'amount': rental.payment_amount or 0,
                        'currency': 'PHP',
                        'status': 'pending',
                    }
                )
                messages.success(
                    request,
                    'Rental request submitted successfully. Wait for admin approval before completing payment.'
                )
                return redirect('machines:rental_confirmation', pk=rental.pk)

            messages.success(
                request,
                'Rental request submitted. IN-KIND settlement will be recorded after harvest and rice delivery.'
            )
            return redirect('machines:rental_confirmation', pk=rental.pk)
        else:
            # Detect overlap/conflict and notify the requester
            error_text = str(form.errors) + " " + " ".join(e for e in form.non_field_errors())
            if 'already rented' in error_text.lower():
                messages.error(request, 'This machine is already rented for the selected dates. Please rent this on another day.')
                try:
                    # Include machine name if available
                    machine_name = None
                    try:
                        mid = request.POST.get('machine') or form.initial.get('machine')
                        if mid:
                            m_obj = Machine.objects.filter(pk=mid).first()
                            machine_name = m_obj.name if m_obj else None
                    except Exception:
                        pass
                    # Try to get dates for message context
                    start_date = request.POST.get('start_date')
                    end_date = request.POST.get('end_date')
                    msg = 'This machine is already rented for the selected dates. Please rent this on another day.'
                    if machine_name:
                        if start_date and end_date:
                            msg = f'{machine_name} is already rented from {start_date} to {end_date}. Please rent this on another day.'
                        else:
                            msg = f'{machine_name} is already rented for the selected dates. Please rent this on another day.'
                    UserNotification.objects.create(
                        user=request.user,
                        notification_type='rental_conflict',
                        message=msg
                    )

                    # Broadcast to other verified members (prefer same sector)
                    try:
                        User = get_user_model()
                        # Determine requester's sector if available
                        requester_sector = None
                        try:
                            requester_sector = getattr(getattr(request.user, 'membership_application', None), 'assigned_sector', None)
                        except Exception:
                            requester_sector = None

                        recipients = None
                        if requester_sector:
                            recipients = User.objects.filter(is_verified=True, membership_application__assigned_sector=requester_sector)
                        else:
                            recipients = User.objects.filter(is_verified=True)
                        # Exclude the requester (already notified)
                        recipients = recipients.exclude(pk=request.user.pk)

                        broadcast_msg = msg
                        # Create notifications in bulk-like loop
                        for member in recipients:
                            UserNotification.objects.create(
                                user=member,
                                notification_type='rental_conflict_broadcast',
                                message=broadcast_msg
                            )
                    except Exception as e:
                        print(f'Failed to broadcast rental conflict notification: {e}')
                except Exception as e:
                    print(f'Failed to create rental conflict notification: {e}')
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = RentalForm(initial=initial, user=request.user)

    # Provide list of all machines with status for Services and Pricing section
    available_machines = _machine_rental_queryset().filter(status='available').order_by('name')
    all_machines = _machine_rental_queryset().order_by('name')
    
    # Get machine object if machine_pk is provided
    machine = None
    if machine_pk:
        try:
            machine = _machine_rental_queryset().get(pk=machine_pk)
        except Machine.DoesNotExist:
            pass
    
    return render(request, 'machines/rental_form.html', {
        'form': form,
        'action': 'Create',
        'available_machines': available_machines,
        'all_machines': all_machines,
        'machine': machine,
    })

@login_required
def rental_update(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    if request.method == 'POST':
        form = RentalForm(request.POST, instance=rental, user=request.user)
        if form.is_valid():
            rental = form.save()
            messages.success(request, 'Rental updated successfully.')
            return redirect('machines:machine_detail', pk=rental.machine.pk)
    else:
        form = RentalForm(instance=rental, user=request.user)

    available_machines = _machine_rental_queryset().filter(status='available').order_by('name')
    all_machines = _machine_rental_queryset().order_by('name')
    return render(request, 'machines/rental_form.html', {
        'form': form,
        'action': 'Update',
        'available_machines': available_machines,
        'all_machines': all_machines,
        'machine': rental.machine,  # Pass the machine object for the template
    })

@login_required
def rental_delete(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    if request.method == 'POST':
        rental.delete()
        messages.success(request, 'Rental deleted successfully.')
        return redirect('machines:machine_detail', pk=rental.machine.pk)
    
    return render(request, 'machines/rental_confirm_delete.html', {'rental': rental})

@login_required
def rental_slip(request, pk):
    """View for displaying printable rental slip after submission"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view the slip
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental slip.")
        return redirect('machines:rental_list')
    
    context = {
        'rental': rental,
    }
    
    return render(request, 'machines/rental_slip.html', context)

@login_required
def maintenance_create(request, machine_pk=None):
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.created_by = request.user
            
            # If the machine being maintained is currently available, update its status
            if maintenance.machine.status == 'available':
                maintenance.machine.status = 'maintenance'
                maintenance.machine.save()
                
            maintenance.save()
            messages.success(request, 'Maintenance record created successfully.')
            
            # Redirect to the maintenance detail page if it exists, otherwise to the machine detail
            try:
                return redirect('machines:maintenance_detail', pk=maintenance.pk)
            except NoReverseMatch:
                return redirect('machines:machine_detail', pk=maintenance.machine.pk)
    else:
        initial = {}
        if machine_pk:
            initial['machine'] = machine_pk
        form = MaintenanceForm(initial=initial)
    
    return render(request, 'machines/maintenance_form.html', {'form': form, 'action': 'Create'})

@login_required
def maintenance_update(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            maintenance = form.save()
            
            # Check if status changed to completed and update machine status if needed
            if maintenance.status == 'completed' and not maintenance.actual_completion_date:
                maintenance.actual_completion_date = timezone.now()
                maintenance.save()
                
                # Check if there are other active maintenance records for this machine
                other_active_records = Maintenance.objects.filter(
                    machine=maintenance.machine,
                    status__in=['scheduled', 'in_progress']
                ).exclude(pk=maintenance.pk).exists()
                
                # If no other active records and machine is in maintenance status, set it back to available
                if not other_active_records and maintenance.machine.status == 'maintenance':
                    maintenance.machine.status = 'available'
                    maintenance.machine.save()
            
            messages.success(request, 'Maintenance record updated successfully.')
            
            # Redirect to the maintenance detail page if it exists, otherwise to the machine detail
            try:
                return redirect('machines:maintenance_detail', pk=maintenance.pk)
            except NoReverseMatch:
                return redirect('machines:machine_detail', pk=maintenance.machine.pk)
    else:
        form = MaintenanceForm(instance=maintenance)
    
    return render(request, 'machines/maintenance_form.html', {'form': form, 'maintenance': maintenance, 'action': 'Update'})

@login_required
def maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)
    if request.method == 'POST':
        maintenance.delete()
        messages.success(request, 'Maintenance record deleted successfully.')
        return redirect('machines:machine_detail', pk=maintenance.machine.pk)
    
    return render(request, 'machines/maintenance_confirm_delete.html', {'maintenance': maintenance})

@login_required
def price_history_create(request, machine_pk):
    machine = get_object_or_404(Machine, pk=machine_pk)
    if request.method == 'POST':
        form = PriceHistoryForm(request.POST)
        if form.is_valid():
            price_history = form.save(commit=False)
            price_history.machine = machine
            price_history.created_by = request.user
            price_history.save()
            
            # Update machine's current price
            machine.current_price = price_history.price
            machine.save()
            
            messages.success(request, 'Price history record created successfully.')
            return redirect('machines:machine_detail', pk=machine.pk)
    else:
        form = PriceHistoryForm()
    
    return render(request, 'machines/price_history_form.html', {'form': form, 'machine': machine})

@login_required
def rental_list(request):
    """User's rental history organized by status - Redirects admins to admin dashboard"""
    from datetime import date
    from django.shortcuts import redirect
    
    # If user is admin/staff, redirect to admin dashboard
    if request.user.is_staff or request.user.is_superuser:
        return redirect('machines:admin_rental_dashboard')
    
    today = date.today()
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()
    valid_status_filters = {'all', 'pending', 'approved', 'in_progress', 'past'}
    if status_filter not in valid_status_filters:
        status_filter = 'all'

    user_rentals = Rental.objects.filter(user=request.user).select_related('machine')
    
    # Add payment information to context for each rental efficiently
    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment
    
    rental_ct = ContentType.objects.get_for_model(Rental)
    rental_ids = list(user_rentals.values_list('id', flat=True))
    
    # Prefetch payments for all rentals to avoid N+1 queries
    payments_dict = {}
    if rental_ids:
        payments = Payment.objects.filter(
            content_type=rental_ct,
            object_id__in=rental_ids
        ).select_related('user')
        
        for payment in payments:
            payments_dict[payment.object_id] = payment

    if search_query:
        user_rentals = user_rentals.filter(
            Q(machine__name__icontains=search_query) |
            Q(machine__machine_type__icontains=search_query) |
            Q(purpose__icontains=search_query) |
            Q(field_location__icontains=search_query)
        )
    
    # Categorize rentals by workflow state instead of calendar buckets.
    pending_rentals = user_rentals.filter(status='pending').order_by('-created_at')

    approved_rentals = user_rentals.filter(
        status='approved',
        workflow_state='approved'
    ).order_by('start_date', 'created_at')

    in_progress_rentals = user_rentals.filter(
        workflow_state='in_progress'
    ).order_by('start_date', 'created_at')

    history_rentals = user_rentals.filter(
        Q(status='completed') |
        Q(workflow_state='completed') |
        Q(status='approved', end_date__lt=today) |
        Q(status='rejected') |
        Q(status='cancelled')
    ).order_by('-updated_at', '-created_at')

    # Apply status filter
    if status_filter == 'pending':
        approved_rentals = approved_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'approved':
        pending_rentals = pending_rentals.none()
        in_progress_rentals = in_progress_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'in_progress':
        pending_rentals = pending_rentals.none()
        approved_rentals = approved_rentals.none()
        history_rentals = history_rentals.none()
    elif status_filter == 'past':
        pending_rentals = pending_rentals.none()
        approved_rentals = approved_rentals.none()
        in_progress_rentals = in_progress_rentals.none()

    # Add pagination for history rentals (largest list)
    from django.core.paginator import Paginator
    
    history_paginator = Paginator(history_rentals, 10)  # 10 items per page
    history_page_number = request.GET.get('history_page')
    history_page_obj = history_paginator.get_page(history_page_number)

    context = {
        'pending_rentals': pending_rentals,
        'approved_rentals': approved_rentals,
        'in_progress_rentals': in_progress_rentals,
        'history_rentals': history_page_obj,
        'history_page_obj': history_page_obj,
        'pending_count': pending_rentals.count(),
        'approved_count': approved_rentals.count(),
        'in_progress_count': in_progress_rentals.count(),
        'history_count': history_rentals.count(),
        'status_filter': status_filter,
        'search_query': search_query,
        'payments_dict': payments_dict,  # Add payments for efficient template access
    }
    
    return render(request, 'machines/rental_list_organized.html', context)

@login_required
def rental_detail(request, pk):
    """View details of a specific rental"""
    rental = get_object_or_404(Rental, pk=pk, user=request.user)
    return render(request, 'machines/rental_detail.html', {'rental': rental})

@login_required
def rental_confirmation(request, pk):
    """View rental confirmation after submission"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental confirmation.")
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_confirmation.html', {'rental': rental})


def rental_confirmation_print(request, pk):
    """Render a printable payment form for face-to-face payments"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Security check - only allow the rental owner or staff to view
    if rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this rental.")
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_confirmation_print.html', {'rental': rental})

@login_required
def payment_success(request):
    """View payment success page after Stripe payment"""
    # Get the most recent rental for this user
    rental = Rental.objects.filter(user=request.user).order_by('-created_at').first()
    
    # Mark payment as pending verification if rental exists
    if rental and not rental.payment_verified:
        messages.success(
            request,
            'Payment received. Admin verification is still required before the rental is completed.'
        )
    
    return render(request, 'machines/payment_success.html', {'rental': rental})

@login_required
def upload_payment_proof(request, rental_id):
    """Handle payment proof upload with validation"""
    rental = get_object_or_404(Rental, pk=rental_id)
    
    # Security check - only rental owner can upload proof
    if rental.user != request.user:
        messages.error(request, "You don't have permission to upload proof for this rental.")
        return redirect('machines:rental_list')
    
    if request.method == 'POST':
        payment_proof = request.FILES.get('payment_proof')
        
        if payment_proof:
            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            if payment_proof.size > max_size:
                messages.error(request, 'File size too large. Maximum size is 5MB.')
                return redirect('machines:rental_confirmation', pk=rental_id)
            
            # Validate file type - only JPG, JPEG, PNG
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            file_extension = payment_proof.name.lower().split('.')[-1]
            allowed_extensions = ['jpg', 'jpeg', 'png']
            
            if payment_proof.content_type not in allowed_types or file_extension not in allowed_extensions:
                messages.error(request, 'Invalid file type. Please upload JPG, JPEG, or PNG images only.')
                return redirect('machines:rental_confirmation', pk=rental_id)
            
            # Rename file automatically for security and organization
            # Format: proof_{rental_id}_{timestamp}.{extension}
            from django.utils.text import slugify
            import time
            timestamp = int(time.time())
            new_filename = f"proof_{rental.id}_{timestamp}.{file_extension}"
            
            # Update the file name
            payment_proof.name = new_filename
            
            # Save the payment proof
            rental.payment_slip = payment_proof
            rental.payment_date = timezone.now()
            rental.save()
            
            messages.success(request, '✅ Payment proof uploaded successfully! Admin will verify it shortly.')
            
            # Create notification for admin
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='payment_proof_uploaded',
                        message=f'{rental.user.get_full_name()} uploaded payment proof for {rental.machine.name} rental.'
                    )
            except Exception as e:
                print(f'Failed to create admin notification: {e}')
        else:
            messages.error(request, 'Please select a file to upload.')
    
    return redirect('machines:rental_confirmation', pk=rental_id)

@login_required
def approve_rental(request, pk):
    """View to approve a rental request"""
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser or request.user.has_perm('machines.can_approve_rentals')):
        messages.error(request, "You don't have permission to approve rentals.")
        return redirect('machines:rental_list')
    
    rental = get_object_or_404(Rental, pk=pk)
    
    if request.method == 'POST':
        rental.status = 'approved'
        rental.save()
        
        # Update machine status if needed
        if rental.machine.status == 'available':
            rental.machine.status = 'rented'
            rental.machine.save()
        
        messages.success(request, f'✅ Rental request for {rental.machine.name} by {rental.user.get_full_name()} has been approved!')
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_approve.html', {'rental': rental})

@login_required
def rental_reject(request, pk):
    """View to reject a rental request"""
    rental = get_object_or_404(Rental, pk=pk)
    
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser or request.user.has_perm('machines.can_approve_rentals')):
        messages.error(request, "You don't have permission to reject rentals.")
        return redirect('machines:rental_list')
    
    if request.method == 'POST':
        rental.status = 'rejected'
        rental.save()
        
        # Update machine status if necessary
        active_rentals = Rental.objects.filter(
            machine=rental.machine,
            status='approved',
            end_date__gte=timezone.now().date()
        ).exclude(pk=rental.pk)
        
        if not active_rentals.exists() and rental.machine.status == 'rented':
            rental.machine.status = 'available'
            rental.machine.save()
        
        messages.success(request, f'Rental request for {rental.machine.name} has been rejected.')
        return redirect('machines:rental_list')
    
    return render(request, 'machines/rental_confirm_reject.html', {'rental': rental})

# Machine Views

class MachineListView(LoginRequiredMixin, ListView):
    model = Machine
    template_name = 'machines/machine_list.html'
    context_object_name = 'machines'
    
    def get_queryset(self):
        """Return all machines excluding rice mills, filtered by search query or type if provided."""
        # Exclude rice mills from the machines list
        queryset = _machine_rental_queryset().prefetch_related('images')
        
        # Filter by search query if provided
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Filter by machine type if provided
        machine_type = self.request.GET.get('type')
        if machine_type:
            queryset = queryset.filter(machine_type=machine_type)
            
        # Filter by availability if provided
        availability = self.request.GET.get('availability')
        if availability:
            queryset = queryset.filter(status=availability)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = _machine_rental_queryset()

        # Add permission checks to context
        context['can_create'] = self.request.user.has_perm('machines.add_machine')
        context['can_edit'] = self.request.user.has_perm('machines.change_machine')
        context['can_delete'] = self.request.user.has_perm('machines.delete_machine')
        context['can_rent'] = self.request.user.has_perm('machines.can_rent_machine')
        context['total_machines'] = base_queryset.count()
        context['available_machines'] = base_queryset.filter(status='available').count()
        context['in_use_machines'] = base_queryset.filter(status='rented').count()
        context['maintenance_machines'] = base_queryset.filter(status='maintenance').count()
        context['machine_types'] = base_queryset.values('machine_type').distinct().count()
        context['machine_type_choices'] = [
            choice for choice in Machine._meta.get_field('machine_type').choices
            if choice[0] not in ['rice_mill', 'flatbed_dryer']
        ]
        context['selected_query'] = self.request.GET.get('q', '').strip()
        context['selected_type'] = self.request.GET.get('type', '').strip()
        context['selected_availability'] = self.request.GET.get('availability', '').strip()
        return context

class MachineDetailView(LoginRequiredMixin, DetailView):
    model = Machine
    template_name = 'machines/machine_detail.html'
    context_object_name = 'machine'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        machine = self.get_object()
        
        # Get related data
        context['rentals'] = machine.rentals.all().order_by('-start_date')
        context['maintenance_records'] = machine.maintenance_records.all().order_by('-start_date')
        context['price_history'] = machine.price_history.all().order_by('-start_date')
        
        # Get machine images (both from related MachineImage model and direct image field)
        context['images'] = machine.images.all()
        
        # Get similar machines based on machine type
        context['similar_machines'] = Machine.objects.filter(
            machine_type=machine.machine_type
        ).exclude(
            pk=machine.pk
        ).prefetch_related('images').order_by('-created_at')[:5]
        
        # Create calendar events data
        calendar_events = []
        
        # Add rental events
        for rental in context['rentals']:
            color = '#dc3545' if rental.status == 'approved' else '#ffc107'
            calendar_events.append({
                'title': 'Rented',
                'start': rental.start_date.strftime('%Y-%m-%d'),
                'end': rental.end_date.strftime('%Y-%m-%d'),
                'color': color
            })
        
        # Add maintenance events
        for record in context['maintenance_records']:
            if record.end_date:
                end_date = record.end_date.strftime('%Y-%m-%d')
            else:
                end_date = None
                
            calendar_events.append({
                'title': 'Maintenance',
                'start': record.start_date.strftime('%Y-%m-%d'),
                'end': end_date,
                'color': '#fd7e14'
            })
        
        # Add rice mill appointments if this is a rice mill
        if machine.is_rice_mill():
            appointments = machine.appointments.all().order_by('-appointment_date')
            context['appointments'] = appointments
            
            # Add appointment events to calendar
            for appointment in appointments:
                if appointment.status in RICE_MILL_LOCKED_STATUSES:
                    title = f"{appointment.display_time_range} - {appointment.user.get_full_name()}"
                    calendar_events.append({
                        'title': title,
                        'start': appointment.appointment_date.strftime('%Y-%m-%d'),
                        'allDay': True,
                        'color': '#007bff',
                        'range_label': appointment.display_time_range,
                        'start_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else '',
                        'end_time': appointment.end_time.strftime('%H:%M') if appointment.end_time else '',
                    })
        
        context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
        return context

class MachineCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Machine
    form_class = MachineForm
    template_name = 'machines/machine_form.html'
    success_url = reverse_lazy('machines:machine_list')
    permission_required = 'machines.add_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        
        # Add image formset
        if self.request.POST:
            context['formset'] = MachineImageFormSet(self.request.POST, self.request.FILES, prefix='form')
        else:
            context['formset'] = MachineImageFormSet(prefix='form')
            
        # Add machines for Services and Pricing section: both available and all with statuses
        available = Machine.objects.filter(status='available').order_by('name')
        context['available_machines'] = available
        context['all_machines'] = Machine.objects.all().order_by('name')
        return context
    
    def form_valid(self, form):
        """Handle form submission when form is valid"""
        # Save the machine first without committing to the database
        self.object = form.save()
        print(f"Creating new machine: {self.object.name} (ID: {self.object.id})")
        
        # Process the formset with the new machine instance
        formset = MachineImageFormSet(
            self.request.POST, 
            self.request.FILES, 
            instance=self.object,
            prefix='form'  # Make sure this matches the prefix in the template
        )
        
        # Debug information about the formset
        print(f"Formset valid: {formset.is_valid()}")
        print(f"Files in request: {len(self.request.FILES)}")
        for key, file in self.request.FILES.items():
            print(f"File: {key} = {file.name} ({file.size} bytes)")
            
        # DEBUG: Print all POST data related to the formset
        print("All formset-related POST data:")
        for key, value in self.request.POST.items():
            if key.startswith('form-'):
                print(f"POST: {key} = {value}")
            
        if not formset.is_valid():
            print(f"Formset errors: {formset.errors}")
            print(f"Management form data: {formset.management_form.data}")
            print(f"Total forms in management form: {formset.management_form.cleaned_data.get('TOTAL_FORMS')}")
            for form_index, form in enumerate(formset.forms):
                print(f"Form {form_index} errors: {form.errors}")
        
        # Process the formset if it's valid
        if formset.is_valid():
            # Save formset instances
            image_instances = formset.save(commit=False)
            print(f"Number of image instances to save: {len(image_instances)}")
            
            for image in image_instances:
                # Ensure the machine is set
                image.machine = self.object
                print(f"Saving image: {image.image}")
                
                try:
                    # Debug information before saving
                    if image.pk:
                        print(f"Updating existing MachineImage: id={image.pk}, is_primary={image.is_primary}")
                    else:
                        print(f"Saving MachineImage: machine={image.machine.id}, is_primary={image.is_primary}")
                    
                    if hasattr(image.image, 'name'):
                        print(f"Image file: {image.image.name}")
                    
                    image.save()
                    print(f"Successfully saved image: {image.id}")
                except Exception as e:
                    print(f"Error saving image: {str(e)}")
                    # More detailed error information
                    import traceback
                    traceback.print_exc()
            
            # Handle deleted images
            deleted_count = 0
            for obj in formset.deleted_objects:
                print(f"Deleting image: {obj.id}")
                try:
                    obj.delete()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting image {obj.id}: {str(e)}")
            
            print(f"Deleted {deleted_count} images")
            
            # Ensure there's at least one primary image if images exist
            try:
                images = self.object.images.all()
                if images.exists() and not images.filter(is_primary=True).exists():
                    first_image = images.first()
                    first_image.is_primary = True
                    print(f"Setting image {first_image.id} as primary")
                    first_image.save()
            except Exception as e:
                print(f"Error handling primary image: {str(e)}")
            
            # Force a final save of the formset
            try:
                formset.save()
                print(f"Final formset save completed. Total images: {self.object.images.count()}")
            except Exception as e:
                print(f"Error saving formset: {str(e)}")
        else:
            print("Formset is not valid, but machine has been created")
        
        messages.success(self.request, 'Machine created successfully.')
        return redirect(self.get_success_url())

class MachineUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Machine
    form_class = MachineForm
    template_name = 'machines/machine_form.html'
    permission_required = 'machines.change_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        
        # Add image formset
        if self.request.POST:
            context['formset'] = MachineImageFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form')
            # Print form errors for debugging
            if not context['formset'].is_valid():
                for i, form in enumerate(context['formset'].forms):
                    if form.errors:
                        print(f"Form {i} errors: {form.errors}")
        else:
            context['formset'] = MachineImageFormSet(instance=self.object, prefix='form')
            
        return context
    
    def get_success_url(self):
        return reverse('machines:machine_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle form submission when form is valid"""
        # Get the context data to access the formset
        context = self.get_context_data()
        formset = context['formset']
        
        # Print POST data for debugging
        print("POST data for image formset:")
        for key, value in self.request.POST.items():
            if key.startswith('form-'):
                print(f"{key}: {value}")
        
        # Print FILES data for debugging
        print("FILES data for image formset:")
        for key, value in self.request.FILES.items():
            if key.startswith('form-'):
                print(f"{key}: {value}")
        
        # Save the machine first
        self.object = form.save(commit=False)
        print(f"Saving machine {self.object.name} (ID: {self.object.id})")
        self.object.save()
        
        # Handle the formset
        print("Processing image formset")
        if formset.is_valid():
            print("Formset is valid")
            try:
                # Save but don't commit to allow for further processing
                image_instances = formset.save(commit=False)
                created_count = 0
                updated_count = 0
                deleted_count = 0
                
                print(f"Processing {len(image_instances)} image instances")
                for image in image_instances:
                    print(f"Processing image: {image.id if image.id else 'new'}")
                    # Make sure the image is associated with this machine
                    image.machine = self.object
                    image.save()
                    
                    if image.id:
                        updated_count += 1
                        print(f"Updated existing image: {image.id}")
                    else:
                        created_count += 1
                        print(f"Created new image with ID: {image.id}")
                
                # Now handle deletion of marked items
                print(f"Processing {len(formset.deleted_objects)} deleted objects")
                for obj in formset.deleted_objects:
                    print(f"Deleting image: {obj.id}")
                    try:
                        obj.delete()
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting image {obj.id}: {str(e)}")
                
                print(f"Created {created_count} images, updated {updated_count} images, deleted {deleted_count} images")
                
                # Ensure there's always a primary image if images exist
                images = self.object.images.all()
                if images.exists() and not images.filter(is_primary=True).exists():
                    first_image = images.first()
                    first_image.is_primary = True
                    first_image.save()
                    print(f"Set image {first_image.id} as primary since no primary was specified")
                
                print(f"Final formset save completed. Total images: {self.object.images.count()}")
                
                messages.success(self.request, 'Machine updated successfully.')
                return super().form_valid(form)
            
            except Exception as e:
                print(f"Error saving formset: {str(e)}")
                # Print stack trace for detailed error info
                import traceback
                traceback.print_exc()
                messages.error(self.request, f"An error occurred while saving images: {str(e)}")
                return self.form_invalid(form)
        else:
            print("Formset is invalid")
            print("Formset errors:", formset.errors)
            print("Non-form errors:", formset.non_form_errors())
            messages.error(self.request, 'Please correct the errors in the image section.')
            return self.form_invalid(form)

@login_required
def machine_delete_view(request, pk):
    """Simple function-based view for deleting machines"""
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser or 
            request.user.has_perm('machines.delete_machine')):
        messages.error(request, "You don't have permission to delete machines.")
        return redirect('machines:machine_list')
    
    machine = get_object_or_404(Machine, pk=pk)
    
    if request.method == 'POST':
        # Delete the machine
        machine_name = machine.name
        machine.delete()
        messages.success(request, f'Machine "{machine_name}" has been deleted successfully.')
        return redirect('machines:machine_list')
    
    # GET request - show confirmation page
    return render(request, 'machines/machine_confirm_delete.html', {'machine': machine})


# Keep the class-based view as backup
class MachineDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Machine
    template_name = 'machines/machine_confirm_delete.html'
    success_url = reverse_lazy('machines:machine_list')
    permission_required = 'machines.delete_machine'
    
    def has_permission(self):
        # Override to allow staff and admin users
        return (
            super().has_permission() or 
            self.request.user.is_staff or
            self.request.user.role in ['president', 'superuser']
        )
    
    def post(self, request, *args, **kwargs):
        """Handle POST request for deletion"""
        machine = self.get_object()
        machine_name = machine.name
        machine.delete()
        messages.success(request, f'Machine "{machine_name}" has been deleted successfully.')
        return redirect('machines:machine_list')

# Rental Views

class RentalListView(LoginRequiredMixin, ListView):
    model = Rental
    template_name = 'machines/rental_list.html'
    context_object_name = 'rentals'
    
    def get_queryset(self):
        """
        Return rentals based on user permissions:
        - Regular users see only their own rentals
        - Staff members can see all rentals
        """
        user = self.request.user
        if user.is_staff or user.has_perm('machines.can_view_all_rentals'):
            return Rental.objects.all()
        else:
            return Rental.objects.filter(user=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_approve'] = self.request.user.has_perm('machines.can_approve_rentals')
        return context

class RentalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Rental
    template_name = 'machines/rental_detail.html'
    context_object_name = 'rental'
    
    def test_func(self):
        """
        Ensure users can only view their own rentals unless they have
        permission to view all rentals
        """
        rental = self.get_object()
        user = self.request.user
        return (user == rental.user or 
                user.is_staff or 
                user.has_perm('machines.can_view_all_rentals'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rental = self.get_object()
        user = self.request.user
        
        # Check if user can modify this rental
        context['can_modify'] = (
            rental.can_be_modified() and
            (user == rental.user or user.is_staff)
        )
        
        # Check if user can approve/reject this rental
        context['can_approve'] = user.has_perm('machines.can_approve_rentals')
        
        return context

class RentalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Rental
    form_class = RentalForm
    template_name = 'machines/rental_form_enhanced.html'
    permission_required = 'machines.can_rent_machine'
    
    def has_permission(self):
        # Allow verified users or staff to rent machines
        user = self.request.user
        return (user.is_verified or 
                user.is_staff or 
                user.is_superuser or
                user.has_perm('machines.can_rent_machine'))
    
    def get_initial(self):
        initial = super().get_initial()
        if 'machine_pk' in self.kwargs:
            initial['machine'] = self.kwargs['machine_pk']
        return initial

    def dispatch(self, request, *args, **kwargs):
        machine_id = kwargs.get('machine_pk') or kwargs.get('machine_id')
        if machine_id:
            machine = get_object_or_404(Machine, pk=machine_id)
            if machine.machine_type == 'flatbed_dryer':
                messages.info(request, 'Flatbed dryer uses a separate dryer rental process.')
                return redirect('machines:dryer_rental_create_for_machine', machine_id=machine.pk)
            if machine.machine_type == 'rice_mill':
                messages.info(request, 'Rice mill uses a separate milling appointment process.')
                return redirect('machines:ricemill_appointment_create_for_machine', machine_id=machine.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass user to form for autofilling personal details
        kwargs['user'] = self.request.user
        if 'machine_pk' in self.kwargs:
            kwargs['machine_id'] = self.kwargs['machine_pk']
        elif 'machine_id' in self.kwargs: 
            kwargs['machine_id'] = self.kwargs['machine_id']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        
        # Add machine details if specified
        if 'machine_pk' in self.kwargs:
            try:
                machine = _machine_rental_queryset().get(pk=self.kwargs['machine_pk'])
                context['machine'] = machine
            except Machine.DoesNotExist:
                pass
        elif 'machine_id' in self.kwargs:
            try:
                machine = _machine_rental_queryset().get(pk=self.kwargs['machine_id'])
                context['machine'] = machine
            except Machine.DoesNotExist:
                pass
        
        # Add all machines for the service type dropdown
        context['available_machines'] = _machine_rental_queryset().filter(status='available').order_by('name')
        context['all_machines'] = _machine_rental_queryset().order_by('name')
        
        # Prepare machine data for JavaScript
        machines_data = []
        for m in _machine_rental_queryset().order_by('name'):
            pricing = m.get_pricing_info()
            machines_data.append({
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'type': m.get_machine_type_display(),
                'price': m.current_price,
                'pricing_rate': float(pricing.get('rate') or 0),
                'pricing_unit': pricing.get('unit') or '',
                'rental_price_type': m.rental_price_type,
                'allow_online_payment': m.allow_online_payment,
                'allow_face_to_face_payment': m.allow_face_to_face_payment,
                'settlement_type': m.settlement_type,
                'in_kind_farmer_share': m.in_kind_farmer_share,
                'in_kind_organization_share': m.in_kind_organization_share,
                'image': m.get_display_image_url() if m.get_display_image_url() else None,
            })
        context['machines_json'] = json.dumps(machines_data)
                
        return context
    
    def get(self, request, *args, **kwargs):
        # Check if trying to rent a rice mill machine and redirect appropriately
        if 'machine_pk' in kwargs:
            try:
                machine = Machine.objects.get(pk=kwargs['machine_pk'])
                if machine.is_rice_mill():
                    messages.info(request, 'Rice mill machines require scheduling an appointment instead of regular rental.')
                    return redirect('machines:ricemill_appointment_create', machine_pk=machine.pk)
            except Machine.DoesNotExist:
                pass
                
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.payment_amount = form.instance.calculate_payment_amount()
        
        # Get payment method from form
        payment_method = form.cleaned_data.get('payment_method')
        if payment_method:
            form.instance.payment_method = payment_method
        
        # Auto-approve request if admin is creating it
        if self.request.user.is_staff or self.request.user.is_superuser:
            form.instance.status = 'approved'
            messages.success(self.request, 'Rental request automatically approved.')
        else:
            # Show success message for regular users
            messages.success(
                self.request, 
                f'✅ Rental request submitted successfully! Your request for {form.instance.machine.name} '
                f'is now pending admin approval. You will be notified once it is reviewed.'
            )
        
        # Save the object first to get the ID (this will trigger the signal to create notifications)
        self.object = form.save()
        
        if self.object.payment_type == 'cash':
            # Create Payment object only for cash rentals
            from django.contrib.contenttypes.models import ContentType
            from bufia.models import Payment
            
            content_type = ContentType.objects.get_for_model(self.object)
            Payment.objects.get_or_create(
                content_type=content_type,
                object_id=self.object.id,
                defaults={
                    'user': self.request.user,
                    'payment_type': 'rental',
                    'amount': self.object.payment_amount or 0,
                    'currency': 'PHP',
                    'status': 'pending',
                }
            )
        
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Notify user on date conflicts
        error_text = str(form.errors) + " " + " ".join(e for e in form.non_field_errors())
        if 'already rented' in error_text.lower() or 'already booked' in error_text.lower():
            messages.error(self.request, 'This machine is already rented for the selected dates. Please rent this on another day.')
            try:
                machine_name = None
                try:
                    m = form.cleaned_data.get('machine') if hasattr(form, 'cleaned_data') else None
                    if m:
                        machine_name = getattr(m, 'name', None)
                except Exception:
                    pass
                # Try to get dates from POST
                start_date = self.request.POST.get('start_date')
                end_date = self.request.POST.get('end_date')
                msg = 'This machine is already rented for the selected dates. Please rent this on another day.'
                if machine_name:
                    if start_date and end_date:
                        msg = f'{machine_name} is already rented from {start_date} to {end_date}. Please rent this on another day.'
                    else:
                        msg = f'{machine_name} is already rented for the selected dates. Please rent this on another day.'
                UserNotification.objects.create(
                    user=self.request.user,
                    notification_type='rental_conflict',
                    message=msg
                )

                # Broadcast to other verified members (prefer same sector)
                try:
                    User = get_user_model()
                    requester_sector = None
                    try:
                        requester_sector = getattr(getattr(self.request.user, 'membership_application', None), 'assigned_sector', None)
                    except Exception:
                        requester_sector = None

                    if requester_sector:
                        recipients = User.objects.filter(is_verified=True, membership_application__assigned_sector=requester_sector)
                    else:
                        recipients = User.objects.filter(is_verified=True)
                    recipients = recipients.exclude(pk=self.request.user.pk)

                    broadcast_msg = msg
                    for member in recipients:
                        UserNotification.objects.create(
                            user=member,
                            notification_type='rental_conflict_broadcast',
                            message=broadcast_msg
                        )
                except Exception as e:
                    print(f'Failed to broadcast rental conflict notification: {e}')
            except Exception as e:
                print(f'Failed to create rental conflict notification: {e}')
        return super().form_invalid(form)
    
    def get_success_url(self):
        # Redirect to confirmation page
        return reverse('machines:rental_confirmation', kwargs={'pk': self.object.pk})

class RentalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Rental
    form_class = RentalForm
    template_name = 'machines/rental_form.html'
    
    def test_func(self):
        """Ensure users can only edit their own rentals that are in editable status"""
        rental = self.get_object()
        user = self.request.user
        return (rental.can_be_modified() and 
                (user == rental.user or user.is_staff) and
                user.has_perm('machines.can_rent_machine'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Rental Request'
        context['button_text'] = 'Update Rental'
        available = _machine_rental_queryset().filter(status='available').order_by('name')
        context['available_machines'] = available
        context['all_machines'] = _machine_rental_queryset().order_by('name')
        return context
    
    def get_success_url(self):
        return reverse('machines:rental_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # If status was already approved, set it back to pending
        if self.get_object().status == 'approved' and not self.request.user.is_staff:
            form.instance.status = 'pending'
            messages.info(self.request, 'Your rental has been updated and will require re-approval.')
        else:
            messages.success(self.request, 'Rental updated successfully!')
        
        return super().form_valid(form)

class RentalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Rental
    template_name = 'machines/rental_confirm_delete.html'
    success_url = reverse_lazy('machines:rental_list')
    
    def test_func(self):
        """Ensure users can only delete their own rentals that are in deletable status"""
        rental = self.get_object()
        user = self.request.user
        return (rental.can_be_cancelled() and 
                (user == rental.user or user.is_staff))
    
    def delete(self, request, *args, **kwargs):
        rental = self.get_object()
        # Instead of actually deleting, just mark as cancelled
        rental.status = 'cancelled'
        rental.save()
        messages.success(request, 'Rental cancelled successfully!')
        return redirect(self.success_url)

# Rice Mill Appointment Views
class RiceMillAppointmentListView(LoginRequiredMixin, ListView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_list.html'
    context_object_name = 'appointments'
    
    def get_queryset(self):
        queryset = RiceMillAppointment.objects.all()
        
        # Filter by user if not admin/staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Apply filters if present
        status_filter = self.request.GET.get('status')
        date_filter = self.request.GET.get('date')
        
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if date_filter:
            try:
                date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date=date_obj)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = list(context['appointments'])
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['date_filter'] = self.request.GET.get('date', '')
        context['pending_count'] = sum(1 for appointment in appointments if appointment.status == 'pending')
        context['approved_count'] = sum(1 for appointment in appointments if appointment.status == 'approved')
        context['paid_count'] = sum(1 for appointment in appointments if appointment.status == 'paid')
        context['confirmed_count'] = sum(1 for appointment in appointments if appointment.status == 'confirmed')
        context['completed_count'] = sum(1 for appointment in appointments if appointment.status == 'completed')
        return context

class RiceMillAppointmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_detail.html'
    context_object_name = 'appointment'
    
    def test_func(self):
        # Only allow users to view their own appointments or staff to view any
        appointment = self.get_object()
        return self.request.user.is_staff or self.request.user == appointment.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.get_object()
        
        # Add machine details
        context['machine_details'] = {
            'name': appointment.machine.name,
            'description': appointment.machine.description,
            'rental_fee': appointment.machine.current_price,
        }
        
        # Check if the appointment can be modified
        context['can_modify'] = appointment.can_be_modified()
        context['can_cancel'] = appointment.can_be_cancelled()
        
        payment = _get_appointment_payment(appointment)
        context['payment'] = payment
        context['total_amount'] = appointment.total_amount
        context['can_select_payment_method'] = (
            self.request.user == appointment.user
            and appointment.status == 'approved'
            and not appointment.payment_method
        )
        context['can_pay_online'] = (
            self.request.user == appointment.user
            and appointment.status == 'approved'
            and appointment.payment_method == 'online'
            and (not payment or payment.status != 'completed')
        )
        context['awaiting_face_to_face'] = (
            appointment.status == 'approved'
            and appointment.payment_method == 'face_to_face'
        )
        context['can_admin_confirm_payment'] = (
            self.request.user.is_staff
            and appointment.status in ['approved', 'paid']
            and appointment.payment_method in ['online', 'face_to_face']
            and (
                appointment.payment_method == 'face_to_face'
                or (payment and payment.status == 'completed')
            )
        )
        context['can_admin_mark_completed'] = (
            self.request.user.is_staff and appointment.status == 'confirmed'
        )
        
        return context

class RiceMillAppointmentCreateView(LoginRequiredMixin, CreateView):
    model = RiceMillAppointment
    form_class = RiceMillAppointmentForm
    template_name = 'machines/ricemill_appointment_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check verification status before processing the view"""
        if not request.user.is_verified:
            if not request.user.is_superuser:
                messages.warning(
                    request,
                    "Your membership requires verification before you can schedule appointments. "
                    "Please complete your profile and submit the membership form."
                )
                return redirect('profile')
                
        return super().dispatch(request, *args, **kwargs)
        
    def get_initial(self):
        initial = super().get_initial()
        # Pre-populate machine if provided in URL
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            initial['machine'] = machine_id
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the machine_id to the form if it exists in the URL
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            kwargs['machine_id'] = machine_id
        # Pass the current user to the form
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        
        # Get the rice mill machine for calendar display
        form = context.get('form')
        rice_mill = None

        if form is not None and hasattr(form, 'cleaned_data'):
            rice_mill = form.cleaned_data.get('machine')

        if not rice_mill and form is not None:
            instance = getattr(form, 'instance', None)
            if getattr(instance, 'machine_id', None):
                rice_mill = instance.machine

        if not rice_mill and form is not None:
            rice_mill = getattr(form, '_selected_machine', None)

        if not rice_mill:
            rice_mill = Machine.objects.filter(
                pk=self.kwargs.get('machine_id'),
                machine_type='rice_mill'
            ).first()
        if not rice_mill:
            rice_mill = Machine.objects.filter(machine_type='rice_mill', status='available').first()
        if not rice_mill:
            rice_mill = Machine.objects.filter(machine_type='rice_mill').first()
        if rice_mill:
            context['machine'] = rice_mill
            machine = rice_mill
            
            # Add calendar data for the rice mill
            # Get existing appointments for this machine
            appointments = RiceMillAppointment.objects.filter(
                machine=machine,
                status__in=RICE_MILL_LOCKED_STATUSES
            )
            
            # Format for calendar
            calendar_events = []
            for appointment in appointments:
                title = f"{appointment.display_time_range} - {appointment.user.get_full_name()}"
                color = '#007bff'
                
                calendar_events.append({
                    'title': title,
                    'start': appointment.appointment_date.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': color,
                    'range_label': appointment.display_time_range,
                    'start_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else '',
                    'end_time': appointment.end_time.strftime('%H:%M') if appointment.end_time else '',
                    'booked_by': appointment.user.get_full_name(),
                    'status': appointment.status,
                })
            
            # Also add maintenance and rentals
            maintenance_records = Maintenance.objects.filter(
                machine=machine,
                status__in=['scheduled', 'in_progress']
            )
            
            rentals = Rental.objects.filter(
                machine=machine,
                status='approved'
            )
            
            for record in maintenance_records:
                if record.end_date:
                    end_date = record.end_date.strftime('%Y-%m-%d')
                else:
                    end_date = None
                    
                calendar_events.append({
                    'title': 'Maintenance',
                    'start': record.start_date.strftime('%Y-%m-%d'),
                    'end': end_date,
                    'color': '#fd7e14'
                })
            
            for rental in rentals:
                calendar_events.append({
                    'title': 'Rented',
                    'start': rental.start_date.strftime('%Y-%m-%d'),
                    'end': rental.end_date.strftime('%Y-%m-%d'),
                    'color': '#dc3545'
                })
            
            context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
                
        return context
    
    def form_valid(self, form):
        # Set the user automatically to the current user
        form.instance.user = self.request.user
        
        form.instance.status = 'pending'
        appointment = form.save(commit=False)
        
        # Ensure machine is set from cleaned_data
        if not appointment.machine_id:
            appointment.machine = (
                form.cleaned_data.get('machine')
                or Machine.objects.filter(
                    pk=self.kwargs.get('machine_id'),
                    machine_type='rice_mill'
                ).first()
                or Machine.objects.filter(machine_type='rice_mill', status='available').first()
                or Machine.objects.filter(machine_type='rice_mill').first()
            )
        if not appointment.machine_id:
            form.add_error(None, 'No rice mill is configured yet. Please contact the administrator.')
            return self.form_invalid(form)
        
        appointment.save()
        
        # Store the appointment ID for redirect
        self.object = appointment
        
        messages.success(self.request, 'Appointment created successfully and is now waiting for admin approval.')
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('machines:ricemill_appointment_pending', kwargs={'pk': self.object.pk})

class RiceMillAppointmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RiceMillAppointment
    form_class = RiceMillAppointmentForm
    template_name = 'machines/ricemill_appointment_form.html'
    
    def test_func(self):
        # Only allow users to update their own appointments that are still pending or approved
        appointment = self.get_object()
        if not appointment.can_be_modified():
            return False
        return self.request.user == appointment.user or self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        
        # Add calendar data for the selected machine
        appointment = self.get_object()
        machine = appointment.machine
        context['machine'] = machine
        
        # Get existing appointments for this machine
        appointments = RiceMillAppointment.objects.filter(
            machine=machine,
            status__in=RICE_MILL_LOCKED_STATUSES
        ).exclude(pk=appointment.pk)
        
        # Format for calendar
        calendar_events = []
        for other_appointment in appointments:
            title = f"{other_appointment.display_time_range} - {other_appointment.user.get_full_name()}"
            color = '#007bff'
            
            calendar_events.append({
                'title': title,
                'start': other_appointment.appointment_date.strftime('%Y-%m-%d'),
                'allDay': True,
                'color': color,
                'range_label': other_appointment.display_time_range,
                'start_time': other_appointment.start_time.strftime('%H:%M') if other_appointment.start_time else '',
                'end_time': other_appointment.end_time.strftime('%H:%M') if other_appointment.end_time else '',
                'booked_by': other_appointment.user.get_full_name(),
                'status': other_appointment.status,
            })
        
        # Also add maintenance and rentals
        maintenance_records = Maintenance.objects.filter(
            machine=machine,
            status__in=['scheduled', 'in_progress']
        )
        
        rentals = Rental.objects.filter(
            machine=machine,
            status='approved'
        )
        
        for record in maintenance_records:
            if record.end_date:
                end_date = record.end_date.strftime('%Y-%m-%d')
            else:
                end_date = None
                
            calendar_events.append({
                'title': 'Maintenance',
                'start': record.start_date.strftime('%Y-%m-%d'),
                'end': end_date,
                'color': '#fd7e14'
            })
        
        for rental in rentals:
            calendar_events.append({
                'title': 'Rented',
                'start': rental.start_date.strftime('%Y-%m-%d'),
                'end': rental.end_date.strftime('%Y-%m-%d'),
                'color': '#dc3545'
            })
        
        context['calendar_events_json'] = mark_safe(json.dumps(calendar_events))
        return context
    
    def form_valid(self, form):
        form.instance.status = 'pending'
        messages.info(self.request, 'Your appointment has been updated and is waiting for admin approval again.')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('machines:ricemill_appointment_detail', kwargs={'pk': self.object.pk})

class RiceMillAppointmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = RiceMillAppointment
    template_name = 'machines/ricemill_appointment_confirm_delete.html'
    success_url = reverse_lazy('machines:ricemill_appointment_list')
    
    def test_func(self):
        # Only allow users to delete their own appointments that can be cancelled
        appointment = self.get_object()
        if not appointment.can_be_cancelled():
            return False
        return self.request.user == appointment.user or self.request.user.is_staff
    
    def delete(self, request, *args, **kwargs):
        appointment = self.get_object()
        success_message = f'Appointment for {appointment.appointment_date} has been cancelled.'
        messages.success(self.request, success_message)
        return super().delete(request, *args, **kwargs)

@login_required
def approve_appointment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to approve appointments.")
    
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    if request.method == 'POST':
        conflict_exists = RiceMillAppointment.objects.filter(
            machine=appointment.machine,
            appointment_date=appointment.appointment_date,
            status__in=RICE_MILL_LOCKED_STATUSES,
            start_time__lt=appointment.end_time,
            end_time__gt=appointment.start_time,
        ).exclude(pk=appointment.pk).exists()
        if conflict_exists:
            messages.error(request, 'This time range overlaps with another approved or confirmed appointment.')
            return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

        appointment.status = 'approved'
        appointment.save()
        messages.success(request, 'Appointment approved. The user can now choose a payment method.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
    
    return render(request, 'machines/ricemill_appointment_confirm_approve.html', {'appointment': appointment})

@login_required
def reject_appointment(request, pk):
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    # Ensure only staff can reject appointments
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to reject appointments.")
    
    # Handle form submission
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        appointment.status = 'rejected'
        appointment.save()
        
        try:
            # Try to create a notification
            create_notification(
                user=appointment.user,
                title="Appointment Rejected",
                message=f"Your rice mill appointment for {appointment.appointment_date} has been rejected.",
                category="appointment",
                reference_object=appointment
            )
        except Exception as e:
            # Log the error but continue
            print(f"Error creating notification: {e}")
        
        messages.success(request, 'Appointment has been rejected.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
    
    return render(request, 'machines/ricemill_appointment_confirm_reject.html', {'appointment': appointment})

@login_required
def ricemill_appointment_pending(request, pk):
    """View for displaying the pending appointment confirmation page"""
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    # Ensure only the appointment owner can view the pending page
    if request.user != appointment.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this appointment.")

    if appointment.status != 'pending':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)
        
    return render(request, 'machines/ricemill_appointment_pending.html', {'appointment': appointment})


@login_required
def select_ricemill_payment_method(request, pk):
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    if request.user != appointment.user:
        return HttpResponseForbidden("You don't have permission to update this appointment.")

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status != 'approved':
        messages.info(request, 'Payment method can only be selected after admin approval.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    payment_method = request.POST.get('payment_method')
    if payment_method not in ['online', 'face_to_face']:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    appointment.payment_method = payment_method
    appointment.save(update_fields=['payment_method', 'updated_at'])

    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment

    content_type = ContentType.objects.get_for_model(RiceMillAppointment)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=appointment.id,
        defaults={
            'user': appointment.user,
            'payment_type': 'appointment',
            'amount': appointment.total_amount,
            'currency': 'PHP',
            'status': 'pending',
        }
    )
    if not created and payment.amount != appointment.total_amount:
        payment.amount = appointment.total_amount
        payment.save(update_fields=['amount'])

    if payment_method == 'online':
        messages.success(request, 'Online payment selected. You can now proceed to payment.')
    else:
        messages.success(request, 'Face-to-face payment selected. Please pay at the BUFIA office for admin confirmation.')

    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def confirm_ricemill_payment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to confirm payments.")

    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    payment = _get_appointment_payment(appointment)

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status not in ['approved', 'paid']:
        messages.info(request, 'This appointment is not waiting for payment confirmation.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.payment_method == 'online' and (not payment or payment.status != 'completed'):
        messages.error(request, 'Online payment has not been completed yet.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.payment_method == 'face_to_face':
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment

        content_type = ContentType.objects.get_for_model(RiceMillAppointment)
        payment, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=appointment.id,
            defaults={
                'user': appointment.user,
                'payment_type': 'appointment',
                'amount': appointment.total_amount,
                'currency': 'PHP',
                'status': 'completed',
                'paid_at': timezone.now(),
            }
        )
        update_fields = []
        if not created and payment.status != 'completed':
            payment.status = 'completed'
            update_fields.append('status')
        if payment.paid_at is None:
            payment.paid_at = timezone.now()
            update_fields.append('paid_at')
        if update_fields:
            payment.save(update_fields=update_fields)

    appointment.status = 'confirmed'
    appointment.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Appointment payment confirmed. The slot is now fully confirmed.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


@login_required
def complete_ricemill_appointment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to complete appointments.")

    appointment = get_object_or_404(RiceMillAppointment, pk=pk)

    if request.method != 'POST':
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    if appointment.status != 'confirmed':
        messages.info(request, 'Only confirmed appointments can be marked as completed.')
        return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)

    appointment.status = 'completed'
    appointment.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Appointment marked as completed.')
    return redirect('machines:ricemill_appointment_detail', pk=appointment.pk)


class DryerRentalListView(LoginRequiredMixin, ListView):
    model = DryerRental
    template_name = 'machines/dryer_rental_list.html'
    context_object_name = 'dryer_rentals'

    def get_queryset(self):
        queryset = DryerRental.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        status_filter = self.request.GET.get('status')
        date_filter = self.request.GET.get('date')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        if date_filter:
            try:
                date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(rental_date=date_obj)
            except ValueError:
                pass
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rentals = list(context['dryer_rentals'])
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['date_filter'] = self.request.GET.get('date', '')
        context['pending_count'] = sum(1 for rental in rentals if rental.status == 'pending')
        context['approved_count'] = sum(1 for rental in rentals if rental.status == 'approved')
        context['paid_count'] = sum(1 for rental in rentals if rental.status == 'paid')
        context['confirmed_count'] = sum(1 for rental in rentals if rental.status == 'confirmed')
        context['completed_count'] = sum(1 for rental in rentals if rental.status == 'completed')
        return context


class DryerRentalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = DryerRental
    template_name = 'machines/dryer_rental_detail.html'
    context_object_name = 'dryer_rental'

    def test_func(self):
        dryer_rental = self.get_object()
        return self.request.user.is_staff or self.request.user == dryer_rental.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dryer_rental = self.get_object()
        payment = _get_dryer_payment(dryer_rental)

        context['payment'] = payment
        context['total_amount'] = dryer_rental.total_amount
        context['can_modify'] = dryer_rental.can_be_modified()
        context['can_cancel'] = dryer_rental.can_be_cancelled()
        context['can_select_payment_method'] = (
            self.request.user == dryer_rental.user
            and dryer_rental.status == 'approved'
            and not dryer_rental.payment_method
        )
        context['can_pay_online'] = (
            self.request.user == dryer_rental.user
            and dryer_rental.status == 'approved'
            and dryer_rental.payment_method == 'online'
            and (not payment or payment.status != 'completed')
        )
        context['awaiting_face_to_face'] = (
            dryer_rental.status == 'approved' and dryer_rental.payment_method == 'face_to_face'
        )
        context['can_admin_confirm_payment'] = (
            self.request.user.is_staff
            and dryer_rental.status in ['approved', 'paid']
            and dryer_rental.payment_method in ['online', 'face_to_face']
            and (
                dryer_rental.payment_method == 'face_to_face'
                or (payment and payment.status == 'completed')
            )
        )
        context['can_admin_mark_completed'] = self.request.user.is_staff and dryer_rental.status == 'confirmed'
        return context


class DryerRentalCreateView(LoginRequiredMixin, CreateView):
    model = DryerRental
    form_class = DryerRentalForm
    template_name = 'machines/dryer_rental_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_verified and not request.user.is_superuser:
            messages.warning(request, "Your membership requires verification before you can schedule dryer rentals.")
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            initial['machine'] = machine_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        machine_id = self.kwargs.get('machine_id')
        if machine_id:
            kwargs['machine_id'] = machine_id
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        dryer = (
            getattr(context.get('form'), '_selected_machine', None)
            or Machine.objects.filter(
                pk=self.kwargs.get('machine_id'),
                machine_type='flatbed_dryer'
            ).first()
            or Machine.objects.filter(machine_type='flatbed_dryer', status='available').first()
            or Machine.objects.filter(machine_type='flatbed_dryer').first()
        )
        if dryer:
            context['machine'] = dryer
            rentals = DryerRental.objects.filter(machine=dryer, status__in=DRYER_LOCKED_STATUSES)
            events = []
            for rental in rentals:
                events.append({
                    'title': f"{rental.display_time_range} - {rental.user.get_full_name()}",
                    'start': rental.rental_date.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#f59f00',
                    'range_label': rental.display_time_range,
                    'start_time': rental.start_time.strftime('%H:%M'),
                    'end_time': rental.end_time.strftime('%H:%M'),
                    'booked_by': rental.user.get_full_name(),
                    'status': rental.status,
                })
            context['calendar_events_json'] = mark_safe(json.dumps(events))
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = 'pending'
        dryer = (
            form.cleaned_data.get('machine')
            or getattr(form, '_selected_machine', None)
            or Machine.objects.filter(machine_type='flatbed_dryer', status='available').first()
            or Machine.objects.filter(machine_type='flatbed_dryer').first()
        )
        if not dryer:
            form.add_error(None, 'No flatbed dryer is configured yet. Please contact the administrator.')
            return self.form_invalid(form)
        form.instance.machine = dryer
        self.object = form.save()
        messages.success(self.request, 'Dryer rental request created successfully and is now waiting for admin approval.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('machines:dryer_rental_pending', kwargs={'pk': self.object.pk})


class DryerRentalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DryerRental
    form_class = DryerRentalForm
    template_name = 'machines/dryer_rental_form.html'

    def test_func(self):
        dryer_rental = self.get_object()
        if not dryer_rental.can_be_modified():
            return False
        return self.request.user == dryer_rental.user or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        dryer_rental = self.get_object()
        machine = dryer_rental.machine
        context['machine'] = machine
        rentals = DryerRental.objects.filter(machine=machine, status__in=DRYER_LOCKED_STATUSES).exclude(pk=dryer_rental.pk)
        events = []
        for rental in rentals:
            events.append({
                'title': f"{rental.display_time_range} - {rental.user.get_full_name()}",
                'start': rental.rental_date.strftime('%Y-%m-%d'),
                'allDay': True,
                'color': '#f59f00',
                'range_label': rental.display_time_range,
                'start_time': rental.start_time.strftime('%H:%M'),
                'end_time': rental.end_time.strftime('%H:%M'),
                'booked_by': rental.user.get_full_name(),
                'status': rental.status,
            })
        context['calendar_events_json'] = mark_safe(json.dumps(events))
        return context

    def form_valid(self, form):
        dryer = (
            form.cleaned_data.get('machine')
            or self.get_object().machine
            or getattr(form, '_selected_machine', None)
        )
        if not dryer:
            form.add_error(None, 'No flatbed dryer is configured for this rental.')
            return self.form_invalid(form)
        form.instance.machine = dryer
        form.instance.status = 'pending'
        messages.info(self.request, 'Your dryer rental has been updated and is waiting for admin approval again.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('machines:dryer_rental_detail', kwargs={'pk': self.object.pk})


class DryerRentalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = DryerRental
    template_name = 'machines/dryer_rental_confirm_delete.html'
    success_url = reverse_lazy('machines:dryer_rental_list')

    def test_func(self):
        dryer_rental = self.get_object()
        if not dryer_rental.can_be_cancelled():
            return False
        return self.request.user == dryer_rental.user or self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        dryer_rental = self.get_object()
        messages.success(self.request, f'Dryer rental for {dryer_rental.rental_date} has been cancelled.')
        return super().delete(request, *args, **kwargs)


@login_required
def approve_dryer_rental(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to approve dryer rentals.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.method == 'POST':
        conflict_exists = DryerRental.objects.filter(
            machine=dryer_rental.machine,
            rental_date=dryer_rental.rental_date,
            status__in=DRYER_LOCKED_STATUSES,
            start_time__lt=dryer_rental.end_time,
            end_time__gt=dryer_rental.start_time,
        ).exclude(pk=dryer_rental.pk).exists()
        if conflict_exists:
            messages.error(request, 'This dryer time range overlaps with another approved or confirmed rental.')
            return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
        dryer_rental.status = 'approved'
        dryer_rental.save()
        messages.success(request, 'Dryer rental approved. The user can now choose a payment method.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    return render(request, 'machines/dryer_rental_confirm_approve.html', {'dryer_rental': dryer_rental})


@login_required
def reject_dryer_rental(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to reject dryer rentals.")
    if request.method == 'POST':
        dryer_rental.status = 'rejected'
        dryer_rental.save()
        messages.success(request, 'Dryer rental has been rejected.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    return render(request, 'machines/dryer_rental_confirm_reject.html', {'dryer_rental': dryer_rental})


@login_required
def dryer_rental_pending(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.user != dryer_rental.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this dryer rental.")
    if dryer_rental.status != 'pending':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    return render(request, 'machines/dryer_rental_pending.html', {'dryer_rental': dryer_rental})


@login_required
def select_dryer_payment_method(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.user != dryer_rental.user:
        return HttpResponseForbidden("You don't have permission to update this dryer rental.")
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status != 'approved':
        messages.info(request, 'Payment method can only be selected after admin approval.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    payment_method = request.POST.get('payment_method')
    if payment_method not in ['online', 'face_to_face']:
        messages.error(request, 'Please choose a valid payment method.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    dryer_rental.payment_method = payment_method
    dryer_rental.save(update_fields=['payment_method', 'updated_at'])

    from django.contrib.contenttypes.models import ContentType
    from bufia.models import Payment
    content_type = ContentType.objects.get_for_model(DryerRental)
    payment, created = Payment.objects.get_or_create(
        content_type=content_type,
        object_id=dryer_rental.id,
        defaults={
            'user': dryer_rental.user,
            'payment_type': 'dryer',
            'amount': dryer_rental.total_amount,
            'currency': 'PHP',
            'status': 'pending',
        }
    )
    if not created and payment.amount != dryer_rental.total_amount:
        payment.amount = dryer_rental.total_amount
        payment.save(update_fields=['amount'])
    messages.success(request, 'Online payment selected. You can now proceed to payment.' if payment_method == 'online' else 'Face-to-face payment selected. Please pay at the BUFIA office for admin confirmation.')
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def confirm_dryer_payment(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to confirm dryer payments.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    payment = _get_dryer_payment(dryer_rental)
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status not in ['approved', 'paid']:
        messages.info(request, 'This dryer rental is not waiting for payment confirmation.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.payment_method == 'online' and (not payment or payment.status != 'completed'):
        messages.error(request, 'Online payment has not been completed yet.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.payment_method == 'face_to_face':
        from django.contrib.contenttypes.models import ContentType
        from bufia.models import Payment
        content_type = ContentType.objects.get_for_model(DryerRental)
        payment, _ = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=dryer_rental.id,
            defaults={
                'user': dryer_rental.user,
                'payment_type': 'dryer',
                'amount': dryer_rental.total_amount,
                'currency': 'PHP',
                'status': 'completed',
                'paid_at': timezone.now(),
            }
        )
        update_fields = []
        if payment.status != 'completed':
            payment.status = 'completed'
            update_fields.append('status')
        if payment.paid_at is None:
            payment.paid_at = timezone.now()
            update_fields.append('paid_at')
        if update_fields:
            payment.save(update_fields=update_fields)
    dryer_rental.status = 'confirmed'
    dryer_rental.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Dryer rental payment confirmed.')
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def complete_dryer_rental(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to complete dryer rentals.")
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if request.method != 'POST':
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    if dryer_rental.status != 'confirmed':
        messages.info(request, 'Only confirmed dryer rentals can be marked as completed.')
        return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)
    dryer_rental.status = 'completed'
    dryer_rental.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Dryer rental marked as completed.')
    return redirect('machines:dryer_rental_detail', pk=dryer_rental.pk)


@login_required
def dryer_rental_receipt(request, pk):
    dryer_rental = get_object_or_404(DryerRental, pk=pk)
    if dryer_rental.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('machines:dryer_rental_list')
    return render(request, 'machines/dryer_rental_receipt.html', {
        'dryer_rental': dryer_rental,
        'total_amount': dryer_rental.total_amount,
    })

@login_required
def debug_machine_images(request, pk):
    """Debug view to check machine images"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only")
    
    machine = get_object_or_404(Machine, pk=pk)
    
    # Check media directories
    media_root = settings.MEDIA_ROOT
    machine_dir = os.path.join(media_root, 'machines')
    machine_images_dir = os.path.join(machine_dir, 'images')
    
    # Generate machine slug
    machine_slug = slugify(machine.name)
    machine_specific_dir = os.path.join(machine_images_dir, machine_slug)
    
    # Directory structure
    directories = {
        'MEDIA_ROOT': {
            'path': media_root,
            'exists': os.path.exists(media_root),
        },
        'machines/': {
            'path': machine_dir,
            'exists': os.path.exists(machine_dir),
        },
        'machines/images/': {
            'path': machine_images_dir,
            'exists': os.path.exists(machine_images_dir),
        },
        f'machines/images/{machine_slug}/': {
            'path': machine_specific_dir,
            'exists': os.path.exists(machine_specific_dir),
        },
    }
    
    # Check machine direct image
    machine_image = {
        'field': machine.image,
        'url': machine.image.url if machine.image else None,
        'path': machine.image.path if machine.image else None,
        'exists': os.path.exists(machine.image.path) if machine.image else False,
    }
    
    # Check related images
    related_images = []
    for img in machine.images.all():
        related_images.append({
            'id': img.id,
            'url': img.image.url if img.image else None,
            'path': img.image.path if img.image else None,
            'exists': os.path.exists(img.image.path) if img.image else False,
            'is_primary': img.is_primary,
        })
    
    # List files in machine-specific directory
    directory_files = []
    if os.path.exists(machine_specific_dir):
        for file in os.listdir(machine_specific_dir):
            file_path = os.path.join(machine_specific_dir, file)
            directory_files.append({
                'name': file,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'in_db': any(img['path'] == file_path for img in related_images) if related_images else False,
            })
    
    context = {
        'machine': machine,
        'directories': directories,
        'machine_image': machine_image,
        'related_images': related_images,
        'directory_files': directory_files,
    }
    
    return render(request, 'machines/debug_images.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/dashboard/', redirect_field_name=None)
def maintenance_list(request):
    """View all maintenance records with filtering options"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    machine_filter = request.GET.get('machine', '')
    maintenance_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    maintenance_records = Maintenance.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        maintenance_records = maintenance_records.filter(status=status_filter)
    if machine_filter:
        maintenance_records = maintenance_records.filter(machine_id=machine_filter)
    if maintenance_type:
        maintenance_records = maintenance_records.filter(maintenance_type=maintenance_type)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(start_date__date__gte=date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(start_date__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Find machines with status 'maintenance' that don't have active maintenance records
    machines_under_maintenance = Machine.objects.filter(status='maintenance')
    
    # Create a list to track machines that already have active maintenance records
    machines_with_records = set(
        maintenance_records.filter(
            status__in=['scheduled', 'in_progress'],
            machine__status='maintenance'
        ).values_list('machine_id', flat=True)
    )
    
    # Find machines that are in maintenance status but don't have active maintenance records
    orphaned_machines = []
    for machine in machines_under_maintenance:
        if machine.id not in machines_with_records:
            orphaned_machines.append(machine)
    
    # Get machines and maintenance types for filter dropdowns
    machines = Machine.objects.all().order_by('name')
    maintenance_types = Maintenance.MAINTENANCE_TYPE_CHOICES
    status_choices = Maintenance.STATUS_CHOICES
    
    # Statistics
    active_maintenance = maintenance_records.filter(status__in=['scheduled', 'in_progress']).count() + len(orphaned_machines)
    completed_maintenance = maintenance_records.filter(status='completed').count()
    overdue_maintenance = sum(1 for record in maintenance_records if record.is_overdue())
    
    context = {
        'maintenance_records': maintenance_records,
        'orphaned_machines': orphaned_machines, 
        'machines': machines,
        'maintenance_types': maintenance_types,
        'status_choices': status_choices,
        'active_maintenance': active_maintenance,
        'completed_maintenance': completed_maintenance,
        'overdue_maintenance': overdue_maintenance,
        'selected_status': status_filter,
        'selected_machine': machine_filter,
        'selected_type': maintenance_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'machines/maintenance_list.html', context)

@login_required
def maintenance_detail(request, pk):
    """View details of a specific maintenance record"""
    maintenance = get_object_or_404(Maintenance, pk=pk)
    
    context = {
        'maintenance': maintenance,
    }
    
    return render(request, 'machines/maintenance_detail.html', context)

@login_required
def maintenance_complete(request, pk):
    """Mark a maintenance record as completed"""
    maintenance = get_object_or_404(Maintenance, pk=pk)
    
    if request.method == 'POST':
        # Update maintenance status
        maintenance.status = 'completed'
        maintenance.actual_completion_date = timezone.now()
        maintenance.save()
        
        # Check if there are other active maintenance records for this machine
        other_active_records = Maintenance.objects.filter(
            machine=maintenance.machine,
            status__in=['scheduled', 'in_progress']
        ).exclude(pk=maintenance.pk).exists()
        
        # If no other active records and machine is in maintenance status, set it back to available
        if not other_active_records and maintenance.machine.status == 'maintenance':
            maintenance.machine.status = 'available'
            maintenance.machine.save()
        
        messages.success(request, f'Maintenance for {maintenance.machine.name} marked as completed.')
        
        # Redirect to the maintenance detail page if it exists, otherwise to the maintenance list
        try:
            return redirect('machines:maintenance_detail', pk=maintenance.pk)
        except NoReverseMatch:
            return redirect('machines:maintenance_list')
    
    context = {
        'maintenance': maintenance,
    }
    
    return render(request, 'machines/maintenance_complete_confirm.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_rental_create(request, machine_pk=None):
    """Admin view for creating rentals on behalf of users"""
    if request.method == 'POST':
        form = AdminRentalForm(request.POST)
        if form.is_valid():
            rental = form.save(commit=False)
            
            # Get renter name from form
            renter_name = form.cleaned_data['renter_name']
            
            # Find or create a temporary system user for this rental
            # First check if a system user already exists for tracking rentals
            User = get_user_model()
            system_user = None
            
            try:
                # Try to find an existing system user with this name
                system_user = User.objects.get(username='system')
            except User.DoesNotExist:
                # Create a system user if one doesn't exist
                system_user = User.objects.create_user(
                    username='system',
                    email='system@bufia.local',
                    password=get_random_string(length=32),
                    first_name='System',
                    last_name='User',
                    is_active=False
                )
            
            # Assign the system user but store the actual renter name in purpose field
            rental.user = system_user
            
            # Prepend renter name to purpose
            if rental.purpose:
                rental.purpose = f"Renter: {renter_name}\n\n{rental.purpose}"
            else:
                rental.purpose = f"Renter: {renter_name}"
            
            rental.save()

            # Keep amount aligned with admin-configured machine pricing
            rental.payment_amount = rental.calculate_payment_amount()
            rental.save(update_fields=['payment_amount'])
            
            if rental.payment_type == 'cash':
                from django.contrib.contenttypes.models import ContentType
                from bufia.models import Payment
                
                content_type = ContentType.objects.get_for_model(rental)
                Payment.objects.get_or_create(
                    content_type=content_type,
                    object_id=rental.id,
                    defaults={
                        'user': system_user,
                        'payment_type': 'rental',
                        'amount': rental.payment_amount or 0,
                        'currency': 'PHP',
                        'status': 'pending',
                    }
                )
            
            messages.success(request, f'Rental for {renter_name} created and automatically approved.')
            return redirect('machines:rental_detail', pk=rental.pk)
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = AdminRentalForm(initial=initial)
    
    context = {
        'form': form,
        'action': 'Create',
        'is_admin_form': True
    }
    return render(request, 'machines/admin_rental_form.html', context)


@login_required
def ricemill_appointment_receipt(request, pk):
    """Render a printable receipt for rice mill appointment"""
    appointment = get_object_or_404(RiceMillAppointment, pk=pk)
    
    # Security check - only allow the appointment owner or staff to view
    if appointment.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('machines:ricemill_appointment_list')
    
    total_amount = appointment.total_amount
    
    context = {
        'appointment': appointment,
        'total_amount': total_amount,
    }
    
    return render(request, 'machines/ricemill_appointment_receipt.html', context)
