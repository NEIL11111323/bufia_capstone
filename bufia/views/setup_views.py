from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import connection

User = get_user_model()

def setup_view(request):
    """
    One-time setup page for creating initial superuser.
    Only accessible if no superusers exist.
    """
    # Check if any superuser exists
    if User.objects.filter(is_superuser=True).exists():
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'setup.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, 'setup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'setup.html')
        
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
            messages.error(request, f'Error creating admin account: {str(e)}')
            return render(request, 'setup.html')
    
    return render(request, 'setup.html')
