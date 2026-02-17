#!/usr/bin/env python
"""
Comprehensive page test for BUFIA system
Tests all pages for both admin and regular users
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse, NoReverseMatch
from django.contrib.messages import get_messages

User = get_user_model()

class PageTester:
    def __init__(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def create_test_users(self):
        """Create test users if they don't exist"""
        # Create regular user
        try:
            self.regular_user = User.objects.get(username='test_user')
        except User.DoesNotExist:
            self.regular_user = User.objects.create_user(
                username='test_user',
                email='test@example.com',
                password='testpass123'
            )
            
        # Create admin user
        try:
            self.admin_user = User.objects.get(username='test_admin')
        except User.DoesNotExist:
            self.admin_user = User.objects.create_superuser(
                username='test_admin',
                email='admin@example.com',
                password='adminpass123'
            )
    
    def test_url(self, url_name, args=None, kwargs=None, user=None, method='GET', data=None):
        """Test a single URL"""
        args = args or []
        kwargs = kwargs or {}
        data = data or {}
        
        try:
            url = reverse(url_name, args=args, kwargs=kwargs)
        except NoReverseMatch as e:
            return {
                'status': 'FAILED',
                'url_name': url_name,
                'error': f'URL not found: {e}',
                'url': None
            }
        
        # Login if user provided
        if user:
            self.client.force_login(user)
        else:
            self.client.logout()
        
        # Make request
        try:
            if method == 'GET':
                response = self.client.get(url, follow=True)
            elif method == 'POST':
                response = self.client.post(url, data, follow=True)
            
            # Check response
            result = {
                'status': 'PASSED',
                'url_name': url_name,
                'url': url,
                'status_code': response.status_code,
                'user': user.username if user else 'Anonymous',
                'redirects': len(response.redirect_chain) if hasattr(response, 'redirect_chain') else 0
            }
            
            # Check for errors
            if response.status_code >= 500:
                result['status'] = 'FAILED'
                result['error'] = f'Server error: {response.status_code}'
            elif response.status_code == 404:
                result['status'] = 'FAILED'
                result['error'] = 'Page not found'
            elif response.status_code == 403:
                result['status'] = 'WARNING'
                result['error'] = 'Access denied (expected for some pages)'
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'url_name': url_name,
                'url': url,
                'error': str(e),
                'user': user.username if user else 'Anonymous'
            }
    
    def run_tests(self):
        """Run all page tests"""
        print("=" * 80)
        print("COMPREHENSIVE PAGE TEST - BUFIA SYSTEM")
        print("=" * 80)
        print()
        
        # Create test users
        print("Setting up test users...")
        self.create_test_users()
        print(f"✅ Regular user: {self.regular_user.username}")
        print(f"✅ Admin user: {self.admin_user.username}")
        print()
        
        # Define test cases
        test_cases = [
            # Public pages (no login required)
            ('PUBLIC PAGES', None, [
                ('home', [], {}),
                ('account_login', [], {}),
                ('account_signup', [], {}),
            ]),
            
            # Regular user pages
            ('REGULAR USER PAGES', self.regular_user, [
                ('dashboard', [], {}),
                ('profile', [], {}),
                ('account_email', [], {}),
                ('machines:machine_list', [], {}),
                ('machines:ricemill_appointment_list', [], {}),
                ('machines:rental_list', [], {}),
                ('irrigation:irrigation_request_list', [], {}),
                ('notifications:user_notifications', [], {}),
            ]),
            
            # Admin pages
            ('ADMIN PAGES', self.admin_user, [
                ('dashboard', [], {}),
                ('user_list', [], {}),
                ('machines:maintenance_list', [], {}),
                ('notifications:send_notification', [], {}),
                ('activity_logs:logs', [], {}),
                ('reports:user_activity_report', [], {}),
                ('reports:machine_usage_report', [], {}),
                ('reports:rice_mill_scheduling_report', [], {}),
                ('general_reports:dashboard', [], {}),
                ('admin:index', [], {}),
            ]),
        ]
        
        # Run tests
        for section_name, user, urls in test_cases:
            print(f"\n{'=' * 80}")
            print(f"{section_name}")
            print(f"{'=' * 80}")
            
            for url_name, args, kwargs in urls:
                result = self.test_url(url_name, args, kwargs, user)
                
                # Print result
                status_icon = {
                    'PASSED': '✅',
                    'FAILED': '❌',
                    'WARNING': '⚠️'
                }.get(result['status'], '❓')
                
                print(f"{status_icon} {url_name:45} ", end='')
                
                if result['status'] == 'PASSED':
                    print(f"[{result['status_code']}] {result['url']}")
                    self.results['passed'].append(result)
                elif result['status'] == 'WARNING':
                    print(f"[{result.get('status_code', 'N/A')}] {result.get('error', 'Unknown')}")
                    self.results['warnings'].append(result)
                else:
                    print(f"ERROR: {result.get('error', 'Unknown')}")
                    self.results['failed'].append(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Passed:   {len(self.results['passed'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"❌ Failed:   {len(self.results['failed'])}")
        print()
        
        if self.results['failed']:
            print("FAILED TESTS:")
            for result in self.results['failed']:
                print(f"  ❌ {result['url_name']}")
                print(f"     Error: {result.get('error', 'Unknown')}")
                print(f"     User: {result.get('user', 'N/A')}")
                print()
        
        if self.results['warnings']:
            print("WARNINGS:")
            for result in self.results['warnings']:
                print(f"  ⚠️  {result['url_name']}")
                print(f"     {result.get('error', 'Unknown')}")
                print()
        
        # Exit code
        if self.results['failed']:
            print("❌ Some tests failed!")
            return 1
        else:
            print("✅ All tests passed!")
            return 0

if __name__ == '__main__':
    tester = PageTester()
    exit_code = tester.run_tests()
    exit(exit_code)
