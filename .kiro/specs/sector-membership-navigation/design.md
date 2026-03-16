# Design Document: Sector-Based Membership & Navigation Enhancement

## Overview

This document provides the technical design for implementing sector-based membership management, reorganized admin navigation, and synchronized operator-admin dashboards with responsive design.

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     BUFIA System                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Frontend   │  │   Backend    │  │   Database   │     │
│  │              │  │              │  │              │     │
│  │ - Templates  │◄─┤ - Views      │◄─┤ - Models     │     │
│  │ - CSS/JS     │  │ - Forms      │  │ - Migrations │     │
│  │ - Responsive │  │ - URLs       │  │ - Indexes    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Integration Layer                        │  │
│  │  - Notifications  - Email  - Activity Logs           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: Django 4.x, Python 3.10+
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5, JavaScript (ES6+)
- **Icons**: Font Awesome 6
- **Charts**: Chart.js (for reports)
- **Export**: jsPDF, SheetJS
- **Server**: Windows, Bash shell

## Database Design

### Enhanced Sector Model

```python
class Sector(models.Model):
    """Geographic sector within BUFIA jurisdiction"""
    sector_number = models.IntegerField(
        unique=True,
        choices=[(i, f'Sector {i}') for i in range(1, 11)],
        help_text="Sector number (1-10)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Area name (e.g., 'North District')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the sector"
    )
    area_coverage = models.TextField(
        blank=True,
        help_text="Geographic boundaries and coverage area"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this sector is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sector_number']
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectors'
        indexes = [
            models.Index(fields=['sector_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Sector {self.sector_number} - {self.name}"
    
    @property
    def total_members(self):
        """Total approved members in this sector"""
        return self.members.filter(is_approved=True).count()
    
    @property
    def active_members(self):
        """Total verified members in this sector"""
        return self.members.filter(
            is_approved=True,
            user__is_verified=True
        ).count()
    
    @property
    def pending_applications(self):
        """Pending applications for this sector"""
        return self.members.filter(
            is_approved=False,
            is_rejected=False
        ).count()
    
    @property
    def average_farm_size(self):
        """Average farm size in this sector"""
        from django.db.models import Avg
        result = self.members.filter(
            is_approved=True
        ).aggregate(Avg('farm_size'))
        return result['farm_size__avg'] or 0
```


### Enhanced MembershipApplication Model

```python
class MembershipApplication(models.Model):
    """Enhanced with sector tracking"""
    # ... existing fields ...
    
    # Sector fields (existing)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text="Sector selected by user during application"
    )
    assigned_sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_members',
        help_text="Sector assigned by admin during verification"
    )
    
    # New sector tracking fields
    sector_confirmed = models.BooleanField(
        default=False,
        help_text="User confirmed sector selection"
    )
    sector_change_reason = models.TextField(
        blank=True,
        help_text="Reason for sector change by admin"
    )
    previous_sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_members',
        help_text="Previous sector before reassignment"
    )
    sector_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last sector change"
    )
    sector_changed_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sector_changes_made',
        help_text="Admin who changed the sector"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['sector', 'is_approved']),
            models.Index(fields=['assigned_sector', 'is_approved']),
            models.Index(fields=['payment_status']),
        ]
```

### Database Migration Strategy

**Migration 1: Add Sector Fields**
```python
# users/migrations/0XXX_add_sector_tracking.py
operations = [
    migrations.AddField(
        model_name='membershipapplication',
        name='sector_confirmed',
        field=models.BooleanField(default=False),
    ),
    migrations.AddField(
        model_name='membershipapplication',
        name='sector_change_reason',
        field=models.TextField(blank=True),
    ),
    # ... other fields ...
]
```

**Migration 2: Add Indexes**
```python
operations = [
    migrations.AddIndex(
        model_name='membershipapplication',
        index=models.Index(
            fields=['sector', 'is_approved'],
            name='sector_approved_idx'
        ),
    ),
]
```

**Migration 3: Populate Sectors**
```python
def populate_sectors(apps, schema_editor):
    Sector = apps.get_model('users', 'Sector')
    sectors_data = [
        (1, 'North District', 'Northern farming area'),
        (2, 'South District', 'Southern farming area'),
        # ... sectors 3-10 ...
    ]
    for number, name, desc in sectors_data:
        Sector.objects.get_or_create(
            sector_number=number,
            defaults={'name': name, 'description': desc}
        )
```


## URL Structure

### New URL Patterns

```python
# users/urls.py - Membership Registration
urlpatterns = [
    # Registration Dashboard
    path('membership/registration/', 
         views.registration_dashboard, 
         name='registration_dashboard'),
    path('membership/registration/pending/', 
         views.pending_applications, 
         name='pending_applications'),
    path('membership/registration/<int:pk>/review/', 
         views.review_application, 
         name='review_application'),
    path('membership/registration/<int:pk>/approve/', 
         views.approve_application, 
         name='approve_application'),
    path('membership/registration/<int:pk>/reject/', 
         views.reject_application, 
         name='reject_application'),
    
    # Sector Management
    path('sectors/', views.sector_overview, name='sector_overview'),
    path('sectors/<int:pk>/', views.sector_detail, name='sector_detail'),
    path('sectors/<int:pk>/members/', views.sector_members, name='sector_members'),
    
    # Enhanced Member URLs
    path('users/', views.user_list, name='user_list'),  # Add ?sector=<id> filter
    path('users/by-sector/', views.members_by_sector, name='members_by_sector'),
    path('users/bulk-assign-sector/', views.bulk_assign_sector, name='bulk_assign_sector'),
]

# reports/urls.py - Sector Reports
urlpatterns = [
    path('sectors/<int:pk>/member-list/', 
         views.sector_member_list_report, 
         name='sector_member_list'),
    path('sectors/<int:pk>/summary/', 
         views.sector_summary_report, 
         name='sector_summary'),
    path('sectors/comparison/', 
         views.sector_comparison_report, 
         name='sector_comparison'),
]
```

## View Design

### Registration Dashboard View

```python
@login_required
@user_passes_test(lambda u: u.is_superuser)
def registration_dashboard(request):
    """Membership registration dashboard"""
    # Statistics
    stats = {
        'pending_payment': MembershipApplication.objects.filter(
            payment_status='pending'
        ).count(),
        'payment_received': MembershipApplication.objects.filter(
            payment_status='paid',
            is_approved=False
        ).count(),
        'approved': MembershipApplication.objects.filter(
            is_approved=True
        ).count(),
        'rejected': MembershipApplication.objects.filter(
            is_rejected=True
        ).count(),
    }
    
    # Filters
    sector_filter = request.GET.get('sector')
    payment_filter = request.GET.get('payment_status')
    
    applications = MembershipApplication.objects.select_related(
        'user', 'sector'
    ).filter(
        is_approved=False,
        is_rejected=False
    )
    
    if sector_filter:
        applications = applications.filter(sector_id=sector_filter)
    if payment_filter:
        applications = applications.filter(payment_status=payment_filter)
    
    applications = applications.order_by('-submission_date')
    
    context = {
        'stats': stats,
        'applications': applications,
        'sectors': Sector.objects.filter(is_active=True),
    }
    return render(request, 'users/registration_dashboard.html', context)
```


### Approve Application View

```python
@login_required
@user_passes_test(lambda u: u.is_superuser)
@transaction.atomic
def approve_application(request, pk):
    """Approve membership application"""
    application = get_object_or_404(
        MembershipApplication.objects.select_for_update(),
        pk=pk
    )
    
    if request.method == 'POST':
        assigned_sector_id = request.POST.get('assigned_sector')
        approval_notes = request.POST.get('approval_notes', '')
        
        # Assign sector
        if assigned_sector_id:
            application.assigned_sector_id = assigned_sector_id
        else:
            application.assigned_sector = application.sector
        
        # Approve application
        application.is_approved = True
        application.reviewed_by = request.user
        application.review_date = timezone.now().date()
        application.save()
        
        # Update user
        user = application.user
        user.is_verified = True
        user.membership_approved_date = timezone.now().date()
        user.save()
        
        # Send notification
        UserNotification.objects.create(
            user=user,
            notification_type='membership_approved',
            message=f'Your membership application has been approved! Welcome to BUFIA.',
        )
        
        # Send email
        send_mail(
            subject='BUFIA Membership Approved',
            message=f'Congratulations! Your membership has been approved.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='membership_approved',
            description=f'Approved membership for {user.get_full_name()}',
            related_object_id=application.id,
        )
        
        messages.success(request, f'Membership approved for {user.get_full_name()}')
        return redirect('registration_dashboard')
    
    context = {
        'application': application,
        'sectors': Sector.objects.filter(is_active=True),
    }
    return render(request, 'users/approve_application.html', context)
```

## Form Design

### Sector Selection Form (Signup Enhancement)

```python
# users/forms.py
from allauth.account.forms import SignupForm

class SectorSignupForm(SignupForm):
    """Enhanced signup form with sector selection"""
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.filter(is_active=True),
        required=True,
        empty_label="Select your farm sector",
        help_text="Select the sector where your farm is located",
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    sector_confirmed = forms.BooleanField(
        required=True,
        label="I confirm my farm is located in the selected sector",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize sector display
        self.fields['sector'].label_from_instance = lambda obj: f"Sector {obj.sector_number} - {obj.name}"
    
    def save(self, request):
        user = super().save(request)
        # Sector will be saved in MembershipApplication
        # when user completes full application
        return user
```

### Membership Application Form Enhancement

```python
class MembershipApplicationForm(forms.ModelForm):
    """Enhanced with sector selection"""
    class Meta:
        model = MembershipApplication
        fields = [
            'middle_name', 'gender', 'birth_date', 'place_of_birth',
            'civil_status', 'education',
            'sitio', 'barangay', 'city', 'province',
            'sector', 'sector_confirmed',  # NEW
            'is_tiller', 'lot_number', 'ownership_type',
            'land_owner', 'farm_manager', 'farm_location',
            'bufia_farm_location', 'farm_size',
            'payment_method',
        ]
        widgets = {
            'sector': forms.Select(attrs={'class': 'form-select'}),
            'sector_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # ... other widgets ...
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'].queryset = Sector.objects.filter(is_active=True)
        self.fields['sector'].label_from_instance = lambda obj: f"Sector {obj.sector_number} - {obj.name}"
        self.fields['sector'].required = True
        self.fields['sector_confirmed'].required = True
```


## Template Design

### Navigation Structure (base.html)

```django
{# templates/base.html - Enhanced Navigation #}
{% if user.is_authenticated %}
<aside class="sidebar" id="sidebar">
    <nav class="sidebar-nav">
        {% if user.is_staff and not user.is_superuser %}
            {# OPERATOR NAVIGATION - No changes #}
        {% else %}
            {# ADMIN/USER NAVIGATION #}
            
            <!-- Main -->
            <div class="nav-section-title">Main</div>
            <div class="nav-item">
                <a href="{% url 'dashboard' %}" class="nav-link">
                    <i class="fas fa-gauge-high"></i>
                    <span class="nav-link-text">Dashboard</span>
                </a>
            </div>
            
            <!-- Equipment & Scheduling -->
            <div class="nav-section-title">Equipment & Scheduling</div>
            <div class="nav-item">
                <a href="{% url 'machines:machine_list' %}" class="nav-link">
                    <i class="fas fa-tractor"></i>
                    <span class="nav-link-text">Machines</span>
                </a>
            </div>
            <!-- ... other equipment links ... -->
            
            <!-- Operator Assignment (NEW) -->
            {% if user.is_superuser %}
            <div class="nav-section-title">Operator Assignment</div>
            <div class="nav-item">
                <a href="{% url 'operators:assign' %}" class="nav-link">
                    <i class="fas fa-user-gear"></i>
                    <span class="nav-link-text">Assign Operators</span>
                </a>
            </div>
            <div class="nav-item">
                <a href="{% url 'machines:operator_dashboard' %}" class="nav-link">
                    <i class="fas fa-gauge-high"></i>
                    <span class="nav-link-text">Operator Dashboard</span>
                </a>
            </div>
            {% endif %}
            
            <!-- Services -->
            <div class="nav-section-title">Services</div>
            <div class="nav-item">
                <a href="{% url 'irrigation:irrigation_request_list' %}" class="nav-link">
                    <i class="fas fa-droplet"></i>
                    <span class="nav-link-text">Water Irrigation</span>
                </a>
            </div>
            
            <!-- Membership Management (NEW) -->
            {% if user.is_superuser %}
            <div class="nav-section-title">Membership Management</div>
            
            <div class="nav-item">
                <a href="{% url 'registration_dashboard' %}" class="nav-link">
                    <i class="fas fa-user-plus"></i>
                    <span class="nav-link-text">Membership Registration</span>
                </a>
            </div>
            
            <div class="nav-item nav-dropdown">
                <button class="nav-dropdown-toggle">
                    <i class="fas fa-users icon"></i>
                    <span class="nav-link-text">Members</span>
                    <i class="fas fa-chevron-down dropdown-arrow"></i>
                </button>
                <div class="nav-dropdown-menu">
                    <a href="{% url 'user_list' %}" class="nav-link">
                        <i class="fas fa-list"></i>
                        <span class="nav-link-text">All Members</span>
                    </a>
                    <a href="{% url 'user_list' %}?verified=true" class="nav-link">
                        <i class="fas fa-check-circle"></i>
                        <span class="nav-link-text">Verified Members</span>
                    </a>
                    <a href="{% url 'members_by_sector' %}" class="nav-link">
                        <i class="fas fa-map-marked-alt"></i>
                        <span class="nav-link-text">By Sector</span>
                    </a>
                </div>
            </div>
            
            <div class="nav-item">
                <a href="{% url 'sector_overview' %}" class="nav-link">
                    <i class="fas fa-map-marked-alt"></i>
                    <span class="nav-link-text">Sectors</span>
                </a>
            </div>
            {% endif %}
            
            <!-- Reports & Analytics -->
            {# ... existing reports with sector reports added ... #}
        {% endif %}
    </nav>
</aside>
{% endif %}
```

### Registration Dashboard Template

```django
{# templates/users/registration_dashboard.html #}
{% extends 'base.html' %}

{% block content %}
<div class="container-fluid py-4">
    <div class="page-header">
        <h1><i class="fas fa-user-plus me-2"></i>Membership Registration</h1>
        <p class="text-muted">Manage membership applications and payments</p>
    </div>
    
    <!-- Statistics Cards -->
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="stat-card">
                <div class="stat-icon bg-warning">
                    <i class="fas fa-clock"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Pending Payment</div>
                    <div class="stat-value">{{ stats.pending_payment }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <div class="stat-icon bg-info">
                    <i class="fas fa-money-bill"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Payment Received</div>
                    <div class="stat-value">{{ stats.payment_received }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <div class="stat-icon bg-success">
                    <i class="fas fa-check-circle"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Approved</div>
                    <div class="stat-value">{{ stats.approved }}</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <div class="stat-icon bg-danger">
                    <i class="fas fa-times-circle"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">Rejected</div>
                    <div class="stat-value">{{ stats.rejected }}</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Filters -->
    <div class="card mb-4">
        <div class="card-body">
            <form method="get" class="row g-3">
                <div class="col-md-4">
                    <label class="form-label">Search</label>
                    <input type="text" name="search" class="form-control" 
                           placeholder="Name, email, or transaction ID">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Sector</label>
                    <select name="sector" class="form-select">
                        <option value="">All Sectors</option>
                        {% for sector in sectors %}
                        <option value="{{ sector.id }}">Sector {{ sector.sector_number }} - {{ sector.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Payment Status</label>
                    <select name="payment_status" class="form-select">
                        <option value="">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="paid">Paid</option>
                    </select>
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-filter me-2"></i>Filter
                    </button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Applications Table -->
    <div class="card">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Transaction ID</th>
                            <th>Member</th>
                            <th>Email</th>
                            <th>Sector</th>
                            <th>Submitted</th>
                            <th>Payment Method</th>
                            <th>Payment Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for app in applications %}
                        <tr>
                            <td><code>{{ app.transaction_id }}</code></td>
                            <td>{{ app.user.get_full_name }}</td>
                            <td>{{ app.user.email }}</td>
                            <td>
                                <span class="badge bg-primary">
                                    Sector {{ app.sector.sector_number }}
                                </span>
                            </td>
                            <td>{{ app.submission_date|date:"M d, Y" }}</td>
                            <td>{{ app.get_payment_method_display }}</td>
                            <td>
                                <span class="badge bg-{{ app.payment_status|yesno:'success,warning' }}">
                                    {{ app.get_payment_status_display }}
                                </span>
                            </td>
                            <td>
                                <a href="{% url 'review_application' app.id %}" 
                                   class="btn btn-sm btn-primary">
                                    <i class="fas fa-eye"></i> Review
                                </a>
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="8" class="text-center text-muted py-4">
                                No pending applications
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```


## Responsive Design Strategy

### Mobile-First Approach

```css
/* Base styles for mobile (320px+) */
.stat-card {
    padding: 1rem;
    margin-bottom: 1rem;
}

.table-responsive {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

/* Tablet (768px+) */
@media (min-width: 768px) {
    .stat-card {
        padding: 1.5rem;
    }
    
    .sidebar {
        display: block;
    }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
    .main-content {
        margin-left: var(--sidebar-width);
    }
}

/* Large Desktop (1920px+) */
@media (min-width: 1920px) {
    .container-fluid {
        max-width: 1800px;
        margin: 0 auto;
    }
}
```

### Touch-Friendly Interactions

```css
/* Minimum touch target size: 44x44px */
.btn {
    min-height: 44px;
    min-width: 44px;
    padding: 0.75rem 1.5rem;
}

.form-control,
.form-select {
    min-height: 44px;
    font-size: 16px; /* Prevents zoom on iOS */
}

/* Larger tap targets on mobile */
@media (max-width: 768px) {
    .nav-link {
        padding: 1rem;
        font-size: 1rem;
    }
    
    .btn {
        padding: 1rem 1.5rem;
    }
}
```

## Dashboard Synchronization Design

### Real-Time Data Flow

```
┌─────────────────┐         ┌─────────────────┐
│  Operator       │         │  Admin          │
│  Dashboard      │         │  Dashboard      │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ 1. Update Status          │
         ├──────────────────────────►│
         │                           │
         │                           │ 2. View Update
         │                           │    (on refresh)
         │                           │
         │ 3. Assign Operator        │
         │◄──────────────────────────┤
         │                           │
         │ 4. See Assignment         │
         │    (on refresh)           │
         │                           │
         ▼                           ▼
    ┌────────────────────────────────────┐
    │         Database (PostgreSQL)       │
    │  - Atomic transactions              │
    │  - Row-level locking                │
    │  - Consistent reads                 │
    └────────────────────────────────────┘
```

### Transaction Safety

```python
from django.db import transaction

@transaction.atomic
def update_operator_job(request, rental_id):
    """Atomic job status update"""
    # Lock the rental row
    rental = Rental.objects.select_for_update().get(pk=rental_id)
    
    # Update status
    rental.operator_status = new_status
    rental.operator_last_update_at = timezone.now()
    rental.save()
    
    # Create notification (part of same transaction)
    UserNotification.objects.create(
        user=rental.user,
        message=f'Job status updated to {rental.get_operator_status_display()}'
    )
    
    # If any operation fails, entire transaction rolls back
    return redirect('operator_dashboard')
```

### Optimized Queries

```python
# Bad: N+1 queries
applications = MembershipApplication.objects.all()
for app in applications:
    print(app.user.email)  # Hits database each time
    print(app.sector.name)  # Hits database each time

# Good: Optimized with select_related
applications = MembershipApplication.objects.select_related(
    'user', 'sector', 'assigned_sector'
).all()
for app in applications:
    print(app.user.email)  # No additional query
    print(app.sector.name)  # No additional query
```

## Report Generation Design

### Printable Member List

```python
def sector_member_list_report(request, pk):
    """Generate printable sector member list"""
    sector = get_object_or_404(Sector, pk=pk)
    
    members = MembershipApplication.objects.select_related(
        'user'
    ).filter(
        sector=sector,
        is_approved=True
    ).order_by('user__last_name', 'user__first_name')
    
    context = {
        'sector': sector,
        'members': members,
        'total_members': members.count(),
        'report_date': timezone.now(),
    }
    
    return render(request, 'reports/sector_member_list.html', context)
```

### Print-Friendly CSS

```css
@media print {
    /* Hide navigation */
    .sidebar,
    .top-navbar,
    .no-print {
        display: none !important;
    }
    
    /* Full width content */
    .main-content {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Page breaks */
    .page-break {
        page-break-after: always;
    }
    
    /* Optimize for printing */
    body {
        font-size: 12pt;
        line-height: 1.5;
    }
    
    table {
        page-break-inside: avoid;
    }
    
    thead {
        display: table-header-group;
    }
}
```

### PDF Export

```javascript
// Using jsPDF
function exportToPDF() {
    const element = document.getElementById('report-content');
    const opt = {
        margin: 1,
        filename: 'sector-member-list.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
}
```

### Excel Export

```javascript
// Using SheetJS
function exportToExcel() {
    const table = document.getElementById('member-table');
    const wb = XLSX.utils.table_to_book(table, {sheet: "Members"});
    XLSX.writeFile(wb, 'sector-members.xlsx');
}
```

## Security Considerations

### Authentication & Authorization

```python
# View-level protection
@login_required
@user_passes_test(lambda u: u.is_superuser)
def registration_dashboard(request):
    # Only superusers can access
    pass

# Template-level protection
{% if user.is_superuser %}
    <a href="{% url 'registration_dashboard' %}">Registration</a>
{% endif %}

# URL-level protection (urls.py)
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('membership/registration/', 
         staff_member_required(views.registration_dashboard)),
]
```

### Input Validation

```python
class MembershipApplicationForm(forms.ModelForm):
    def clean_sector(self):
        sector = self.cleaned_data.get('sector')
        if not sector or not sector.is_active:
            raise forms.ValidationError("Please select a valid active sector")
        return sector
    
    def clean_farm_size(self):
        size = self.cleaned_data.get('farm_size')
        if size and size <= 0:
            raise forms.ValidationError("Farm size must be greater than zero")
        return size
```

### CSRF Protection

```django
{# All forms include CSRF token #}
<form method="post">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

## Performance Optimization

### Database Indexes

```python
class Meta:
    indexes = [
        models.Index(fields=['sector', 'is_approved']),
        models.Index(fields=['payment_status']),
        models.Index(fields=['submission_date']),
        models.Index(fields=['user', 'is_approved']),
    ]
```

### Query Optimization

```python
# Use select_related for ForeignKey
applications = MembershipApplication.objects.select_related(
    'user', 'sector', 'assigned_sector', 'reviewed_by'
)

# Use prefetch_related for reverse ForeignKey
sectors = Sector.objects.prefetch_related('members')

# Use only() to limit fields
applications = MembershipApplication.objects.only(
    'id', 'user__email', 'sector__name', 'payment_status'
)
```

### Caching Strategy

```python
from django.core.cache import cache

def sector_overview(request):
    # Cache sector statistics for 5 minutes
    cache_key = 'sector_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        stats = {
            'total_members': MembershipApplication.objects.filter(
                is_approved=True
            ).count(),
            # ... other stats ...
        }
        cache.set(cache_key, stats, 300)  # 5 minutes
    
    return render(request, 'sectors/overview.html', {'stats': stats})
```

## Testing Strategy

### Unit Tests

```python
from django.test import TestCase

class SectorModelTest(TestCase):
    def setUp(self):
        self.sector = Sector.objects.create(
            sector_number=1,
            name="Test Sector",
            is_active=True
        )
    
    def test_sector_str(self):
        self.assertEqual(str(self.sector), "Sector 1 - Test Sector")
    
    def test_total_members_property(self):
        # Create test members
        user = CustomUser.objects.create_user(username='test')
        MembershipApplication.objects.create(
            user=user,
            sector=self.sector,
            is_approved=True
        )
        self.assertEqual(self.sector.total_members, 1)
```

### Integration Tests

```python
from django.test import Client

class RegistrationDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
    
    def test_dashboard_access(self):
        response = self.client.get('/membership/registration/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Membership Registration')
    
    def test_approve_application(self):
        # Create test application
        user = CustomUser.objects.create_user(username='test')
        sector = Sector.objects.create(sector_number=1, name="Test")
        app = MembershipApplication.objects.create(
            user=user,
            sector=sector
        )
        
        # Approve
        response = self.client.post(f'/membership/registration/{app.id}/approve/', {
            'assigned_sector': sector.id
        })
        
        app.refresh_from_db()
        self.assertTrue(app.is_approved)
        self.assertTrue(app.user.is_verified)
```

## Deployment Considerations

### Migration Sequence

1. Run migrations to add new fields
2. Populate sectors (1-10)
3. Update existing applications with default sector
4. Deploy new code
5. Test thoroughly
6. Monitor for issues

### Rollback Plan

```python
# If issues occur, can rollback migrations
python manage.py migrate users <previous_migration_number>

# Restore from database backup if needed
pg_restore -d bufia_db backup.dump
```

### Monitoring

```python
# Log all critical operations
import logging
logger = logging.getLogger(__name__)

@transaction.atomic
def approve_application(request, pk):
    try:
        # ... approval logic ...
        logger.info(f"Approved application {pk} by {request.user.username}")
    except Exception as e:
        logger.error(f"Failed to approve application {pk}: {str(e)}")
        raise
```

## Summary

This design document provides the technical blueprint for implementing:

1. **Sector-based membership** with 10 sectors
2. **Reorganized navigation** with dedicated sections
3. **Membership registration dashboard** separate from member management
4. **Synchronized operator-admin dashboards** with atomic transactions
5. **Responsive design** for all devices
6. **Printable reports** with PDF/Excel export
7. **Performance optimization** with caching and query optimization
8. **Security** with proper authentication and authorization
9. **Testing** with unit and integration tests

All components follow Django best practices and are designed for maintainability, scalability, and user experience.
