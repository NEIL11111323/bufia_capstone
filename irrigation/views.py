from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Max, F, Subquery, OuterRef, Q

from users.decorators import verified_member_required, water_tender_required
from users.models import Sector
from .models import WaterIrrigationRequest, IrrigationRequestHistory
from .forms import IrrigationRequestForm, IrrigationRequestStatusForm, AdminIrrigationRequestForm

def is_admin_or_president(user):
    """Check if user is admin"""
    return user.is_superuser

def is_admin_president_or_water_tender(user):
    """Check if user is admin or water tender"""
    return user.is_superuser or user.is_water_tender()

# Farmer Views
@login_required
def irrigation_request_create(request):
    """View for farmers to create new irrigation requests"""
    # Check if user is verified member (skip check for admin/staff)
    if not (request.user.is_superuser or request.user.is_staff):
        if not (hasattr(request.user, 'is_verified') and request.user.is_verified):
            messages.error(request, "You must be a verified member to create irrigation requests.")
            return redirect('dashboard')
    
    if request.method == 'POST':
        form = IrrigationRequestForm(request.POST, user=request.user)
        if form.is_valid():
            # Ensure the user has a MembershipApplication and an assigned_sector
            if not hasattr(request.user, 'membership_application') or \
               not request.user.membership_application.assigned_sector:
                messages.error(request, "You must have an assigned sector to create an irrigation request. Please contact an administrator or complete your membership profile.")
                return redirect('irrigation:irrigation_request_list')

            assigned_sector = request.user.membership_application.assigned_sector

            irrigation_request = form.save(commit=False)
            irrigation_request.farmer = request.user
            # Assign the user's existing assigned_sector to the request
            irrigation_request.sector = assigned_sector
            
            # Link request to membership (if it exists)
            if hasattr(request.user, 'membership_application'):
                membership = request.user.membership_application
                irrigation_request.membership = membership
                
                # Auto-fill location details from membership if available
                if hasattr(membership, 'farm_location') and membership.farm_location:
                    irrigation_request.farm_location = membership.farm_location
                
                if hasattr(membership, 'bufia_farm_location') and membership.bufia_farm_location:
                    irrigation_request.bufia_farm_location = membership.bufia_farm_location
            
            irrigation_request.save() # Save the WaterIrrigationRequest
            
            messages.success(request, "Your irrigation request has been submitted successfully. Please complete payment to proceed.")
            return redirect('create_irrigation_payment', irrigation_id=irrigation_request.pk)
    else:
        form = IrrigationRequestForm(user=request.user)
    
    return render(request, 'irrigation/request_form.html', {'form': form})

@login_required
def irrigation_request_list(request):
    """View for farmers to see their irrigation requests (excluding completed requests)"""
    requests = WaterIrrigationRequest.objects.filter(
        farmer=request.user
    ).exclude(
        status='completed'
    ).order_by('-request_date')
    return render(request, 'irrigation/request_list.html', {'requests': requests})

@login_required
def irrigation_request_detail(request, pk):
    """View for farmers to see details of a specific irrigation request"""
    irrigation_request = get_object_or_404(WaterIrrigationRequest, pk=pk, farmer=request.user)
    history = irrigation_request.history.all()
    return render(request, 'irrigation/request_detail.html', {
        'request': irrigation_request,
        'history': history
    })

@login_required
def irrigation_request_cancel(request, pk):
    """View for farmers to cancel their pending irrigation request"""
    irrigation_request = get_object_or_404(WaterIrrigationRequest, pk=pk, farmer=request.user)
    
    # Only allow cancellation of pending requests
    if irrigation_request.status != 'pending':
        messages.error(request, "Only pending requests can be cancelled.")
        return redirect('irrigation:irrigation_request_detail', pk=pk)
    
    if request.method == 'POST':
        irrigation_request.status = 'cancelled'
        irrigation_request.status_notes = "Cancelled by farmer"
        irrigation_request.save()  # This will trigger history creation in the save method
        
        messages.success(request, "Your irrigation request has been cancelled.")
        return redirect('irrigation:irrigation_request_list')
    
    return render(request, 'irrigation/request_cancel.html', {'request': irrigation_request})

# Water Tender Views
@login_required
@water_tender_required
def water_tender_irrigation_request_list(request):
    """View for water tenders to see irrigation requests in their assigned sectors"""
    
    # Get sectors managed by this water tender
    if request.user.is_water_tender():
        managed_sector_ids = request.user.managed_sectors.values_list('id', flat=True)
    else:
        # For admins/presidents, show all sectors
        managed_sector_ids = Sector.objects.values_list('id', flat=True)
    
    # Filter options
    status_filter = request.GET.get('status', '')
    sector_filter = request.GET.get('sector', '')
    date_filter = request.GET.get('date', '')
    
    # Base query: get requests for managed sectors
    requests = WaterIrrigationRequest.objects.filter(
        sector_id__in=managed_sector_ids
    ).select_related('farmer', 'sector', 'membership')
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    if sector_filter and sector_filter.isdigit():
        # Only filter by sector if it's one of the managed sectors
        sector_id = int(sector_filter)
        if sector_id in managed_sector_ids:
            requests = requests.filter(sector_id=sector_id)
    if date_filter:
        requests = requests.filter(requested_date=date_filter)
    
    # Filter out completed requests unless specifically requested
    if not status_filter or status_filter != 'completed':
        requests = requests.exclude(status='completed')
    
    # Get sectors for the filter dropdown (only show managed sectors)
    sectors = Sector.objects.filter(id__in=managed_sector_ids)
    
    # Count statistics for managed sectors
    pending_count = WaterIrrigationRequest.objects.filter(
        sector_id__in=managed_sector_ids, status='pending'
    ).count()
    approved_count = WaterIrrigationRequest.objects.filter(
        sector_id__in=managed_sector_ids, status='approved'
    ).count()
    completed_count = WaterIrrigationRequest.objects.filter(
        sector_id__in=managed_sector_ids, status='completed'
    ).count()
    
    context = {
        'requests': requests,
        'sectors': sectors,
        'status_filter': status_filter,
        'sector_filter': sector_filter,
        'date_filter': date_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'completed_count': completed_count,
        'is_water_tender': request.user.is_water_tender(),
    }
    
    return render(request, 'irrigation/water_tender_request_list.html', context)

@login_required
@water_tender_required
def water_tender_irrigation_request_detail(request, pk):
    """View for water tenders to see and update a specific irrigation request"""
    
    # Get sectors managed by this water tender
    if request.user.is_water_tender():
        managed_sector_ids = request.user.managed_sectors.values_list('id', flat=True)
        # Get request only if it's in a managed sector
        irrigation_request = get_object_or_404(
            WaterIrrigationRequest, 
            pk=pk, 
            sector_id__in=managed_sector_ids
        )
    else:
        # For admins/presidents, allow access to any request
        irrigation_request = get_object_or_404(WaterIrrigationRequest, pk=pk)
    
    history = irrigation_request.history.all()
    
    if request.method == 'POST':
        form = IrrigationRequestStatusForm(request.POST, instance=irrigation_request)
        if form.is_valid():
            irrigation_request = form.save(commit=False)
            irrigation_request.reviewed_by = request.user
            irrigation_request.review_date = timezone.now()
            irrigation_request.save()
            
            messages.success(request, f"Irrigation request has been updated to {irrigation_request.get_status_display()}.")
            return redirect('irrigation:water_tender_irrigation_request_list')
    else:
        form = IrrigationRequestStatusForm(instance=irrigation_request)
    
    return render(request, 'irrigation/water_tender_request_detail.html', {
        'request': irrigation_request,
        'history': history,
        'form': form
    })

# Admin Views
@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_list(request):
    """View for admins to see all irrigation requests"""
    status_filter = request.GET.get('status', '')
    sector_filter = request.GET.get('sector', '')
    date_filter = request.GET.get('date', '')
    
    requests = WaterIrrigationRequest.objects.all().select_related('farmer', 'sector', 'membership')
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    if sector_filter:
        requests = requests.filter(sector_id=sector_filter)
    if date_filter:
        requests = requests.filter(requested_date=date_filter)
    
    sectors = Sector.objects.all()
    
    # Count statistics
    pending_count = WaterIrrigationRequest.objects.filter(status='pending').count()
    approved_count = WaterIrrigationRequest.objects.filter(status='approved').count()
    completed_count = WaterIrrigationRequest.objects.filter(status='completed').count()
    
    context = {
        'requests': requests,
        'sectors': sectors,
        'status_filter': status_filter,
        'sector_filter': sector_filter,
        'date_filter': date_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'completed_count': completed_count,
    }
    
    return render(request, 'irrigation/admin_request_list.html', context)

@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_detail(request, pk):
    """View for admins to see and update a specific irrigation request"""
    irrigation_request = get_object_or_404(WaterIrrigationRequest, pk=pk)
    history = irrigation_request.history.all()
    
    if request.method == 'POST':
        form = IrrigationRequestStatusForm(request.POST, instance=irrigation_request)
        if form.is_valid():
            irrigation_request = form.save(commit=False)
            irrigation_request.reviewed_by = request.user
            irrigation_request.review_date = timezone.now()
            irrigation_request.save()
            
            messages.success(request, f"Irrigation request has been updated to {irrigation_request.get_status_display()}.")
            return redirect('irrigation:admin_irrigation_request_list')
    else:
        form = IrrigationRequestStatusForm(instance=irrigation_request)
    
    return render(request, 'irrigation/admin_request_detail.html', {
        'request': irrigation_request,
        'history': history,
        'form': form
    })

@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_create(request):
    """View for admins to create irrigation requests for walk-in customers"""
    if request.method == 'POST':
        form = AdminIrrigationRequestForm(request.POST)
        if form.is_valid():
            irrigation_request = form.save(commit=False)
            irrigation_request.save()
            
            messages.success(request, f"Irrigation request created successfully for {irrigation_request.farmer.get_full_name()}.")
            return redirect('irrigation:admin_irrigation_request_list')
    else:
        form = AdminIrrigationRequestForm()
    
    return render(request, 'irrigation/admin_request_create.html', {
        'form': form
    })

@login_required
@user_passes_test(is_admin_or_president)
def admin_irrigation_request_history(request):
    """View for admins to see history of all irrigation requests"""
    history_entries = IrrigationRequestHistory.objects.all().select_related('request', 'changed_by', 'request__farmer').order_by('-changed_date')
    
    # Filter options
    status_filter = request.GET.get('status', '')
    if status_filter:
        history_entries = history_entries.filter(status=status_filter)
    
    # Date range filtering
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if from_date:
        history_entries = history_entries.filter(changed_date__date__gte=from_date)
    if to_date:
        history_entries = history_entries.filter(changed_date__date__lte=to_date)
    
    return render(request, 'irrigation/admin_request_history.html', {
        'history_entries': history_entries,
        'status_filter': status_filter,
        'from_date': from_date,
        'to_date': to_date,
    })

@login_required
def user_irrigation_request_history(request):
    """View for users to see complete history of all their irrigation requests"""
    # Redirect admin users to admin history page
    if request.user.is_superuser or request.user.is_staff:
        return redirect('irrigation:admin_irrigation_request_history')
    
    # Get all irrigation requests for the user, ordered by most recent first
    irrigation_requests = WaterIrrigationRequest.objects.filter(
        farmer=request.user
    ).select_related('sector').order_by('-request_date', '-requested_date')
    
    # Status filtering
    status_filter = request.GET.get('status', '')
    if status_filter:
        irrigation_requests = irrigation_requests.filter(status=status_filter)
    
    # Date range filtering
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if from_date:
        irrigation_requests = irrigation_requests.filter(request_date__gte=from_date)
    if to_date:
        irrigation_requests = irrigation_requests.filter(request_date__lte=to_date)
    
    # Get status choices for filter dropdown
    status_choices = WaterIrrigationRequest.STATUS_CHOICES
    
    return render(request, 'irrigation/user_request_history.html', {
        'irrigation_requests': irrigation_requests,
        'from_date': from_date,
        'to_date': to_date,
        'status_filter': status_filter,
        'status_choices': status_choices,
    })
