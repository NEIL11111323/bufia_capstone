# Tech Context

## Tech Stack
- **Backend:** Django (Python)
- **Frontend:** HTML/CSS/JavaScript with Bootstrap 5
- **Database:** SQLite (Development), MySQL (Production)
- **Authentication:** Django Authentication System
- **Authorization:** Role-based access control + Verification-based access control
- **Deployment:** TBD

## Key Libraries
- Django 4.2+
- Bootstrap 5
- Font Awesome
- jQuery
- Django Crispy Forms
- Django Simple History

## App Structure
- **users**: User management, authentication, and verification
- **machines**: Machine rental and tracking
- **rice_mill**: Rice mill scheduling
- **notifications**: System alerts and messages
- **reports**: Data exports and analytics

## Database Considerations
*Document considerations related to the database schema, migrations, and performance.*

## Authentication Flow
1. User registers or logs in
2. System checks role (president, superuser, regular)
3. System checks verification status
4. Access control rules applied based on role + verification status
5. UI adjusts to show only accessible features

## Security Implementations
- Django's built-in security features (CSRF, password hashing, etc.)
- Role-based permission system
- Verification status checks for feature access

## Verification System Implementation
1. **Database Models:**
   - `CustomUser.is_verified` flag to track verification status
   - `MembershipApplication` model to store verification applications

2. **Access Control Components:**
   ```python
   # users/decorators.py
   def verified_member_required(view_func):
       """Decorator to restrict view access to verified members only."""
       @wraps(view_func)
       def _wrapped_view(request, *args, **kwargs):
           if not request.user.is_verified and not request.user.is_superuser:
               messages.warning(request, "Verification required")
               return redirect('profile')
           return view_func(request, *args, **kwargs)
       return _wrapped_view
   ```

3. **Global Middleware:**
   ```python
   # users/middleware.py
   class VerificationCheckMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response
           
       def __call__(self, request):
           # Check verification status for certain paths
           # ...
   ```

4. **Template Tags:**
   ```python
   # users/templatetags/verification_tags.py
   @register.simple_tag(takes_context=True)
   def can_access_feature(context):
       user = context['request'].user
       return user.is_verified or user.is_superuser
   ```

## Performance Considerations
*Document any performance considerations for the application.*

## Deployment Architecture
*Document the planned deployment architecture for the application.*

## Development Environment
*Document the development environment setup and configuration.*

*Note: This file focuses on the technical implementation and architecture of the project. It should be updated as the technical implementation evolves.* 