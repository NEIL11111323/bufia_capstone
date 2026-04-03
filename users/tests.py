from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import get_user_model
from unittest.mock import patch
from bufia.models import Payment
from bufia.services.payments import record_membership_online_payment
from .decorators import verified_member_required
from .models import MembershipApplication
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
        )
        self.verified_user.is_verified = True
        self.verified_user.save(update_fields=['is_verified'])
        
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
            is_staff=True,
            is_verified=False  # Even though not verified, should have access
        )

    def _prepare_request(self, path, user):
        request = self.factory.get(path)
        request.user = user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        return request
    
    def test_verified_member_decorator(self):
        """Test the verified_member_required decorator"""
        
        # Create a simple test view that returns a success response
        @verified_member_required
        def test_view(request):
            return HttpResponse("Success")
        
        # Test with unverified user
        request = self._prepare_request('/test-url/', self.regular_user)
        response = test_view(request)
        # Should redirect to profile
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('profile'))
        
        # Test with verified user
        request = self._prepare_request('/test-url/', self.verified_user)
        response = test_view(request)
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")
        
        # President does not bypass this decorator unless separately verified
        request = self._prepare_request('/test-url/', self.president_user)
        response = test_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('profile'))
        
        # Test with admin user (should bypass verification)
        request = self._prepare_request('/test-url/', self.admin_user)
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
        self.assertEqual(response.status_code, 403)
        
        # President account still lacks the machine permissions required by the target view
        self.client.login(username='president', password='testpassword123')
        response = self.client.get(reverse('machines:rental_create'))
        self.assertEqual(response.status_code, 403)
        
        self.client.login(username='adminuser', password='testpassword123')
        response = self.client.get(reverse('machines:rental_create'))
        self.assertNotEqual(response.status_code, 403)  # Should not be forbidden


class MembershipPaymentFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='memberuser',
            email='member@example.com',
            password='testpassword123',
        )
        self.membership = MembershipApplication.objects.create(
            user=self.user,
            middle_name='Q',
            gender='female',
            civil_status='single',
            education='college',
            sitio='Sitio 1',
            barangay='Barangay 1',
            city='Leganes',
            province='Iloilo',
            ownership_type='owned',
            farm_location='Farm 1',
            bufia_farm_location='BUFIA Area',
            farm_size=1.5,
            payment_method='online',
            payment_status='pending',
        )
        self.client.force_login(self.user)

    def test_cancelled_membership_payment_returns_to_form(self):
        response = self.client.get(reverse('payment_cancelled'), {
            'type': 'membership',
            'id': self.membership.pk,
        })

        self.assertRedirects(response, reverse('submit_membership_form'), fetch_redirect_response=False)

    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.retrieve')
    def test_membership_success_requires_complete_paid_session(self, mock_retrieve, _mock_configured):
        class FakeSession(dict):
            def __getattr__(self, item):
                return self[item]

        mock_retrieve.return_value = FakeSession(
            status='open',
            payment_status='unpaid',
            amount_total=50000,
            payment_intent='pi_test_incomplete',
        )

        response = self.client.get(reverse('payment_success'), {
            'session_id': 'cs_test_incomplete',
            'type': 'membership',
            'id': self.membership.pk,
        })

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.payment_status, 'pending')
        self.assertIsNone(self.membership.payment_date)
        self.assertRedirects(response, reverse('submit_membership_form'), fetch_redirect_response=False)

    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.retrieve')
    def test_membership_success_marks_paid_only_when_complete(self, mock_retrieve, _mock_configured):
        class FakeSession(dict):
            def __getattr__(self, item):
                return self[item]

        mock_retrieve.return_value = FakeSession(
            status='complete',
            payment_status='paid',
            amount_total=50000,
            payment_intent='pi_test_complete',
        )

        response = self.client.get(reverse('payment_success'), {
            'session_id': 'cs_test_complete',
            'type': 'membership',
            'id': self.membership.pk,
        })

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.payment_status, 'paid')
        self.assertEqual(self.membership.payment_method, 'online')
        self.assertIsNotNone(self.membership.payment_date)
        self.assertRedirects(response, reverse('membership_slip'), fetch_redirect_response=False)


class MembershipPaymentServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='serviceuser',
            email='service@example.com',
            password='testpassword123',
        )
        self.membership = MembershipApplication.objects.create(
            user=self.user,
            middle_name='R',
            gender='male',
            civil_status='single',
            education='college',
            sitio='Sitio 2',
            barangay='Barangay 2',
            city='Leganes',
            province='Iloilo',
            ownership_type='owned',
            farm_location='Farm 2',
            bufia_farm_location='BUFIA Zone',
            farm_size=2,
            payment_method='online',
            payment_status='pending',
        )

    def test_record_membership_online_payment_updates_membership_and_payment_record(self):
        payment_obj = record_membership_online_payment(
            self.membership,
            self.user,
            'cs_service_test',
            payment_intent_id='pi_service_test',
        )

        self.membership.refresh_from_db()
        payment_obj.refresh_from_db()

        self.assertEqual(self.membership.payment_status, 'paid')
        self.assertEqual(self.membership.payment_method, 'online')
        self.assertIsNotNone(self.membership.payment_date)
        self.assertEqual(payment_obj.payment_type, 'membership')
        self.assertEqual(payment_obj.status, 'completed')
        self.assertEqual(payment_obj.currency, 'PHP')
        self.assertEqual(str(payment_obj.amount), '500.00')
        self.assertEqual(payment_obj.stripe_session_id, 'cs_service_test')
        self.assertEqual(payment_obj.stripe_payment_intent_id, 'pi_service_test')

    def test_record_membership_online_payment_reuses_existing_payment_record(self):
        first_payment = record_membership_online_payment(
            self.membership,
            self.user,
            'cs_service_test_1',
            payment_intent_id='pi_service_test_1',
        )
        second_payment = record_membership_online_payment(
            self.membership,
            self.user,
            'cs_service_test_2',
            payment_intent_id='pi_service_test_2',
            paid_amount=750,
        )

        self.assertEqual(first_payment.pk, second_payment.pk)
        self.assertEqual(
            Payment.objects.filter(
                user=self.user,
                payment_type='membership',
            ).count(),
            1,
        )
        second_payment.refresh_from_db()
        self.assertEqual(str(second_payment.amount), '750.00')
        self.assertEqual(second_payment.stripe_session_id, 'cs_service_test_2')
        self.assertEqual(second_payment.stripe_payment_intent_id, 'pi_service_test_2')
