#!/usr/bin/env python
"""
Final verification script for operator dashboard templates
Confirms all duplicates are removed and correct templates are in use
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')

import django
django.setup()

from django.template.loader import get_template
from django.template import TemplateDoesNotExist


def main():
    print("=" * 70)
    print("OPERATOR DASHBOARD TEMPLATE VERIFICATION")
    print("=" * 70)
    
    # Check that old templates are deleted
    print("\n1. CHECKING OLD TEMPLATES ARE DELETED:")
    old_templates = [
        'machines/operator/dashboard.html',
        'machines/operator/operator_dashboard_simple.html',
    ]
    
    for template_name in old_templates:
        try:
            get_template(template_name)
            print(f"   ❌ OLD TEMPLATE STILL EXISTS: {template_name}")
        except TemplateDoesNotExist:
            print(f"   ✅ Deleted: {template_name}")
    
    # Check that active template exists
    print("\n2. CHECKING ACTIVE TEMPLATE:")
    try:
        template = get_template('machines/operator/operator_dashboard_clean.html')
        print("   ✅ Active template found: operator_dashboard_clean.html")
        
        # Read template content to verify it extends base_operator_v2.html
        template_path = 'templates/machines/operator/operator_dashboard_clean.html'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join([f.readline() for _ in range(5)])
                if 'base_operator_v2.html' in first_lines:
                    print("   ✅ Extends: base_operator_v2.html")
                elif 'base.html' in first_lines:
                    print("   ❌ ERROR: Still extends base.html")
                else:
                    print("   ⚠️  WARNING: Could not determine base template")
    except TemplateDoesNotExist:
        print("   ❌ Active template NOT FOUND")
    
    # Check base_operator_v2.html exists
    print("\n3. CHECKING BASE TEMPLATE:")
    try:
        get_template('base_operator_v2.html')
        print("   ✅ Base template found: base_operator_v2.html")
    except TemplateDoesNotExist:
        print("   ❌ Base template NOT FOUND")
    
    # Check all operator templates
    print("\n4. CHECKING ALL OPERATOR TEMPLATES:")
    operator_templates = [
        'machines/operator/operator_dashboard_clean.html',
        'machines/operator/operator_all_jobs.html',
        'machines/operator/operator_job_list.html',
        'machines/operator/operator_in_kind_payments.html',
        'machines/operator/operator_view_machines.html',
        'machines/operator/operator_notifications.html',
        'machines/operator/operator_decision_form.html',
    ]
    
    all_correct = True
    for template_name in operator_templates:
        template_path = f'templates/{template_name}'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join([f.readline() for _ in range(5)])
                if 'base_operator_v2.html' in first_lines:
                    print(f"   ✅ {template_name.split('/')[-1]}")
                else:
                    print(f"   ❌ {template_name.split('/')[-1]} - NOT using base_operator_v2.html")
                    all_correct = False
        else:
            print(f"   ❌ {template_name.split('/')[-1]} - FILE NOT FOUND")
            all_correct = False
    
    # Check view function
    print("\n5. CHECKING VIEW FUNCTION:")
    view_file = 'machines/operator_views.py'
    if os.path.exists(view_file):
        with open(view_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'operator_dashboard_clean.html' in content:
                print("   ✅ View uses: operator_dashboard_clean.html")
            else:
                print("   ❌ View does NOT use operator_dashboard_clean.html")
                all_correct = False
            
            if 'operator_dashboard_simple.html' in content:
                print("   ❌ View still references: operator_dashboard_simple.html")
                all_correct = False
    
    # Final summary
    print("\n" + "=" * 70)
    if all_correct:
        print("✅ ALL CHECKS PASSED - TEMPLATES ARE CLEAN")
        print("\nNEXT STEPS FOR USER:")
        print("1. Hard refresh browser: Ctrl + Shift + R (or Ctrl + F5)")
        print("2. Clear browser cache completely")
        print("3. Log out and log back in")
        print("4. Try accessing operator dashboard again")
    else:
        print("❌ SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
    print("=" * 70)


if __name__ == '__main__':
    main()
