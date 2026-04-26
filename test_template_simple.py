#!/usr/bin/env python
"""
Simple test to check if template changes are working
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

def test_template_rendering():
    """Test if the template renders with our changes"""
    print("Testing template rendering...")
    
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/machines/admin/dashboard/')
        
        # Create a mock admin user
        admin_user = User(username='test_admin', is_staff=True, is_superuser=True)
        request.user = admin_user
        
        # Mock context data
        context = {
            'tab_counts': {
                'pending': 0,
                'approved': 0,
                'in_progress': 0,
                'completed': 0,
            },
            'in_kind_verification_count': 0,
            'overdue_rentals_count': 2,  # This should make the button appear
            'overdue_rentals': [],
            'conflict_review_count': 0,
            'conflict_review_rentals': [],
            'active_tab': 'pending',
            'status_filter': 'all',
            'payment_filter': 'all',
            'date_filter': 'all',
            'search_query': '',
            'page_obj': None,
        }
        
        # Try to render the template
        html = render_to_string('machines/admin/rental_dashboard.html', context, request=request)
        
        print(f"✅ Template rendered successfully ({len(html)} characters)")
        
        # Check for our button
        if 'admin_overdue_rentals_report' in html:
            print("✅ Overdue Rentals button URL found in rendered template")
        else:
            print("❌ Overdue Rentals button URL NOT found in rendered template")
        
        if 'Overdue Rentals' in html:
            print("✅ 'Overdue Rentals' text found in rendered template")
        else:
            print("❌ 'Overdue Rentals' text NOT found in rendered template")
            
        if 'btn-outline-danger' in html:
            print("✅ Danger button styling found in rendered template")
        else:
            print("❌ Danger button styling NOT found in rendered template")
            
        # Check for the test comment
        if 'TEST COMMENT: Overdue button should be here' in html:
            print("✅ Test comment found - template is being read correctly")
        else:
            print("❌ Test comment NOT found - template might not be updating")
            
        # Save rendered HTML for inspection
        with open('debug_template_output.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("📄 Rendered HTML saved to debug_template_output.html for inspection")
        
    except Exception as e:
        print(f"❌ Error rendering template: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_template_rendering()