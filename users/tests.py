from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import get_user_model
from .decorators import verified_member_required
from django.http import HttpResponse

User = get_user_model()

class VerificationTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create test users
        self.regular_user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            password='testpassword123',
            is_verified=False
        )
        
        self.verified_user = User.objects.create_user(
            username='verifieduser',
            email='verified@example.com',
            password='testpassword123',
            is_verified=True
        )
        
        self.president_user = User.objects.create_user(
            username='president',
            email='president@example.com',
            password='testpassword123',
            role='president',
            is_verified=False  # Even though not verified, should have access
        )
        
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='testpassword123',
            is_superuser=True,
            is_verified=False  # Even though not verified, should have access
        )
    
    def test_verified_member_decorator(self):
        """Test the verified_member_required decorator"""
        
        # Create a simple test view that returns a success response
        @verified_member_required
        def test_view(request):
            return HttpResponse("Success")
        
        # Test with unverified user
        request = self.factory.get('/test-url/')
        request.user = self.regular_user
        
        # Add session and messages middleware support to request
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        
        response = test_view(request)
        # Should redirect to profile
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('profile'))
        
        # Test with verified user
        request = self.factory.get('/test-url/')
        request.user = self.verified_user
        response = test_view(request)
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")
        
        # Test with president user (should bypass verification)
        request = self.factory.get('/test-url/')
        request.user = self.president_user
        response = test_view(request)
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")
        
        # Test with admin user (should bypass verification)
        request = self.factory.get('/test-url/')
        request.user = self.admin_user
        response = test_view(request)
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")
        
    def test_verification_middleware(self):
        """Test the verification middleware"""
        # Login as unverified user
        self.client.login(username='testuser', password='testpassword123')
        
        # Try to access rental creation page - this should redirect due to middleware
        response = self.client.get(reverse('machines:rental_create'))
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Test verification bypass for admin users
        self.client.login(username='president', password='testpassword123')
        response = self.client.get(reverse('machines:rental_create'))
        self.assertNotEqual(response.status_code, 403)  # Should not be forbidden
        
        self.client.login(username='adminuser', password='testpassword123')
        response = self.client.get(reverse('machines:rental_create'))
        self.assertNotEqual(response.status_code, 403)  # Should not be forbidden
