#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create cache table (DatabaseCache backend)
python manage.py createcachetable

# Check if setup is needed (no superusers exist)
python manage.py shell << EOF
from users.models import CustomUser

if not CustomUser.objects.filter(is_superuser=True).exists():
    print("=" * 60)
    print("SETUP REQUIRED!")
    print("Visit /setup/ to create your admin account")
    print("=" * 60)
else:
    print("Admin account already exists")
EOF
