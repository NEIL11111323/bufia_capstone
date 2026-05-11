"""
Views for sector management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from .models import Sector
from .forms_sector import SectorForm


def is_admin_or_president(user):
    """Check if user is admin or president"""
    return user.is_staff or user.is_superuser or user.role == 'superuser'


@login_required
@user_passes_test(is_admin_or_president)
def sector_list(request):
    """List all sectors"""
    sectors = Sector.objects.all().order_by('sector_number')
    return render(request, 'users/sector_list.html', {'sectors': sectors})


@login_required
@user_passes_test(is_admin_or_president)
def sector_create(request):
    """Create a new sector"""
    if request.method == 'POST':
        form = SectorForm(request.POST)
        if form.is_valid():
            sector = form.save()
            messages.success(request, f'Sector "{sector.name}" created successfully!')
            return redirect('sector_list')
    else:
        form = SectorForm()
    
    return render(request, 'users/sector_form.html', {'form': form, 'sector': None})


@login_required
@user_passes_test(is_admin_or_president)
def sector_edit(request, pk):
    """Edit an existing sector"""
    sector = get_object_or_404(Sector, id=pk)
    
    if request.method == 'POST':
        form = SectorForm(request.POST, instance=sector)
        if form.is_valid():
            sector = form.save()
            messages.success(request, f'Sector "{sector.name}" updated successfully!')
            return redirect('sector_detail', pk=sector.pk)
    else:
        form = SectorForm(instance=sector)
    
    return render(request, 'users/sector_form.html', {'form': form, 'sector': sector})


@login_required
@user_passes_test(is_admin_or_president)
@transaction.atomic
def sector_delete(request, pk):
    """Delete a sector"""
    sector = get_object_or_404(Sector, id=pk)
    member_count = sector.assigned_members.count()
    
    if request.method == 'POST':
        confirmation_text = (request.POST.get('delete_confirmation') or '').strip()
        if confirmation_text != 'CONFIRM':
            messages.error(request, 'Type CONFIRM before deleting this sector.')
            return render(request, 'users/sector_confirm_delete.html', {
                'sector': sector,
                'member_count': member_count,
            }, status=400)

        # Check if sector has members
        if member_count > 0:
            messages.error(
                request,
                f'Cannot delete sector "{sector.name}" because it has {member_count} assigned member(s). '
                'Please reassign members to another sector first.'
            )
            return redirect('sector_list')
        
        sector_name = sector.name
        sector.delete()
        messages.success(request, f'Sector "{sector_name}" deleted successfully!')
        return redirect('sector_list')
    
    return render(request, 'users/sector_confirm_delete.html', {
        'sector': sector,
        'member_count': member_count,
    })

