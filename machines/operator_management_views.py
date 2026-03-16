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
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        try:
            # Create user with operator role
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                role=CustomUser.OPERATOR,
                is_staff=True,
                is_active=True
            )
            
            messages.success(request, f'Operator {username} created successfully.')
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
