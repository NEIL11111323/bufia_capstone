#!/usr/bin/env python
"""
Force Django template refresh by clearing cache and restarting
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.core.cache import cache
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

def force_template_refresh():
    """Force template refresh"""
    print("🔄 Forcing Template Refresh")
    print("=" * 40)
    
    # Clear Django cache
    try:
        cache.clear()
        print("✅ Django cache cleared")
    except Exception as e:
        print(f"⚠️  Cache clear failed: {e}")
    
    # Try to load the base template
    try:
        template = get_template('base.html')
        print("✅ Base template loaded successfully")
        
        # Check if it contains our clean navigation
        template_source = template.template.source
        if 'CLEAN OPERATOR NAVIGATION' in template_source:
            print("✅ Clean operator navigation found in template")
        else:
            print("❌ Clean operator navigation NOT found in template")
            
        if 'operator_all_jobs' in template_source:
            print("✅ New operator URLs found in template")
        else:
            print("❌ New operator URLs NOT found in template")
            
    except TemplateDoesNotExist:
        print("❌ Base template not found")
    except Exception as e:
        print(f"❌ Template loading error: {e}")
    
    # Check operator dashboard template
    try:
        operator_template = get_template('machines/operator/operator_dashboard_clean.html')
        print("✅ Clean operator dashboard template found")
    except TemplateDoesNotExist:
        print("❌ Clean operator dashboard template NOT found")
    except Exception as e:
        print(f"❌ Operator template error: {e}")
    
    print("\n🎯 Recommendations:")
    print("1. Hard refresh browser (Ctrl+Shift+R)")
    print("2. Clear browser cache completely")
    print("3. Try incognito/private mode")
    print("4. Restart Django server")
    print("5. Check Django DEBUG setting is True")

if __name__ == '__main__':
    force_template_refresh()