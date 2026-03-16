# Operator Overview Implementation Plan

**Date**: March 12, 2026  
**Goal**: Transform "Assign Operators" into "Operator Overview" - a workload dashboard for admins

## Current State

**Navigation** (Line 946-954 in base.html):
```html
<div class="nav-section-title">Operator Assignment</div>
<div class="nav-item">
    <a href="{% url 'machines:rental_list' %}">
        <i class="fas fa-user-gear"></i>
        <span class="nav-link-text">Assign Operators</span>
    </a>
</div>
```

**Problem**: Links to rental_list, not a dedicated operator overview

---

## Proposed Changes

### 1. Rename Navigation Section
**From**: "Operator Assignment"  
**To**: "Operator Management"

### 2. Rename Menu Item
**From**: "Assign Operators"  
**To**: "Operator Overview"

### 3. Create New View: `operator_overview`

**Purpose**: Show all operators with their workload and availability

**Display**:
- List of all operators
- Current assignments count
- Completed jobs count
- Availability status
- Recent activity
- Quick link to their assigned rentals

---

## Implementation Steps

### Step 1: Update Navigation (templates/base.html)

**Change**:
```html
{% if user.is_superuser %}
<div class="nav-section-title">Operator Management</div>

<div class="nav-item">
    <a href="{% url 'machines:operator_overview' %}" class="nav-link">
        <i class="fas fa-users-gear"></i>
        <span class="nav-link-text">Operator Overview</span>
    </a>
</div>
{% endif %}
```

### Step 2: Create URL Pattern (machines/urls.py)

**Add**:
```python
path('operators/overview/', admin_views.operator_overview, name='operator_overview'),
```

### Step 3: Create View (machines/admin_views.py)

**Add**:
```python
@login_required
@user_passes_test(lambda u: u.is_superuser)
def operator_overview(request):
    """Overview of all operators and their workload"""
    from users.models import CustomUser
    from django.db.models import Count, Q
    
    # Get all operators
    operators = CustomUser.objects.filter(
        is_staff=True,
        is_superuser=False
    ).annotate(
        active_jobs=Count(
            'assigned_rentals',
            filter=Q(assigned_rentals__status='approved')
        ),
        completed_jobs=Count(
            'assigned_rentals',
            filter=Q(assigned_rentals__status='completed')
        )
    ).order_by('first_name', 'last_name')
    
    context = {
        'operators': operators,
    }
    
    return render(request, 'machines/admin/operator_overview.html', context)
```

### Step 4: Create Template (templates/machines/admin/operator_overview.html)

**Create new template showing**:
- Operator cards with stats
- Availability indicators
- Links to assigned rentals
- Contact information

---

## Template Design

### Operator Overview Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  Operator Overview                                       │
│  Monitor operator workload and availability              │
└─────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬────────────┐
│ Total        │ Available    │ Busy         │ Offline    │
│ Operators: 5 │ 2            │ 3            │ 0          │
└──────────────┴──────────────┴──────────────┴────────────┘

┌─────────────────────────────────────────────────────────┐
│ Operator: Pedro Santos                    [Available]   │
│ ─────────────────────────────────────────────────────── │
│ Active Jobs: 1    Completed: 15    Phone: 09XX-XXX-XXX │
│                                                          │
│ Current Assignments:                                     │
│ • Tractor rental for Juan Dela Cruz (Mar 15-17)        │
│                                                          │
│ [View All Assignments]                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Operator: Juan Reyes                      [Busy]        │
│ ─────────────────────────────────────────────────────── │
│ Active Jobs: 3    Completed: 8     Phone: 09XX-XXX-XXX │
│                                                          │
│ Current Assignments:                                     │
│ • Harvester for Maria Santos (Mar 14-16)               │
│ • Tractor for Pedro Cruz (Mar 15-18)                   │
│ • Plow for Ana Garcia (Mar 16-17)                      │
│                                                          │
│ [View All Assignments]                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Benefits

### For Admins
✅ Quick view of operator availability  
✅ See workload distribution  
✅ Identify available operators before assigning  
✅ Balance workload across operators  
✅ Monitor operator performance  

### For System
✅ Better resource allocation  
✅ Prevent operator overload  
✅ Improve scheduling efficiency  

---

## Next Steps

1. Update navigation in base.html
2. Create URL pattern
3. Create view function
4. Create template
5. Test functionality
6. Update documentation

---

**Status**: Ready for implementation
