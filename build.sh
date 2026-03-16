#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser automatically
python manage.py shell << EOF
from users.models import CustomUser
import os

username = 'admin'
email = 'admin@bufia.com'
password = 'BufiaAdmin2024'

if not CustomUser.objects.filter(username=username).exists():
    user = CustomUser.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    user.role = 'superuser'
    user.is_verified = True
    user.save()
    print(f'Superuser {username} created successfully!')
else:
    print(f'Superuser {username} already exists.')
EOF
