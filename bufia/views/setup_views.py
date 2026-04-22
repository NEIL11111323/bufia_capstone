import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError

User = get_user_model()
logger = logging.getLogger(__name__)

def setup_view(request):
    """
    One-time setup page for creating initial superuser.
    Only accessible if no superusers exist.
    """
    template_name = 'setup.html'

    try:
        # Check if any superuser exists
        if User.objects.filter(is_superuser=True).exists():
            return redirect('home')
    except (OperationalError, ProgrammingError):
        logger.exception("Setup page unavailable because the user table is not ready.")
        messages.error(
            request,
            'Setup is temporarily unavailable because the database is still initializing. '
            'Please wait a moment and redeploy if this is the first launch.'
        )
        return render(request, template_name, status=503)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, template_name)
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, template_name)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, template_name)
        
        try:
            # Create superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            user.role = 'superuser'
            user.is_verified = True
            user.save()
            
            messages.success(request, f'Admin account created successfully! You can now login with username: {username}')
            return redirect('account_login')
        
        except Exception as e:
            logger.exception("Failed to create initial superuser during setup.")
            messages.error(request, f'Error creating admin account: {str(e)}')
            return render(request, template_name)
    
    return render(request, template_name)
