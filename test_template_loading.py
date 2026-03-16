#!/usr/bin/env python
"""
Test if Django can load the operator_overview template
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.template.loader import get_template
from django.template import TemplateDoesNotExist

def test_template_loading():
    """Test if the operator_overview template can be loaded"""
    template_name = 'machines/admin/operator_overview.html'
    
    print("=" * 60)
    print("DJANGO TEMPLATE LOADING TEST")
    print("=" * 60)
    print()
    
    # Check if file exists
    template_path = os.path.join('templates', template_name)
    file_exists = os.path.exists(template_path)
    print(f"File exists on disk: {file_exists}")
    if file_exists:
        file_size = os.path.getsize(template_path)
        print(f"File size: {file_size} bytes")
    print()
    
    # Try to load template through Django
    print(f"Attempting to load template: {template_name}")
    try:
        template = get_template(template_name)
        print("✅ SUCCESS! Django can load the template")
        print(f"Template object: {template}")
        print()
        print("The template exists and Django can find it.")
        print("If you're still seeing errors, try:")
        print("1. Stop Django server (Ctrl+C)")
        print("2. Clear __pycache__ folders")
        print("3. Restart server: python manage.py runserver")
        return True
    except TemplateDoesNotExist as e:
        print(f"❌ FAILED! Django cannot load the template")
        print(f"Error: {e}")
        print()
        print("Tried these locations:")
        for attempt in e.chain:
            print(f"  - {attempt}")
        print()
        print("SOLUTION:")
        print("1. The file exists but Django can't see it")
        print("2. This is a Windows caching issue")
        print("3. Stop the Django server completely")
        print("4. Delete all __pycache__ folders:")
        print("   Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force")
        print("5. Restart: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

if __name__ == "__main__":
    test_template_loading()
