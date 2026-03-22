from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.urls import reverse
from datetime import date

from .models_operator import Operator, OperatorTask
from .models import Machine
from users.models import CustomUser


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_list(request):
    """List all operators - uses the operator overview template"""
    # Redirect to operator overview which serves as the list page
    return redirect('machines:operator_overview')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_detail(request, operator_id):
    """View operator dashboard - redirects to operator dashboard with admin view"""
    return redirect(f"{reverse('machines:operator_dashboard')}?operator_id={operator_id}")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_add(request):
    """Add new operator - simplified version using User model"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
            
        if not first_name:
            errors.append('First name is required.')
            
        if not last_name:
            errors.append('Last name is required.')
        
        # Check if username already exists
        if username and CustomUser.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" already exists. Please choose a different username.')
        
        # Check if email already exists (if provided)
        if email and CustomUser.objects.filter(email=email).exists():
            errors.append(f'Email "{email}" is already registered. Please use a different email.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                # Create user with operator role
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email if email else '',
                    role=CustomUser.OPERATOR,
                    is_staff=True,
                    is_active=True
                )
                
                messages.success(
                    request, 
                    f'Operator "{user.get_full_name()}" ({username}) created successfully! '
                    f'They can now log in and access the operator dashboard.'
                )
                return redirect('machines:operator_overview')
                
            except Exception as e:
                messages.error(request, f'Error creating operator: {str(e)}')
    
    context = {
        'title': 'Add New Operator',
    }
    return render(request, 'machines/admin/operator_add.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_edit(request, operator_id):
    """Edit operator information"""
    operator = get_object_or_404(CustomUser, id=operator_id, role=CustomUser.OPERATOR)
    
    if request.method == 'POST':
        operator.first_name = request.POST.get('first_name', '')
        operator.last_name = request.POST.get('last_name', '')
        operator.email = request.POST.get('email', '')
        operator.is_active = request.POST.get('is_active') == 'on'
        
        try:
            operator.save()
            messages.success(request, 'Operator updated successfully.')
            return redirect('machines:operator_overview')
        except Exception as e:
            messages.error(request, f'Error updating operator: {str(e)}')
    
    context = {
        'operator': operator,
        'title': 'Edit Operator',
    }
    return render(request, 'machines/admin/operator_edit.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_delete(request, operator_id):
    """Delete/deactivate operator"""
    operator = get_object_or_404(CustomUser, id=operator_id, role=CustomUser.OPERATOR)
    
    if request.method == 'POST':
        # Deactivate instead of delete to preserve history
        operator.is_active = False
        operator.is_staff = False
        operator.save()
        
        messages.success(request, f'Operator {operator.username} has been deactivated.')
        return redirect('machines:operator_overview')
    
    # Check if operator has active assignments
    active_jobs = operator.operator_rentals.exclude(
        status__in=['completed', 'cancelled', 'rejected']
    ).count()
    
    context = {
        'operator': operator,
        'active_jobs': active_jobs,
        'title': 'Deactivate Operator',
    }
    return render(request, 'machines/admin/operator_delete_confirm.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_assign_machine(request, operator_id):
    """This function is deprecated - operators are assigned through rental approval"""
    messages.info(
        request,
        'Operators are now assigned to jobs through the rental approval system in the admin dashboard.'
    )
    return redirect('machines:operator_overview')
