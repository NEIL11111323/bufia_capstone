# System Patterns

## User Roles & Permissions
1. President
   - Full system access
   - All administrative privileges
   - Can manage all aspects of the system

2. Superuser
   - Full system access
   - System maintenance privileges
   - Database management access

3. Regular Users
   - Basic system access
   - Machine rental requests
   - Rice mill scheduling
   - Profile management

## Machine Management
1. Machine Types
   - Harvester
   - Rice Mill
   - Flatbed Dryer
   - Walk-behind Transplanter
   - Hand Tractor
   - Rotavator
   - Four Wheel Drive Tractor
   - Riding Type Transplanter
   - Precision Seeders

2. Machine Status Management
   - Available
   - Rented
   - Under Maintenance
   - Maintenance Scheduled

3. Dynamic Pricing
   - Per-machine pricing
   - Admin-configurable rates
   - Price history tracking

## Reporting System
1. Revenue Reports
   - Daily revenue
   - Monthly revenue
   - Per-machine revenue
   - Per-service revenue

2. Rental Reports
   - Vehicle rental statistics
   - Rice mill rental statistics
   - Usage patterns
   - Popular machines/services

3. Maintenance Reports
   - Maintenance schedules
   - Maintenance history
   - Downtime analysis

## System Architecture
1. Frontend Components
   - Dashboard
   - Machine Management
   - Rice Mill Scheduling
   - User Management
   - Reporting Interface

2. Backend Services
   - Authentication Service
   - Machine Management Service
   - Scheduling Service
   - Notification Service
   - Reporting Service

3. Database Structure
   - User Management
   - Machine Inventory
   - Rental Records
   - Maintenance Records
   - Financial Records

## Design Patterns
1. MVC Architecture
   - Models for data structure
   - Views for user interface
   - Controllers for business logic

2. Service Layer
   - Business logic separation
   - Reusable components
   - Clean architecture

3. Repository Pattern
   - Data access abstraction
   - Consistent data operations
   - Easy testing and maintenance

## Component Relationships
*Describe how different components in the system interact with each other.*

## Data Flow
*Outline the flow of data through the system.*

## State Management
*Explain how state is managed throughout the application.*

## Error Handling
*Document the approach to error handling in the system.*

## Performance Considerations
*Describe any performance considerations or optimizations.*

## Security Patterns
*Document security patterns implemented in the system.*

## Code Structure
*Document the overall code structure, architecture patterns, and organization of the codebase.*

## Naming Conventions
*Document the naming conventions used throughout the codebase.*

## Design Patterns
*Document any design patterns used or created for the project.*

### Verification-Based Access Control
We use a multi-layered approach to implement verification checks across the application:

#### 1. Decorator Pattern
```python
# users/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def verified_member_required(view_func):
    """Decorator to restrict view access to verified members only."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Always allow superusers/presidents
            if request.user.is_superuser or request.user.is_president:
                return view_func(request, *args, **kwargs)
                
            # Check if user is verified
            if not request.user.is_verified:
                messages.warning(
                    request, 
                    "Your membership requires verification before you can access this feature. "
                    "Please complete your profile and submit the membership form."
                )
                return redirect('profile')
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view
```

#### 2. Global Middleware
```python
# users/middleware.py
class VerificationCheckMiddleware:
    """Middleware that performs global verification checks."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip check for unauthenticated users or admin users
        if not request.user.is_authenticated or request.user.is_president() or request.user.is_superuser:
            return self.get_response(request)
            
        # Check if path requires verification
        if any(path in request.path for path in ['/machines/rent/', '/machines/rental_create/', '/ricemill/']):
            if not request.user.is_verified:
                messages.warning(
                    request,
                    "Your membership requires verification before you can access this feature. "
                    "Please complete your profile and submit the membership form."
                )
                return redirect('profile')
                
        return self.get_response(request)
```

#### 3. Template Tags for Verification Status
```python
# users/templatetags/verification_tags.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def verification_status_badge(user):
    """Generate a badge showing the user's verification status."""
    if not user.is_authenticated:
        return ""
        
    if user.is_president() or user.is_superuser:
        return mark_safe('<span class="badge bg-primary">President/Admin</span>')
        
    if user.is_verified:
        return mark_safe('<span class="badge bg-success">Verified Member</span>')
    
    if hasattr(user, 'membership_application') and user.membership_application.status == 'pending':
        return mark_safe('<span class="badge bg-warning">Pending Verification</span>')
        
    return mark_safe('<span class="badge bg-danger">Unverified</span>')

@register.filter
def is_verified_or_exempt(user):
    """Check if user is verified or exempt from verification requirements."""
    return user.is_verified or user.is_president() or user.is_superuser

@register.simple_tag
def verification_alert(user):
    """Generate an alert message for unverified users."""
    if not user.is_authenticated or user.is_verified or user.is_president() or user.is_superuser:
        return ""
        
    return mark_safe(
        '<div class="alert alert-warning">'
        'Your membership requires verification before you can access all features. '
        f'<a href="{reverse("profile")}">Complete your profile</a> and submit the verification form.'
        '</div>'
    )
```

#### 4. Template-Level Verification Checks
We implement verification checks directly in templates to hide/disable features for unverified users:

```html
{% if user|is_verified_or_exempt %}
    <a href="{% url 'machines:rental_create' %}" class="btn btn-primary">
        <i class="fas fa-plus"></i> Rent Machine
    </a>
{% else %}
    <button class="btn btn-secondary" disabled data-bs-toggle="tooltip" title="Verification required">
        <i class="fas fa-plus"></i> Rent Machine
    </button>
{% endif %}
```

#### 5. JavaScript Validation
Additional verification checks in JavaScript prevent form submission for unverified users:

```javascript
// For unverified users - block rental creation
document.addEventListener('DOMContentLoaded', function() {
  const submitRentalBtn = document.getElementById('submitRental');
  if (submitRentalBtn) {
    submitRentalBtn.addEventListener('click', function(e) {
      e.preventDefault();
      alert("You must be a verified member to rent equipment.");
      window.location.href = "{% url 'profile' %}";
      return false;
    });
  }
});
```

This multi-layered approach ensures that verification requirements are enforced consistently across the system, providing both security and a good user experience.

## Authentication & Authorization
The system implements a layered approach to authentication and authorization:

1. **Authentication Layer**: Using Django's built-in authentication system
2. **Role-Based Access Control**: Users can be president, superuser, or regular users
3. **Verification Status Control**: Additional layer checking verification status before allowing feature access
4. **Permission-Based Actions**: Certain actions are restricted based on permissions

For verification checks, we use:
- Decorators on view functions
- Middleware for global checks
- Template conditions to show/hide UI elements
- Context processors to provide verification status to all templates

## Testing Approach
*Document the approach to testing the codebase.*

## Database Schema
*Document the database schema, relationships, and design decisions.*

## UI/UX Patterns
*Document any UI/UX patterns used consistently throughout the application.*

### Verification Status Indicators
We use consistent visual indicators for verification status:
- Green check icon and "Verified" label for verified members
- Blue clock icon and "Pending" label for members with submitted applications
- Yellow warning icon and "Not Verified" label for members without verification

### Feature Access Indicators
For unverified members, we:
1. Disable buttons with explanatory tooltips
2. Show helpful alert messages explaining the verification requirement
3. Provide direct links to verification steps
4. Use color-coding to indicate available vs restricted features

## Security Measures
*Document security measures implemented throughout the application.*

## Performance Optimizations
*Document any performance optimizations implemented in the codebase.*

*Note: This file should document any reusable patterns, architecture decisions, and coding standards used throughout the project. It serves as a reference for maintaining consistency and understanding the overall architecture.*

*Note: This file focuses on the technical architecture and patterns used in the project. It should be updated as the architecture evolves.* 