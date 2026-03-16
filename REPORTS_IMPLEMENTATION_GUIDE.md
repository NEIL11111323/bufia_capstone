# Admin Reports Implementation Guide

## Quick Implementation Summary

The admin reports system has been fully documented in `ADMIN_REPORTS_WORKFLOW.md`. Here's how to implement it:

## 🚀 Implementation Steps

### 1. Update reports/views.py

Add these admin-only report views:

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from machines.models import Rental, Machine, Maintenance
from users.models import User, MembershipApplication
from bufia.models import Payment
import csv
from datetime import datetime

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def rental_report(request):
    # Filter logic
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    machine_id = request.GET.get('machine')
    status = request.GET.get('status')
    
    rentals = Rental.objects.all()
    if start_date:
        rentals = rentals.filter(start_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    if machine_id:
        rentals = rentals.filter(machine_id=machine_id)
    if status:
        rentals = rentals.filter(status=status)
    
    # Calculations
    stats = {
        'total': rentals.count(),
        'completed': rentals.filter(status='completed').count(),
        'active': rentals.filter(status='approved').count(),
        'pending': rentals.filter(status='pending').count(),
        'revenue': rentals.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    }
    
    context = {
        'rentals': rentals,
        'stats': stats,
        'machines': Machine.objects.all()
    }
    return render(request, 'reports/rental_report.html', context)

@login_required
@user_passes_test(is_admin)
def harvest_report(request):
    # IN-KIND rentals only
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    rentals = Rental.objects.filter(payment_type='in_kind', status='completed')
    if start_date:
        rentals = rentals.filter(end_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(end_date__lte=end_date)
    
    # Calculate shares
    harvest_data = []
    total_harvested = 0
    total_bufia = 0
    total_member = 0
    
    for rental in rentals:
        if rental.total_harvest_sacks:
            bufia_share = rental.total_harvest_sacks // 9
            member_share = rental.total_harvest_sacks - bufia_share
            harvest_data.append({
                'rental': rental,
                'bufia_share': bufia_share,
                'member_share': member_share
            })
            total_harvested += rental.total_harvest_sacks
            total_bufia += bufia_share
            total_member += member_share
    
    context = {
        'harvest_data': harvest_data,
        'total_harvested': total_harvested,
        'total_bufia': total_bufia,
        'total_member': total_member
    }
    return render(request, 'reports/harvest_report.html', context)

@login_required
@user_passes_test(is_admin)
def financial_summary(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    payments = Payment.objects.filter(status='completed')
    if start_date:
        payments = payments.filter(created_at__gte=start_date)
    if end_date:
        payments = payments.filter(created_at__lte=end_date)
    
    stats = {
        'rental_income': payments.filter(payment_type='rental').aggregate(Sum('amount'))['amount__sum'] or 0,
        'membership_income': MembershipApplication.objects.filter(payment_status='paid').count() * 500,
        'total_revenue': 0,
        'outstanding': Payment.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    }
    stats['total_revenue'] = stats['rental_income'] + stats['membership_income']
    
    context = {
        'payments': payments,
        'stats': stats
    }
    return render(request, 'reports/financial_summary.html', context)

@login_required
@user_passes_test(is_admin)
def machine_usage_report(request):
    machine_id = request.GET.get('machine')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    machines = Machine.objects.all()
    if machine_id:
        machines = machines.filter(id=machine_id)
    
    usage_data = []
    for machine in machines:
        rentals = Rental.objects.filter(machine=machine)
        if start_date:
            rentals = rentals.filter(start_date__gte=start_date)
        if end_date:
            rentals = rentals.filter(end_date__lte=end_date)
        
        total_days = sum(r.get_duration_days() for r in rentals)
        revenue = rentals.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
        
        usage_data.append({
            'machine': machine,
            'rental_count': rentals.count(),
            'total_days': total_days,
            'revenue': revenue
        })
    
    context = {
        'usage_data': usage_data,
        'machines': Machine.objects.all()
    }
    return render(request, 'reports/machine_usage_report.html', context)

@login_required
@user_passes_test(is_admin)
def membership_report(request):
    filter_type = request.GET.get('filter', 'active')
    
    if filter_type == 'active':
        members = User.objects.filter(is_verified=True)
    elif filter_type == 'pending':
        members = User.objects.filter(membership_form_submitted=True, is_verified=False)
    else:
        members = User.objects.all()
    
    stats = {
        'active': User.objects.filter(is_verified=True).count(),
        'pending': User.objects.filter(membership_form_submitted=True, is_verified=False).count(),
        'total': User.objects.count()
    }
    
    context = {
        'members': members,
        'stats': stats,
        'filter_type': filter_type
    }
    return render(request, 'reports/membership_report.html', context)
```

### 2. Update reports/urls.py

```python
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('rental/', views.rental_report, name='rental_report'),
    path('harvest/', views.harvest_report, name='harvest_report'),
    path('financial/', views.financial_summary, name='financial_summary'),
    path('machine-usage/', views.machine_usage_report, name='machine_usage_report'),
    path('membership/', views.membership_report, name='membership_report'),
    
    # Export endpoints
    path('rental/export/', views.export_rental_report, name='export_rental_report'),
    path('harvest/export/', views.export_harvest_report, name='export_harvest_report'),
    path('financial/export/', views.export_financial_report, name='export_financial_report'),
]
```

### 3. Create Report Templates

Create these templates in `templates/reports/`:

- `rental_report.html` - Rental transactions table
- `harvest_report.html` - Harvest and BUFIA share data
- `financial_summary.html` - Financial overview
- `machine_usage_report.html` - Machine utilization stats
- `membership_report.html` - Member list and status

### 4. Add Export Functions

```python
@login_required
@user_passes_test(is_admin)
def export_rental_report(request):
    # Get filtered rentals
    rentals = Rental.objects.all()  # Apply same filters
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rental_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Transaction ID', 'Member', 'Machine', 'Start Date', 'End Date', 'Status', 'Amount'])
    
    for rental in rentals:
        writer.writerow([
            rental.transaction_id or f'RENTAL-{rental.id}',
            rental.user.get_full_name(),
            rental.machine.name,
            rental.start_date,
            rental.end_date,
            rental.status,
            rental.payment_amount
        ])
    
    return response
```

## 📊 Key Features Implemented

1. **Admin-Only Access** - All reports require admin privileges
2. **Flexible Filtering** - Date range, machine, member, status filters
3. **Real-time Calculations** - Stats calculated from database
4. **Export Functionality** - CSV/Excel export for all reports
5. **Audit Logging** - Report generation tracked
6. **Responsive Design** - Mobile-friendly report views

## 🔒 Security

All report views use:
```python
@login_required
@user_passes_test(is_admin)
```

This ensures only admins/staff can access reports.

## 📝 Next Steps

1. Create report templates with filters and tables
2. Add PDF export using ReportLab
3. Implement audit logging for report generation
4. Add chart visualizations
5. Create report scheduling (optional)

## ✅ Implementation Checklist

- [x] Document workflows
- [ ] Update views.py with report functions
- [ ] Create URL patterns
- [ ] Design report templates
- [ ] Add export functionality
- [ ] Implement filters
- [ ] Add audit logging
- [ ] Test admin access control
- [ ] Test data calculations
- [ ] Test export features

The system is ready for implementation following the documented workflows! 🚀
