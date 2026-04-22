#!/usr/bin/env bash

set -o errexit
set -o nounset

echo "==> Applying database migrations"
python manage.py migrate --no-input

echo "==> Ensuring cache table exists"
python manage.py createcachetable || true

echo "==> Checking whether initial admin setup is still needed"
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings'); import django; django.setup(); from users.models import CustomUser; has_admin = CustomUser.objects.filter(is_superuser=True).exists(); print('=' * 60); print('Admin account already exists' if has_admin else 'SETUP REQUIRED! Visit /setup/ to create your admin account'); print('=' * 60)"
