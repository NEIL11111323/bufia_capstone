#!/usr/bin/env python
"""
Verification script for operator overview template fix
"""
import os
import sys

def check_template_exists():
    """Check if the operator_overview.html template exists"""
    template_path = "templates/machines/admin/operator_overview.html"
    
    if os.path.exists(template_path):
        print(f"✅ Template exists: {template_path}")
        
        # Check file size
        file_size = os.path.getsize(template_path)
        print(f"   File size: {file_size} bytes")
        
        # Check if file has content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.count('\n')
            print(f"   Lines: {lines}")
            
        if file_size > 1000:
            print("   ✅ Template has substantial content")
            return True
        else:
            print("   ⚠️  Template seems too small")
            return False
    else:
        print(f"❌ Template NOT found: {template_path}")
        return False

def check_url_pattern():
    """Check if URL pattern exists"""
    urls_path = "machines/urls.py"
    
    if os.path.exists(urls_path):
        with open(urls_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "operator_overview" in content and "path('operators/overview/'" in content:
            print("✅ URL pattern configured correctly")
            return True
        else:
            print("❌ URL pattern not found or incorrect")
            return False
    else:
        print(f"❌ URLs file not found: {urls_path}")
        return False

def check_view_function():
    """Check if view function exists"""
    views_path = "machines/admin_views.py"
    
    if os.path.exists(views_path):
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "def operator_overview" in content:
            print("✅ View function exists: operator_overview()")
            return True
        else:
            print("❌ View function not found")
            return False
    else:
        print(f"❌ Views file not found: {views_path}")
        return False

def main():
    print("=" * 60)
    print("OPERATOR OVERVIEW TEMPLATE FIX VERIFICATION")
    print("=" * 60)
    print()
    
    template_ok = check_template_exists()
    print()
    
    url_ok = check_url_pattern()
    print()
    
    view_ok = check_view_function()
    print()
    
    print("=" * 60)
    if template_ok and url_ok and view_ok:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("NEXT STEPS:")
        print("1. RESTART your Django development server")
        print("   - Stop the server (Ctrl+C)")
        print("   - Start it again: python manage.py runserver")
        print()
        print("2. Clear your browser cache:")
        print("   - Press Ctrl+Shift+Delete")
        print("   - Clear cached images and files")
        print()
        print("3. Navigate to: http://127.0.0.1:8000/machines/operators/overview/")
        print()
        print("The template exists but Django needs to reload it!")
    else:
        print("❌ SOME CHECKS FAILED")
        print("Please review the errors above")
    print("=" * 60)

if __name__ == "__main__":
    main()
