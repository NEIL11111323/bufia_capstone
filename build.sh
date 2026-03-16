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
from django.db.models import Q

username = 'admin'
email = 'admin@bufia.com'
password = 'BufiaAdmin2024'

# Delete any existing admin users (case-insensitive)
existing_admins = CustomUser.objects.filter(Q(username__iexact=username))
if existing_admins.exists():
    print(f'Deleting {existing_admins.count()} existing admin user(s)...')
    existing_admins.delete()

# Create fresh superuser
user = CustomUser.objects.create_superuser(
    username=username,
    email=email,
    password=password
)
user.role = 'superuser'
user.is_verified = True
user.save()
print(f'Superuser {username} created successfully!')
EOF
