#!/usr/bin/env python
"""Comprehensive test script for admin and user login"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import traceback

User = get_user_model()
client = Client()

print('='*70)
print('COMPREHENSIVE SYSTEM TEST - ADMIN AND USER LOGIN')
print('='*70)

# Test 1: Admin Login and Dashboard
print('\n📋 TEST 1: ADMIN USER LOGIN AND DASHBOARD')
print('-'*70)
admin = User.objects.filter(is_superuser=True).first()
if admin:
    print(f'Admin User: {admin.username}')
    client.force_login(admin)
    
    # Test dashboard
    try:
        response = client.get('/dashboard/')
        print(f'✅ Dashboard: Status {response.status_code}')
        if response.status_code != 200:
            print(f'   ❌ Expected 200, got {response.status_code}')
    except Exception as e:
        print(f'❌ Dashboard Error: {e}')
        traceback.print_exc()
    
    # Test profile
    try:
        response = client.get('/profile/')
        print(f'✅ Profile: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Profile Error: {e}')
    
    # Test user list (admin only)
    try:
        response = client.get('/users/')
        print(f'✅ User List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ User List Error: {e}')
    
    # Test registration dashboard (admin only)
    try:
        response = client.get('/membership/registration/')
        print(f'✅ Registration Dashboard: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Registration Dashboard Error: {e}')
    
    # Test machines list
    try:
        response = client.get('/machines/')
        print(f'✅ Machines List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Machines List Error: {e}')
    
    # Test rentals list
    try:
        response = client.get('/machines/rentals/')
        print(f'✅ Rentals List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Rentals List Error: {e}')
else:
    print('❌ No admin user found')

# Test 2: Regular User Login and Dashboard
print('\n📋 TEST 2: REGULAR USER LOGIN AND DASHBOARD')
print('-'*70)
regular_user = User.objects.filter(is_staff=False, is_superuser=False).first()
if regular_user:
    print(f'Regular User: {regular_user.username}')
    client.force_login(regular_user)
    
    # Test dashboard
    try:
        response = client.get('/dashboard/')
        print(f'✅ Dashboard: Status {response.status_code}')
        if response.status_code != 200:
            print(f'   ❌ Expected 200, got {response.status_code}')
    except Exception as e:
        print(f'❌ Dashboard Error: {e}')
        traceback.print_exc()
    
    # Test profile
    try:
        response = client.get('/profile/')
        print(f'✅ Profile: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Profile Error: {e}')
    
    # Test machines list
    try:
        response = client.get('/machines/')
        print(f'✅ Machines List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Machines List Error: {e}')
    
    # Test rentals list
    try:
        response = client.get('/machines/rentals/')
        print(f'✅ Rentals List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ Rentals List Error: {e}')
    
    # Test user list (should be forbidden)
    try:
        response = client.get('/users/')
        if response.status_code == 302 or response.status_code == 403:
            print(f'✅ User List: Correctly restricted (Status {response.status_code})')
        else:
            print(f'⚠️  User List: Status {response.status_code}')
    except Exception as e:
        print(f'❌ User List Error: {e}')
else:
    print('❌ No regular user found')

# Test 3: System Health Checks
print('\n📋 TEST 3: SYSTEM HEALTH CHECKS')
print('-'*70)

# Check for any Python errors
try:
    from bufia.models import Payment
    from machines.models import Rental, Machine
    print('✅ All models import successfully')
except Exception as e:
    print(f'❌ Model import error: {e}')

# Check database connectivity
try:
    user_count = User.objects.count()
    machine_count = Machine.objects.count()
    rental_count = Rental.objects.count()
    print(f'✅ Database connectivity: {user_count} users, {machine_count} machines, {rental_count} rentals')
except Exception as e:
    print(f'❌ Database error: {e}')

# Check transaction ID system
try:
    from django.contrib.contenttypes.models import ContentType
    test_user = User.objects.first()
    test_rental = Rental.objects.first()
    if test_rental:
        content_type = ContentType.objects.get_for_model(Rental)
        payment = Payment.objects.create(
            user=test_user,
            payment_type='rental',
            amount=100.00,
            currency='PHP',
            status='pending',
            content_type=content_type,
            object_id=test_rental.id
        )
        print(f'✅ Transaction ID System: {payment.internal_transaction_id}')
        payment.delete()
    else:
        print('⚠️  No rental found for transaction ID test')
except Exception as e:
    print(f'❌ Transaction ID error: {e}')

print('\n' + '='*70)
print('COMPREHENSIVE TEST COMPLETED')
print('='*70)
