"""
Quick test to verify template syntax is correct
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.template import Template, Context
from django.template.loader import get_template

try:
    # Try to load the template
    template = get_template('machines/admin/rental_approval.html')
    print("✅ Template loaded successfully!")
    print("✅ No syntax errors found")
except Exception as e:
    print(f"❌ Template error: {e}")
    import traceback
    traceback.print_exc()
