from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserForm, ProfileForm
from .models import CustomUser, MembershipApplication, Sector
from machines.models import Machine, Rental, Maintenance, RiceMillAppointment
from irrigation.models import WaterIrrigationRequest
from django.utils import timezone
import datetime
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
import csv
from django.urls import reverse
from notifications.models import UserNotification

User = get_user_model()

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'users/home.html')

@login_required
def dashboard(request):
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    verified_users = User.objects.filter(is_verified=True).count()
    pending_verification = User.objects.filter(membership_form_submitted=True, is_verified=False).count()
    
    # Machine statistics
    total_machines = Machine.objects.count()
    available_machines = Machine.objects.filter(status='available').count()
    active_rentals = Rental.objects.filter(status='approved').count()
    
    # Rice Mill Scheduling statistics - removed
    """
    total_schedules = RiceMillSchedule.objects.count()
    pending_schedules = RiceMillSchedule.objects.filter(status='pending').count()
    recent_schedules = RiceMillSchedule.objects.order_by('-start_time')[:5]
    """
    
    # Recent rentals
    recent_rentals = Rental.objects.order_by('-created_at')[:5]
    
    # Monthly statistics for graph (last 12 months)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    import json
    
    current_date = timezone.now()
    twelve_months_ago = current_date - datetime.timedelta(days=365)
    
    # Get monthly rental counts
    monthly_rentals = Rental.objects.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Get monthly user registrations
    monthly_users = User.objects.filter(
        date_joined__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('date_joined')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Get monthly irrigation requests
    monthly_irrigation = WaterIrrigationRequest.objects.filter(
        requested_date__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('requested_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Get monthly maintenance records
    monthly_maintenance = Maintenance.objects.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Get monthly rice mill appointments
    monthly_ricemill = RiceMillAppointment.objects.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Prepare data for last 12 months
    months = []
    rental_data = []
    user_data = []
    irrigation_data = []
    maintenance_data = []
    ricemill_data = []
    
    for i in range(12):
        month_date = current_date - datetime.timedelta(days=30 * (11 - i))
        months.append(month_date.strftime('%b'))
        
        # Find rental count for this month
        rental_count = 0
        for item in monthly_rentals:
            if item['month'].month == month_date.month and item['month'].year == month_date.year:
                rental_count = item['count']
                break
        rental_data.append(rental_count)
        
        # Find user count for this month
        user_count = 0
        for item in monthly_users:
            if item['month'].month == month_date.month and item['month'].year == month_date.year:
                user_count = item['count']
                break
        user_data.append(user_count)
        
        # Find irrigation count for this month
        irrigation_count = 0
        for item in monthly_irrigation:
            if item['month'].month == month_date.month and item['month'].year == month_date.year:
                irrigation_count = item['count']
                break
        irrigation_data.append(irrigation_count)
        
        # Find maintenance count for this month
        maintenance_count = 0
        for item in monthly_maintenance:
            if item['month'].month == month_date.month and item['month'].year == month_date.year:
                maintenance_count = item['count']
                break
        maintenance_data.append(maintenance_count)
        
        # Find rice mill count for this month
        ricemill_count = 0
        for item in monthly_ricemill:
            if item['month'].month == month_date.month and item['month'].year == month_date.year:
                ricemill_count = item['count']
                break
        ricemill_data.append(ricemill_count)
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'verified_users': verified_users,
        'pending_verification': pending_verification,
        'total_machines': total_machines,
        'available_machines': available_machines,
        'active_rentals': active_rentals,
        'recent_rentals': recent_rentals,
        # Graph data
        'graph_months': json.dumps(months),
        'graph_rentals': json.dumps(rental_data),
        'graph_users': json.dumps(user_data),
        'graph_irrigation': json.dumps(irrigation_data),
        'graph_maintenance': json.dumps(maintenance_data),
        'graph_ricemill': json.dumps(ricemill_data),
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def profile(request):
    # Get the user's membership application if it exists
    membership_application = None
    try:
        membership_application = request.user.membership_application
    except:
        # Membership application doesn't exist yet
        pass
    
    return render(request, 'users/profile.html', {
        'membership_application': membership_application
    })

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save() # Only saves CustomUser fields now
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
        
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def view_membership_info(request, user_id=None):
    """Displays detailed membership application information for a specific user or the logged-in user."""
    target_user = None
    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
        # Ensure only admins can view other users' full membership info this way
        if not request.user.is_superuser and request.user != target_user:
            messages.error(request, "You do not have permission to view this user's membership information.")
            return redirect('dashboard') # Or some other appropriate page
    else:
        target_user = request.user # Default to logged-in user if no id is provided

    membership_application = None
    try:
        membership_application = target_user.membership_application
    except MembershipApplication.DoesNotExist:
        pass 
    except AttributeError: 
        pass 

    return render(request, 'users/membership_info.html', {
        'membership_application': membership_application,
        'viewed_user': target_user, # Pass the user whose info is being viewed
        # 'user': request.user # Already available in templates by default as 'user'
    })

@login_required
def user_list(request):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    users = User.objects.all()
    pending_verification = users.filter(membership_form_submitted=True, is_verified=False)
    
    context = {
        'users': users,
        'pending_verification': pending_verification,
    }
    
    return render(request, 'users/user_list.html', context)

@login_required
def create_user(request):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        # Pre-validation check for username uniqueness
        username = request.POST.get('username')
        if username and User.objects.filter(username=username).exists():
            form.add_error('username', f'Username "{username}" is already taken. Please choose a different username.')
            return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})
        
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'User {user.username} created successfully.')
                return redirect('user_list')
            except Exception as e:
                # Handle any other errors that might occur
                messages.error(request, f'Error creating user: {str(e)}')
        # If form is not valid, it will be rendered with errors below
    else:
        form = UserForm()
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})

@login_required
def edit_user(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user_to_edit = get_object_or_404(User, pk=pk)
    membership_app = None
    try:
        membership_app = MembershipApplication.objects.get(user=user_to_edit)
    except MembershipApplication.DoesNotExist:
        pass # It's okay if it doesn't exist yet, we might create it

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            updated_user = form.save(commit=False) # Don't save yet, might need to link membership
            
            # Handle assigned_sector
            assigned_sector_id = request.POST.get('assigned_sector')
            if assigned_sector_id:
                try:
                    chosen_sector = Sector.objects.get(pk=assigned_sector_id)
                    if membership_app:
                        membership_app.assigned_sector = chosen_sector
                    else:
                        # Create MembershipApplication if it doesn't exist and a sector is chosen
                        membership_app = MembershipApplication.objects.create(
                            user=updated_user,
                            assigned_sector=chosen_sector,
                            is_current=True, # Assuming default if created here
                            submission_date=user_to_edit.membership_form_date or timezone.now().date(),
                            # Add other defaults if necessary, or ensure they are nullable
                        )
                    membership_app.save()
                except Sector.DoesNotExist:
                    messages.warning(request, 'The selected sector does not exist. User sector not changed.')
            elif membership_app: # If no sector is chosen (e.g., "---"), and app exists, clear it
                membership_app.assigned_sector = None
                membership_app.save()

            updated_user.save() # Now save the user
            messages.success(request, f'User {updated_user.username} updated successfully.')
            return redirect('members_masterlist')
    else:
        form = UserForm(instance=user_to_edit)
    
    sectors = Sector.objects.all().order_by('name')
    current_assigned_sector = membership_app.assigned_sector if membership_app else None
    
    return render(request, 'users/user_form.html', {
        'form': form, 
        'action': 'Edit', 
        'user_to_edit': user_to_edit, # Pass the user being edited for context in template
        'sectors': sectors,
        'current_assigned_sector': current_assigned_sector
    })

@login_required
def verify_user(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        # Get the assigned sector
        assigned_sector_id = request.POST.get('assigned_sector')
        assigned_sector = None
        if assigned_sector_id:
            try:
                assigned_sector = Sector.objects.get(pk=assigned_sector_id)
            except Sector.DoesNotExist:
                messages.warning(request, 'The selected sector does not exist. Verification completed without sector assignment.')
        
        # Update user verification status
        user.is_verified = True
        user.membership_approved_date = datetime.date.today()
        user.membership_rejected_reason = ''
        user.save()
        
        # Update or create membership application status
        membership_app, created = MembershipApplication.objects.get_or_create(
            user=user,
            defaults={
                'is_current': True,
                'submission_date': user.membership_form_date or datetime.date.today(),
            }
        )
        
        # Update the application status
        membership_app.is_approved = True
        membership_app.is_rejected = False
        membership_app.review_date = datetime.date.today()
        membership_app.reviewed_by = request.user
        
        # Assign the sector if provided
        if assigned_sector:
            membership_app.assigned_sector = assigned_sector
        
        membership_app.save()
        
        # Create notification for approved membership
        try:
            UserNotification.objects.create(
                user=user,
                notification_type='membership_approved',
                message=f'Your membership has been approved on {datetime.date.today().strftime("%B %d, %Y")}.'
            )
        except Exception as e:
            # Non-fatal if notifications fail
            print(f"Notification creation failed: {e}")

        messages.success(request, f'User {user.username} has been verified successfully.')
        return redirect('user_list')
    
    # Get all sectors for the dropdown
    sectors = Sector.objects.all().order_by('name')
    
    return render(request, 'users/user_verify_confirm.html', {
        'user': user,
        'sectors': sectors
    })

@login_required
def reject_verification(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '')
        
        # Update user verification status
        user.is_verified = False
        user.membership_form_submitted = False  # Reset to remove from pending list
        user.membership_rejected_reason = reason
        user.save()
        
        # Update or create membership application status
        membership_app, created = MembershipApplication.objects.get_or_create(
            user=user,
            defaults={
                'is_current': True,
                'submission_date': user.membership_form_date or datetime.date.today(),
            }
        )
        
        # Update the application status
        membership_app.is_approved = False
        membership_app.is_rejected = True
        membership_app.rejection_reason = reason
        membership_app.review_date = datetime.date.today()
        membership_app.reviewed_by = request.user
        membership_app.save()
        
        # Create notification for rejected membership
        try:
            UserNotification.objects.create(
                user=user,
                notification_type='membership_rejected',
                message=f'Your membership verification was rejected. Reason: {reason or "No reason provided"}.'
            )
        except Exception as e:
            print(f"Notification creation failed: {e}")

        messages.success(request, f'User {user.username} verification has been rejected.')
        return redirect('user_list')
    
    return render(request, 'users/user_reject_form.html', {'user': user})

@login_required
def delete_user(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully.')
        return redirect('members_masterlist')
    return render(request, 'users/user_confirm_delete.html', {'user': user})

@login_required
def update_profile_photo(request):
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        user = request.user
        # Handle profile photo upload logic here
        # This is a placeholder - you would need to add ImageField to CustomUser model first
        messages.success(request, 'Profile photo updated successfully.')
        return redirect('profile')
    return redirect('profile')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session to prevent logging out
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('profile')
    return redirect('profile')

@login_required
def submit_membership_form(request):
    # Get existing membership application if it exists
    try:
        existing_application = MembershipApplication.objects.get(user=request.user)
    except MembershipApplication.DoesNotExist:
        existing_application = None
    
    # Get all sectors for the dropdown
    sectors = Sector.objects.all().order_by('name')
    
    if request.method == 'POST':
        user = request.user
        
        # Process basic user information
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        
        # Compile full address from form components
        address_parts = []
        sitio = request.POST.get('sitio', '').strip()
        barangay = request.POST.get('barangay', '').strip()
        city = request.POST.get('city', '').strip()
        province = request.POST.get('province', '').strip()
        
        if sitio:
            address_parts.append(sitio)
        if barangay:
            address_parts.append(barangay)
        if city:
            address_parts.append(city)
        if province:
            address_parts.append(province)
        
        user.address = ", ".join(address_parts)
        
        # Parse form data
        try:
            farm_size = float(request.POST.get('farm_size', 0))
        except (ValueError, TypeError):
            farm_size = 0
            
        try:
            birth_date = datetime.datetime.strptime(request.POST.get('birthdate', ''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            birth_date = None
        
        # Check if a membership application already exists for this user
        try:
            # Try to get existing application
            application = MembershipApplication.objects.get(user=user)
            
            # Update existing application
            application.is_current = True
            application.middle_name = request.POST.get('middle_name', '')
            application.gender = request.POST.get('gender', '')
            application.birth_date = birth_date
            application.civil_status = request.POST.get('civil_status', '')
            application.education = request.POST.get('education', '')
            
            # Address details
            application.sitio = sitio
            application.barangay = barangay
            application.city = city
            application.province = province
            
            # Farm information
            application.ownership_type = request.POST.get('ownership', '')
            application.land_owner = request.POST.get('land_owner', '')
            application.farm_manager = request.POST.get('farm_manager', '')
            application.farm_location = request.POST.get('farm_location', '')
            application.bufia_farm_location = request.POST.get('bufia_farm_location', '')
            application.farm_size = farm_size
            
            # Update submission date
            application.submission_date = datetime.date.today()
            
            # Save the updated application
            application.save()
            
        except MembershipApplication.DoesNotExist:
            # Create new application if one doesn't exist
            application = MembershipApplication.objects.create(
                user=user,
                # Personal information
                middle_name=request.POST.get('middle_name', ''),
                gender=request.POST.get('gender', ''),
                birth_date=birth_date,
                civil_status=request.POST.get('civil_status', ''),
                education=request.POST.get('education', ''),
                
                # Address details
                sitio=sitio,
                barangay=barangay,
                city=city,
                province=province,
                
                # Farm information
                ownership_type=request.POST.get('ownership', ''),
                land_owner=request.POST.get('land_owner', ''),
                farm_manager=request.POST.get('farm_manager', ''),
                farm_location=request.POST.get('farm_location', ''),
                bufia_farm_location=request.POST.get('bufia_farm_location', ''),
                farm_size=farm_size,
            )
        
        # Handle payment method (with error handling for missing fields)
        payment_method = request.POST.get('payment_method', 'face_to_face')
        try:
            application.payment_method = payment_method
            if payment_method == 'face_to_face':
                application.payment_status = 'pending'
        except AttributeError:
            # Fields don't exist yet, skip payment handling
            pass
        
        application.save()
        
        # Update membership status fields on user model
        user.membership_form_submitted = True
        user.membership_form_date = datetime.date.today()
        user.is_verified = False  # Reset verification status if resubmitting
        user.membership_rejected_reason = ''  # Clear any previous rejection reason
        
        # Save the user changes
        user.save()
        
        # Create notification for user about form submission
        from notifications.models import UserNotification
        
        # Redirect based on payment method
        try:
            if payment_method == 'online' and hasattr(application, 'payment_method'):
                # Notify user about form submission (payment pending)
                UserNotification.objects.create(
                    user=user,
                    notification_type='membership',
                    message='Your membership application has been submitted. Please complete the payment to proceed.',
                    related_object_id=application.pk
                )
                messages.success(request, 'Your membership application has been submitted. Please complete the payment to proceed.')
                return redirect('create_membership_payment', membership_id=application.pk)
            else:
                # Notify user about form submission (face-to-face payment)
                UserNotification.objects.create(
                    user=user,
                    notification_type='membership',
                    message='Your membership application has been submitted successfully. Please present the verification slip and ₱500 membership fee to a BUFIA administrator for approval.',
                    related_object_id=application.pk
                )
                
                # Notify admins about new membership application
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    UserNotification.objects.create(
                        user=admin,
                        notification_type='membership',
                        message=f'New membership application submitted by {user.get_full_name()} (Face-to-face payment).',
                        related_object_id=application.pk
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
                            message=f'New membership application submitted by {user.get_full_name()} (Face-to-face payment).',
                            related_object_id=application.pk
                        )
                except Exception:
                    pass  # Silently fail if user not found
                
                messages.success(request, 'Your membership application has been submitted successfully. Please print the verification slip and present it to a BUFIA administrator for approval along with the ₱500 membership fee.')
                return redirect('membership_slip')
        except Exception as e:
            # Fallback if payment system not ready
            messages.success(request, 'Your membership application has been submitted successfully. Please print the verification slip and present it to a BUFIA administrator for approval.')
            return redirect('membership_slip')
    
    # GET request - show the form
    context = {
        'membership': existing_application,
        'sectors': sectors,
    }
    return render(request, 'users/submit_membership_form.html', context)

@login_required
def membership_slip(request):
    """View for displaying printable membership slip after form submission"""
    user = request.user
    
    # Get the user's current membership application
    membership = None
    try:
        # First try to get by is_current flag
        membership = MembershipApplication.objects.filter(user=user, is_current=True).latest('submission_date')
    except MembershipApplication.DoesNotExist:
        try:
            # If no current application found, get the most recent one
            membership = MembershipApplication.objects.filter(user=user).latest('submission_date')
            # Mark this as the current application
            if membership:
                membership.is_current = True
                membership.save()
        except MembershipApplication.DoesNotExist:
            membership = None
    
    # Enable debug info if there's an issue displaying data
    debug = request.GET.get('debug') == '1'
    
    if membership and debug:
        print(f"DEBUG - Farm Location: '{membership.farm_location}'")
        print(f"DEBUG - Farm Size: '{membership.farm_size}'")
        print(f"DEBUG - BUFIA Location: '{membership.bufia_farm_location}'")
    
    context = {
        'user': user,
        'membership': membership,
        'debug': debug,
    }
    
    return render(request, 'users/membership_slip.html', context)

def is_admin_or_president(user):
    """Check if user is admin or president"""
    return user.is_superuser

@login_required
@user_passes_test(is_admin_or_president)
def members_masterlist(request):
    """Display a masterlist of all members organized by sector"""
    
    verified_members = MembershipApplication.objects.filter(
        user__is_verified=True
    ).select_related('user', 'assigned_sector') # Removed 'sector' as it might be ambiguous
    
    # Create default sectors if none exist (Consider moving this to a management command or a one-time setup)
    if Sector.objects.count() == 0:
        default_sectors = [
            {'name': 'Sector 1', 'description': 'First sector of BUFIA'},
            {'name': 'Sector 2', 'description': 'Second sector of BUFIA'},
            {'name': 'Sector 3', 'description': 'Third sector of BUFIA'},
            {'name': 'Sector 4', 'description': 'Fourth sector of BUFIA'},
        ]
        for sector_data in default_sectors:
            Sector.objects.create(**sector_data)
            
    all_sectors = Sector.objects.all().order_by('name') # Changed variable name for clarity
    
    sectors_with_members_list = [] # Changed variable name for clarity
    for sector_obj in all_sectors: # Changed variable name for clarity
        sector_members = verified_members.filter(assigned_sector=sector_obj)
        sectors_with_members_list.append({
            'id': sector_obj.id,
            'name': sector_obj.name,
            'description': sector_obj.description,
            'members': sector_members
        })
    
    unassigned_members = verified_members.filter(assigned_sector__isnull=True)
    if unassigned_members.exists():
        sectors_with_members_list.append({
            'id': 'unassigned',
            'name': 'Unassigned',
            'description': 'Members not assigned to any sector',
            'members': unassigned_members
        })
    
    active_sector_id = request.GET.get('sector_id', None)
    # Validate if active_sector_id is a valid integer if it's not 'unassigned'
    if active_sector_id and active_sector_id != 'unassigned':
        try:
            active_sector_id = int(active_sector_id)
        except ValueError:
            active_sector_id = None # Invalid sector_id, default to all

    context = {
        'all_verified_members': verified_members, # For the 'All Members' tab
        'sectors_data': sectors_with_members_list, # For the sector-specific tabs
        'active_sector_id': active_sector_id # To activate the correct tab
    }
    
    return render(request, 'users/members_masterlist.html', context)

@login_required
@user_passes_test(is_admin_or_president)
def export_members_csv(request):
    """Export members to CSV with specific application details."""
    sector_id = request.GET.get('sector', None)
    
    # Determine filename based on sector
    if sector_id and sector_id != 'all':
        if sector_id == 'unassigned':
            filename = f'bufia_members_unassigned_{timezone.now().strftime("%Y%m%d")}.csv'
        else:
            try:
                sector = Sector.objects.get(id=int(sector_id))
                filename = f'bufia_members_{sector.name.replace(" ", "_")}_{timezone.now().strftime("%Y%m%d")}.csv'
            except (Sector.DoesNotExist, ValueError):
                filename = f'bufia_members_{timezone.now().strftime("%Y%m%d")}.csv'
    else:
        filename = f'bufia_members_all_{timezone.now().strftime("%Y%m%d")}.csv'
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
    
    writer = csv.writer(response)
    # Simplified header for member list
    writer.writerow([
        'NO.',
        'NAME OF FARMER',
        'SECTOR',
    ])
    
    # Query for MembershipApplication, focusing on those linked to verified users
    applications = MembershipApplication.objects.filter(
        user__is_verified=True
    ).select_related('user', 'assigned_sector').order_by('user__last_name', 'user__first_name')
    
    # Filter by sector if specified
    if sector_id and sector_id != 'all':
        if sector_id == 'unassigned':
            applications = applications.filter(assigned_sector__isnull=True)
        else:
            try:
                applications = applications.filter(assigned_sector_id=int(sector_id))
            except ValueError:
                pass  # Invalid sector_id, export all

    for index, app in enumerate(applications, start=1):
        full_name = f"{app.user.last_name}, {app.user.first_name}"
        if app.middle_name:
            full_name += f" {app.middle_name}"
        
        writer.writerow([
            index,
            full_name,
            app.assigned_sector.name if app.assigned_sector else 'Unassigned',
        ])
    
    return response

@login_required
@user_passes_test(is_admin_or_president)
def export_members_pdf(request):
    """Export members to PDF using ReportLab."""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    import os
    from django.conf import settings
    
    sector_id = request.GET.get('sector', None)
    
    # Get members based on sector filter
    applications = MembershipApplication.objects.filter(
        user__is_verified=True
    ).select_related('user', 'assigned_sector').order_by('user__last_name', 'user__first_name')
    
    sector_name = "All Sectors"
    
    # Filter by sector if specified
    if sector_id and sector_id != 'all':
        if sector_id == 'unassigned':
            applications = applications.filter(assigned_sector__isnull=True)
            sector_name = "Unassigned Members"
        else:
            try:
                sector = Sector.objects.get(id=int(sector_id))
                applications = applications.filter(assigned_sector_id=int(sector_id))
                sector_name = sector.name
            except (Sector.DoesNotExist, ValueError):
                pass  # Invalid sector_id, export all
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#019d66'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER
    )
    
    # Add logo at top right
    logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'img', 'logo.png')
    if not os.path.exists(logo_path):
        # Try alternative path
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    
    if os.path.exists(logo_path):
        # Create a table to position logo on the right
        logo_img = Image(logo_path, width=1*inch, height=1*inch)
        logo_table = Table([[Paragraph("", title_style), logo_img]], colWidths=[5*inch, 1.5*inch])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(logo_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Add title
    elements.append(Paragraph("BUFIA", title_style))
    elements.append(Paragraph("Members Masterlist", subtitle_style))
    elements.append(Paragraph(sector_name, info_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Add info
    date_str = timezone.now().strftime('%B %d, %Y')
    info_text = f"Generated: {date_str} | Total Members: {applications.count()}"
    elements.append(Paragraph(info_text, info_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Prepare table data
    table_data = [['NO.', 'NAME OF FARMER', 'SECTOR']]
    
    for index, app in enumerate(applications, start=1):
        full_name = f"{app.user.last_name}, {app.user.first_name}"
        if app.middle_name:
            full_name += f" {app.middle_name}"
        
        sector_display = app.assigned_sector.name if app.assigned_sector else 'Unassigned'
        table_data.append([str(index), full_name, sector_display])
    
    # Create table
    table = Table(table_data, colWidths=[0.8*inch, 3.5*inch, 2*inch])
    
    # Style the table
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#019d66')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center NO. column
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),   # Left align other columns
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#017a4f')),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add footer
    footer_text = f"Total: {applications.count()} member{'s' if applications.count() != 1 else ''}"
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#019d66'),
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Determine filename
    filename = f'bufia_members_{sector_name.replace(" ", "_")}_{timezone.now().strftime("%Y%m%d")}.pdf'
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
@user_passes_test(is_admin_or_president)
def sector_list(request):
    """View for listing and managing all sectors"""
    sectors = Sector.objects.all().order_by('name')
    
    context = {
        'sectors': sectors,
    }
    
    return render(request, 'users/sector_list.html', context)

@login_required
@user_passes_test(is_admin_or_president)
def create_sector(request):
    """View for creating a new sector"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, 'Sector name is required.')
            return redirect('create_sector')
        
        sector = Sector.objects.create(
            name=name,
            description=description
        )
        
        messages.success(request, f'Sector "{sector.name}" created successfully.')
        return redirect('sector_list')
    
    return render(request, 'users/sector_form.html', {'action': 'Create'})

@login_required
@user_passes_test(is_admin_or_president)
def edit_sector(request, pk):
    """View for editing an existing sector"""
    sector = get_object_or_404(Sector, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, 'Sector name is required.')
            return redirect('edit_sector', pk=pk)
        
        sector.name = name
        sector.description = description
        sector.save()
        
        messages.success(request, f'Sector "{sector.name}" updated successfully.')
        return redirect('sector_list')
    
    return render(request, 'users/sector_form.html', {
        'sector': sector, 
        'action': 'Edit'
    })

@login_required
@user_passes_test(is_admin_or_president)
def delete_sector(request, pk):
    """View for deleting a sector"""
    sector = get_object_or_404(Sector, pk=pk)
    
    if request.method == 'POST':
        name = sector.name
        
        # Check if sector has members or water tenders associated
        has_members = sector.members.exists() or sector.assigned_members.exists()
        has_water_tenders = sector.water_tenders.exists()
        
        if has_members or has_water_tenders:
            messages.error(request, 
                f'Cannot delete sector "{name}" because it has members or water tenders associated with it. '
                'Reassign them before deleting this sector.')
            return redirect('sector_list')
            
        sector.delete()
        messages.success(request, f'Sector "{name}" deleted successfully.')
        return redirect('sector_list')
    
    return render(request, 'users/sector_confirm_delete.html', {'sector': sector})

@login_required
@user_passes_test(is_admin_or_president)
def verification_requests(request):
    """View for listing all pending verification requests"""
    pending_users = User.objects.filter(
        membership_form_submitted=True, 
        is_verified=False
    ).order_by('membership_form_date')
    
    context = {
        'pending_users': pending_users,
    }
    
    return render(request, 'users/verification_requests.html', context)

@login_required
@user_passes_test(is_admin_or_president)
def get_user_profile_data(request, user_id):
    """
    API endpoint to fetch detailed user profile data.
    """
    try:
        user = User.objects.select_related(
            'membership_application', 
            'membership_application__assigned_sector',
            'membership_application__reviewed_by' # Eager load reviewed_by
        ).prefetch_related(
            'managed_sectors' # For water tenders
        ).get(pk=user_id)
        
        membership_app = getattr(user, 'membership_application', None)

        data = {
            'id': user.id,
            'username': user.username,
            'fullName': user.get_full_name() or user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'middleName': membership_app.middle_name if membership_app else 'N/A',
            'email': user.email or 'Not provided',
            'role': user.get_role_display(),
            'initials': (f"{user.first_name[0] if user.first_name else ''}{user.last_name[0] if user.last_name else ''}".upper() 
                         or (user.username[0].upper() if user.username else 'U')),
            'phoneNumber': user.phone_number or 'Not provided',
            'userAddress': user.address or 'Not provided', # Address from CustomUser model
            'dateJoined': user.date_joined.strftime("%B %d, %Y") if user.date_joined else 'N/A',
            'lastLogin': user.last_login.strftime("%B %d, %Y at %I:%M %p") if user.last_login else 'Never',
            'isActive': user.is_active,
            'statusText': 'Active' if user.is_active else 'Inactive',
            
            # Verification & Membership Status
            'isVerified': user.is_verified,
            'isMembershipFormSubmitted': user.membership_form_submitted,
            'membershipFormDate': user.membership_form_date.strftime("%B %d, %Y") if user.membership_form_date else 'N/A',
            'membershipApprovedDate': user.membership_approved_date.strftime("%B %d, %Y") if user.membership_approved_date else 'N/A',
            'membershipRejectedReasonUser': user.membership_rejected_reason or 'N/A',
            'verificationStatusText': 'Not Verified',
            'verificationStatusClass': 'text-secondary',

            # Links
            'editUrl': reverse('edit_user', args=[user.id]),
            'verifyUrl': reverse('verify_user', args=[user.id]) if not user.is_verified and user.membership_form_submitted else None,
            'rejectUrl': reverse('reject_verification', args=[user.id]) if not user.is_verified and user.membership_form_submitted else None,
            'deleteUrl': reverse('delete_user', args=[user.id]),
        }

        if user.is_verified:
            data['verificationStatusText'] = 'Verified'
            data['verificationStatusClass'] = 'text-success'
        elif user.membership_form_submitted:
            data['verificationStatusText'] = 'Pending Verification'
            data['verificationStatusClass'] = 'text-primary'
        else:
            data['verificationStatusText'] = 'Not Submitted'
            data['verificationStatusClass'] = 'text-warning'

        if user.is_water_tender():
            data['managedSectors'] = list(user.managed_sectors.values_list('name', flat=True))

        # Membership Application Details
        if membership_app:
            data.update({
                'ma_submissionDate': membership_app.submission_date.strftime("%B %d, %Y") if membership_app.submission_date else 'N/A',
                'ma_isCurrent': membership_app.is_current,
                'ma_isApproved': membership_app.is_approved,
                'ma_isRejected': membership_app.is_rejected,
                'ma_assignedSector': membership_app.assigned_sector.name if membership_app.assigned_sector else 'N/A',
                'ma_gender': membership_app.get_gender_display() if membership_app.gender else 'N/A',
                'ma_birthDate': membership_app.birth_date.strftime("%B %d, %Y") if membership_app.birth_date else 'N/A',
                'ma_age': membership_app.age if membership_app.birth_date else 'N/A',
                'ma_placeOfBirth': membership_app.place_of_birth or 'N/A',
                'ma_civilStatus': membership_app.get_civil_status_display() if membership_app.civil_status else 'N/A',
                'ma_education': membership_app.get_education_display() if membership_app.education else 'N/A',
                'ma_fullAddress': f"{membership_app.sitio or ''}, {membership_app.barangay or ''}, {membership_app.city or ''}, {membership_app.province or ''}".strip(", ") or 'N/A',
                'ma_sitio': membership_app.sitio or 'N/A',
                'ma_barangay': membership_app.barangay or 'N/A',
                'ma_city': membership_app.city or 'N/A',
                'ma_province': membership_app.province or 'N/A',
                'ma_isTiller': 'Yes' if membership_app.is_tiller else 'No',
                'ma_lotNumber': membership_app.lot_number or 'N/A',
                'ma_ownershipType': membership_app.get_ownership_type_display() if membership_app.ownership_type else 'N/A',
                'ma_landOwner': membership_app.land_owner or 'N/A',
                'ma_farmManager': membership_app.farm_manager or 'N/A',
                'ma_farmLocation': membership_app.farm_location or 'N/A',
                'ma_bufiaFarmLocation': membership_app.bufia_farm_location or 'N/A',
                'ma_farmSize': str(membership_app.farm_size) if membership_app.farm_size is not None else 'N/A',
                'ma_reviewedBy': membership_app.reviewed_by.get_full_name() or membership_app.reviewed_by.username if membership_app.reviewed_by else 'N/A',
                'ma_reviewDate': membership_app.review_date.strftime("%B %d, %Y") if membership_app.review_date else 'N/A',
                'ma_rejectionReason': membership_app.rejection_reason or 'N/A'
            })
        else:
            # Add placeholders for MA fields if no application exists, to prevent JS errors
            ma_fields = [
                'ma_submissionDate', 'ma_isCurrent', 'ma_isApproved', 'ma_isRejected',
                'ma_assignedSector', 'ma_gender', 'ma_birthDate', 'ma_age', 'ma_placeOfBirth',
                'ma_civilStatus', 'ma_education', 'ma_fullAddress', 'ma_sitio', 'ma_barangay',
                'ma_city', 'ma_province', 'ma_isTiller', 'ma_lotNumber', 'ma_ownershipType',
                'ma_landOwner', 'ma_farmManager', 'ma_farmLocation', 'ma_bufiaFarmLocation',
                'ma_farmSize', 'ma_reviewedBy', 'ma_reviewDate', 'ma_rejectionReason'
            ]
            for field in ma_fields:
                data[field] = 'N/A' # Or specific default like False for booleans if needed

        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        # Log the exception for server-side debugging
        print(f"Error in get_user_profile_data: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'An unexpected error occurred. Please check server logs.', 'details': str(e)}, status=500)
