import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch
from decimal import Decimal
from urllib.parse import quote
from bufia.models import Payment
from bufia.services.payments import record_membership_online_payment
from notifications.models import UserNotification
from .decorators import verified_member_required
from .models import ActivityLog, MembershipApplication, MembershipApplicationProof, Sector
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

    def test_must_change_password_user_can_open_profile_without_redirect_loop(self):
        self.regular_user.must_change_password = True
        self.regular_user.save(update_fields=['must_change_password'])

        self.client.force_login(self.regular_user)

        profile_response = self.client.get(reverse('profile'))
        self.assertEqual(profile_response.status_code, 200)

        dashboard_response = self.client.get(reverse('dashboard'), follow=True)
        self.assertEqual(dashboard_response.redirect_chain[0][0], reverse('change_password'))
        self.assertEqual(dashboard_response.status_code, 200)


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


class MembershipLandProofUploadFlowTestCase(TestCase):
    def setUp(self):
        self.media_root_base = os.path.join(settings.BASE_DIR, 'tmp_test_media')
        os.makedirs(self.media_root_base, exist_ok=True)
        self.media_root = os.path.join(self.media_root_base, f'{self.__class__.__name__}_{self._testMethodName}')
        os.makedirs(self.media_root, exist_ok=True)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        self.user = User.objects.create_user(
            username='landproofuser',
            email='landproof@example.com',
            password='testpassword123',
            first_name='Land',
            last_name='Owner',
            phone_number='09171234567',
        )
        self.admin = User.objects.create_superuser(
            username='landproofadmin',
            email='landproofadmin@example.com',
            password='testpassword123',
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_submit_membership_form_saves_land_proof_and_notes(self):
        self.client.force_login(self.user)
        proof_file = SimpleUploadedFile(
            'land-proof.jpg',
            b'fake-image-bytes',
            content_type='image/jpeg',
        )
        valid_id_file = SimpleUploadedFile(
            'valid-id.jpg',
            b'valid-id-bytes',
            content_type='image/jpeg',
        )
        profile_photo = SimpleUploadedFile(
            'profile-photo.jpg',
            b'profile-photo-bytes',
            content_type='image/jpeg',
        )

        response = self.client.post(
            reverse('submit_membership_form'),
            {
                'first_name': 'Land',
                'middle_name': 'P',
                'last_name': 'Owner',
                'email': 'landproof@example.com',
                'phone_number': '09171234567',
                'gender': 'male',
                'birthdate': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'national_id_number': '1234-5678-9012',
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Uno',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership': 'owned',
                'farm_size': '2.50',
                'land_owner': '',
                'farm_manager': '',
                'farm_location': 'Farm Lot 5',
                'bufia_farm_location': 'BUFIA Block 2',
                'land_proof_notes': 'Inherited farm under family ownership.',
                'land_proof_document': proof_file,
                'valid_id_document': valid_id_file,
                'profile_photo': profile_photo,
                'payment_method': 'face_to_face',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        application = MembershipApplication.objects.get(user=self.user)
        self.assertEqual(application.land_proof_notes, 'Inherited farm under family ownership.')
        self.assertEqual(application.place_of_birth, 'Iloilo')
        self.assertEqual(application.national_id_number, '1234-5678-9012')
        self.assertTrue(application.land_proof_document.name.endswith('land-proof.jpg'))

    def test_submit_membership_form_saves_up_to_two_land_proofs(self):
        self.client.force_login(self.user)
        proof_file_1 = SimpleUploadedFile('land-proof-1.jpg', b'proof-1', content_type='image/jpeg')
        proof_file_2 = SimpleUploadedFile('land-proof-2.png', b'proof-2', content_type='image/png')
        valid_id_file = SimpleUploadedFile('valid-id.pdf', b'valid-id', content_type='application/pdf')
        profile_photo = SimpleUploadedFile('profile-photo.png', b'profile-photo', content_type='image/png')

        response = self.client.post(
            reverse('submit_membership_form'),
            {
                'first_name': 'Land',
                'middle_name': 'P',
                'last_name': 'Owner',
                'email': 'landproof@example.com',
                'phone_number': '09171234567',
                'gender': 'male',
                'birthdate': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'national_id_number': '1234-5678-9012',
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Uno',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership': 'owned',
                'farm_size': '2.50',
                'land_owner': '',
                'farm_manager': '',
                'farm_location': 'Farm Lot 5',
                'bufia_farm_location': 'BUFIA Block 2',
                'land_proof_notes': 'Uploaded two proof files for review.',
                'land_proof_documents': [proof_file_1, proof_file_2],
                'valid_id_document': valid_id_file,
                'profile_photo': profile_photo,
                'payment_method': 'face_to_face',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        application = MembershipApplication.objects.get(user=self.user)
        self.assertEqual(application.land_proof_count, 2)
        self.assertEqual(application.proof_documents.count(), 2)
        self.assertEqual(
            [proof.filename for proof in application.proof_documents.all()],
            ['land-proof-1.jpg', 'land-proof-2.png'],
        )

    def test_submit_membership_form_resubmission_replaces_existing_land_proofs(self):
        self.client.force_login(self.user)

        first_proof = SimpleUploadedFile('old-proof.jpg', b'old-proof', content_type='image/jpeg')
        second_proof = SimpleUploadedFile('new-proof.pdf', b'%PDF-new-proof', content_type='application/pdf')
        valid_id_file = SimpleUploadedFile('valid-id.jpg', b'valid-id', content_type='image/jpeg')
        profile_photo = SimpleUploadedFile('profile-photo.jpg', b'profile-photo', content_type='image/jpeg')

        first_response = self.client.post(
            reverse('submit_membership_form'),
            {
                'first_name': 'Land',
                'middle_name': 'P',
                'last_name': 'Owner',
                'email': 'landproof@example.com',
                'phone_number': '09171234567',
                'gender': 'male',
                'birthdate': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'national_id_number': '1234-5678-9012',
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Uno',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership': 'owned',
                'farm_size': '2.50',
                'land_owner': '',
                'farm_manager': '',
                'farm_location': 'Farm Lot 5',
                'bufia_farm_location': 'BUFIA Block 2',
                'land_proof_documents': [first_proof],
                'valid_id_document': valid_id_file,
                'profile_photo': profile_photo,
                'payment_method': 'face_to_face',
            },
            follow=False,
        )

        self.assertEqual(first_response.status_code, 302)

        second_response = self.client.post(
            reverse('submit_membership_form'),
            {
                'first_name': 'Land',
                'middle_name': 'P',
                'last_name': 'Owner',
                'email': 'landproof@example.com',
                'phone_number': '09171234567',
                'gender': 'male',
                'birthdate': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'national_id_number': '1234-5678-9012',
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Uno',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership': 'owned',
                'farm_size': '2.50',
                'land_owner': '',
                'farm_manager': '',
                'farm_location': 'Farm Lot 6',
                'bufia_farm_location': 'BUFIA Block 3',
                'land_proof_documents': [second_proof],
                'valid_id_document': SimpleUploadedFile('valid-id-updated.jpg', b'valid-id-2', content_type='image/jpeg'),
                'profile_photo': SimpleUploadedFile('profile-photo-updated.jpg', b'profile-photo-2', content_type='image/jpeg'),
                'payment_method': 'face_to_face',
            },
            follow=False,
        )

        self.assertEqual(second_response.status_code, 302)

        application = MembershipApplication.objects.get(user=self.user)
        self.assertEqual(application.land_proof_count, 1)
        self.assertEqual(application.proof_documents.count(), 1)
        self.assertEqual(
            [proof.filename for proof in application.proof_documents.all()],
            ['new-proof.pdf'],
        )
        self.assertTrue(application.land_proof_document.name.endswith('new-proof.pdf'))

    def test_admin_review_page_shows_uploaded_land_proof(self):
        application = MembershipApplication.objects.create(
            user=self.user,
            is_current=True,
            middle_name='P',
            gender='male',
            civil_status='single',
            education='college',
            sitio='Sitio Uno',
            barangay='Barangay Uno',
            city='Leganes',
            province='Iloilo',
            ownership_type='owned',
            farm_location='Farm Lot 5',
            farm_size=Decimal('2.50'),
            land_proof_notes='This is a clear copy of the tax declaration.',
        )
        application.land_proof_document.save(
            'land-proof.jpg',
            SimpleUploadedFile('land-proof.jpg', b'fake-image-bytes', content_type='image/jpeg'),
            save=True,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('review_application', args=[application.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supporting Documents Review')
        self.assertContains(response, 'This is a clear copy of the tax declaration.')
        self.assertContains(response, 'land-proof.jpg')

    def test_admin_review_page_lists_multiple_uploaded_land_proofs(self):
        application = MembershipApplication.objects.create(
            user=self.user,
            is_current=True,
            land_proof_notes='Multiple ownership proof files uploaded.',
        )
        MembershipApplicationProof.objects.create(
            application=application,
            document=SimpleUploadedFile('first-proof.jpg', b'proof-1', content_type='image/jpeg'),
            display_order=0,
        )
        MembershipApplicationProof.objects.create(
            application=application,
            document=SimpleUploadedFile('second-proof.pdf', b'proof-2', content_type='application/pdf'),
            display_order=1,
        )
        application.land_proof_document = application.proof_documents.first().document.name
        application.save(update_fields=['land_proof_document'])

        self.client.force_login(self.admin)
        response = self.client.get(reverse('review_application', args=[application.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Proof 1: first-proof.jpg')
        self.assertContains(response, 'Proof 2: second-proof.pdf')

    def test_invalid_land_proof_extension_is_rejected(self):
        self.client.force_login(self.user)
        invalid_file = SimpleUploadedFile(
            'land-proof.exe',
            b'bad-file',
            content_type='application/octet-stream',
        )
        valid_id_file = SimpleUploadedFile(
            'valid-id.jpg',
            b'valid-id',
            content_type='image/jpeg',
        )
        profile_photo = SimpleUploadedFile(
            'profile-photo.jpg',
            b'profile-photo',
            content_type='image/jpeg',
        )

        response = self.client.post(
            reverse('submit_membership_form'),
            {
                'first_name': 'Land',
                'middle_name': 'P',
                'last_name': 'Owner',
                'email': 'landproof@example.com',
                'phone_number': '09171234567',
                'gender': 'male',
                'birthdate': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'national_id_number': '1234-5678-9012',
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Uno',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership': 'owned',
                'farm_size': '2.50',
                'land_owner': '',
                'farm_manager': '',
                'farm_location': 'Farm Lot 5',
                'bufia_farm_location': 'BUFIA Block 2',
                'land_proof_notes': 'Should fail validation.',
                'land_proof_document': invalid_file,
                'valid_id_document': valid_id_file,
                'profile_photo': profile_photo,
                'payment_method': 'face_to_face',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload a PDF, JPG, JPEG, or PNG file.')
        self.assertFalse(MembershipApplication.objects.filter(user=self.user).exists())


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


class MembershipReviewPaymentControlsTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='reviewadmin',
            email='reviewadmin@example.com',
            password='testpassword123',
            is_superuser=True,
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='reviewmember',
            email='reviewmember@example.com',
            password='testpassword123',
            first_name='Neil',
            last_name='Valiao',
        )
        self.sector = Sector.objects.order_by('sector_number').first()
        if self.sector is None:
            self.sector = Sector.objects.create(sector_number=99, name='Test Sector')
        self.client.force_login(self.admin_user)

    def test_review_page_shows_confirm_payment_for_face_to_face_pending_application(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='pending',
        )

        response = self.client.get(reverse('review_application', args=[application.pk]))

        self.assertContains(response, 'Confirm Payment Received')
        self.assertContains(response, 'Approve Membership', html=False)
        self.assertContains(response, 'disabled')

    def test_review_page_blocks_online_application_until_payment_is_complete(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='online',
            payment_status='pending',
        )

        response = self.client.get(reverse('review_application', args=[application.pk]))

        self.assertContains(response, 'Waiting for online payment')
        self.assertNotContains(response, 'Confirm Payment Received')
        self.assertContains(response, 'disabled')

    def test_mark_membership_paid_rejects_manual_confirmation_for_online_payment(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='online',
            payment_status='pending',
        )

        response = self.client.post(
            reverse('mark_membership_paid', args=[self.member.pk]),
            {'next': reverse('review_application', args=[application.pk])},
        )

        application.refresh_from_db()
        self.assertEqual(application.payment_status, 'pending')
        self.assertRedirects(
            response,
            reverse('review_application', args=[application.pk]),
            fetch_redirect_response=False,
        )

    def test_mark_membership_paid_redirects_back_to_review_for_face_to_face(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='pending',
        )

        response = self.client.post(
            reverse('mark_membership_paid', args=[self.member.pk]),
            {'next': reverse('review_application', args=[application.pk])},
        )

        application.refresh_from_db()
        payment = Payment.objects.get(
            user=self.member,
            payment_type='membership',
            object_id=application.pk,
        )
        self.assertEqual(application.payment_status, 'paid')
        self.assertEqual(application.payment_method, 'face_to_face')
        self.assertIsNotNone(application.payment_date)
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(str(payment.amount), '500.00')
        self.assertEqual(str(payment.amount_received), '500.00')
        self.assertEqual(payment.processed_by, self.admin_user)
        self.assertRedirects(
            response,
            reverse('review_application', args=[application.pk]),
            fetch_redirect_response=False,
        )

    def test_review_page_prefills_editable_default_approval_note(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='paid',
        )

        response = self.client.get(reverse('review_application', args=[application.pk]))

        self.assertContains(
            response,
            'Your membership has been approved. Welcome to BUFIA, Neil Valiao!',
        )
        self.assertContains(
            response,
            'You can edit this message before approving. It will be sent to the applicant.',
        )

    def test_approve_application_uses_custom_approval_note_for_notification(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='paid',
        )

        response = self.client.post(
            reverse('approve_application', args=[application.pk]),
            {
                'assigned_sector': self.sector.pk,
                'rcba_number': 'RCBA-2026-001',
                'approval_notes': 'Approved and ready for member services.',
            },
        )

        application.refresh_from_db()
        self.member.refresh_from_db()
        notification = UserNotification.objects.filter(user=self.member).latest('timestamp')

        self.assertTrue(application.is_approved)
        self.assertEqual(application.assigned_sector, self.sector)
        self.assertEqual(application.rcba_number, 'RCBA-2026-001')
        self.assertTrue(self.member.is_verified)
        self.assertEqual(notification.message, 'Approved and ready for member services.')
        self.assertRedirects(
            response,
            reverse('registration_dashboard'),
            fetch_redirect_response=False,
        )

    def test_approve_application_requires_rcba_number(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='paid',
        )

        response = self.client.post(
            reverse('approve_application', args=[application.pk]),
            {
                'assigned_sector': self.sector.pk,
                'approval_notes': 'Approved and ready for member services.',
            },
            follow=True,
        )

        application.refresh_from_db()
        self.member.refresh_from_db()

        self.assertFalse(application.is_approved)
        self.assertFalse(self.member.is_verified)
        self.assertIsNone(application.rcba_number)
        self.assertContains(response, 'RCBA number is required before approving this application.')

    def test_registration_dashboard_marks_missing_land_proof_file_instead_of_linking_to_media(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='paid',
        )
        application.land_proof_document.name = 'membership/land_proofs/7.jpg'
        application.save(update_fields=['land_proof_document'])

        response = self.client.get(reverse('registration_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Missing file')
        self.assertNotContains(response, '/media/membership/land_proofs/7.jpg')

    def test_approve_application_falls_back_to_default_approval_note_when_blank(self):
        application = MembershipApplication.objects.create(
            user=self.member,
            payment_method='face_to_face',
            payment_status='paid',
        )

        self.client.post(
            reverse('approve_application', args=[application.pk]),
            {
                'assigned_sector': self.sector.pk,
                'rcba_number': 'RCBA-2026-002',
                'approval_notes': '   ',
            },
        )

        notification = UserNotification.objects.filter(user=self.member).latest('timestamp')
        self.assertEqual(
            notification.message,
            'Your membership has been approved. Welcome to BUFIA, Neil Valiao!',
        )


class MembersMasterlistFlowTestCase(TestCase):
    def setUp(self):
        self.media_root_base = os.path.join(settings.BASE_DIR, 'tmp_test_media')
        os.makedirs(self.media_root_base, exist_ok=True)
        self.media_root = os.path.join(self.media_root_base, f'{self.__class__.__name__}_{self._testMethodName}')
        os.makedirs(self.media_root, exist_ok=True)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        self.admin = User.objects.create_user(
            username='masteradmin',
            email='masteradmin@example.com',
            password='testpassword123',
            is_superuser=True,
            is_staff=True,
        )
        self.sector, _ = Sector.objects.get_or_create(
            sector_number=1,
            defaults={
                'name': 'Sector 1',
                'description': 'North cluster',
            },
        )
        self.member_user = User.objects.create_user(
            username='juanmember',
            email='juanmember@example.com',
            password='testpassword123',
            first_name='Juan',
            last_name='Dela Cruz',
            phone_number='09171234567',
            address='Barangay Proper',
            is_verified=True,
            membership_form_submitted=True,
        )
        self.member = MembershipApplication.objects.create(
            user=self.member_user,
            middle_name='S',
            is_current=True,
            is_approved=True,
            assigned_sector=self.sector,
            farm_location='Farm Lot 8',
            bufia_farm_location='BUFIA Block A',
            farm_size=Decimal('2.50'),
        )
        self.client.force_login(self.admin)

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_masterlist_action_links_preserve_current_filters(self):
        response = self.client.get(reverse('members_masterlist'), {
            'sector': 'all',
            'q': 'juan',
        })

        self.assertEqual(response.status_code, 200)
        expected_next = quote('/members/masterlist/?sector=all&q=juan', safe='/')
        self.assertContains(response, reverse("view_membership_info_user", args=[self.member_user.id]))
        self.assertContains(response, reverse("edit_user", args=[self.member_user.id]))
        self.assertContains(response, reverse("delete_user", args=[self.member_user.id]))
        self.assertContains(response, expected_next)

    def test_masterlist_accepts_sector_id_alias_and_keeps_next_flow(self):
        response = self.client.get(reverse('members_masterlist'), {
            'sector_id': str(self.sector.id),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_sector'], str(self.sector.id))
        self.assertEqual(response.context['filtered_members_count'], 1)
        self.assertNotContains(response, 'Quick View')
        self.assertNotContains(response, 'view-profile-btn')
        expected_next = quote(f'/members/masterlist/?sector_id={self.sector.id}', safe='/')
        self.assertContains(response, expected_next)

    def test_masterlist_sector_counts_follow_search_query(self):
        other_sector, _ = Sector.objects.get_or_create(
            sector_number=2,
            defaults={
                'name': 'Sector 2',
                'description': 'South cluster',
            },
        )
        other_user = User.objects.create_user(
            username='pedromember',
            email='pedro@example.com',
            password='testpassword123',
            first_name='Pedro',
            last_name='Santos',
            is_verified=True,
            membership_form_submitted=True,
        )
        MembershipApplication.objects.create(
            user=other_user,
            is_current=True,
            is_approved=True,
            assigned_sector=other_sector,
        )

        response = self.client.get(reverse('members_masterlist'), {
            'q': 'juan',
        })

        self.assertEqual(response.status_code, 200)
        sector_counts = {item['id']: item['count'] for item in response.context['sector_summaries']}
        self.assertEqual(sector_counts['all'], 1)
        self.assertEqual(sector_counts[str(self.sector.id)], 1)
        self.assertEqual(sector_counts[str(other_sector.id)], 0)
        self.assertEqual(response.context['visible_sector_count'], 1)
        self.assertEqual(len(response.context['member_groups']), 1)
        self.assertEqual(response.context['member_groups'][0]['label'], self.sector.name)

    def test_unassigned_filter_stays_selected_when_search_has_no_matches(self):
        other_user = User.objects.create_user(
            username='unassignedmember',
            email='unassigned@example.com',
            password='testpassword123',
            first_name='Maria',
            last_name='Lopez',
            is_verified=True,
            membership_form_submitted=True,
        )
        MembershipApplication.objects.create(
            user=other_user,
            is_current=True,
            is_approved=True,
            assigned_sector=None,
        )

        response = self.client.get(reverse('members_masterlist'), {
            'sector': 'unassigned',
            'q': 'nomatch',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_sector'], 'unassigned')
        self.assertEqual(response.context['filtered_members_count'], 0)

    def test_user_profile_api_returns_real_membership_data(self):
        response = self.client.get(reverse('get_user_profile_data', args=[self.member_user.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['fullName'], 'Juan Dela Cruz')
        self.assertEqual(payload['verificationStatusText'], 'Verified')
        self.assertEqual(payload['ma_assignedSector'], self.sector.name)
        self.assertEqual(payload['ma_farmLocation'], 'Farm Lot 8')
        self.assertEqual(payload['detailsUrl'], reverse('view_membership_info_user', args=[self.member_user.id]))

    def test_membership_info_back_button_uses_masterlist_next_url(self):
        next_url = '/members/masterlist/?sector=all'
        response = self.client.get(
            reverse('view_membership_info_user', args=[self.member_user.id]),
            {'next': next_url},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to Masterlist')
        self.assertContains(response, f'href="{next_url}"', html=False)

    def test_delete_user_redirects_back_to_filtered_masterlist(self):
        next_url = '/members/masterlist/?sector=all&q=juan'

        response = self.client.post(
            reverse('delete_user', args=[self.member_user.id]),
            {'next': next_url},
        )

        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=self.member_user.pk).exists())

    def test_export_members_buttons_return_downloads(self):
        csv_response = self.client.get(reverse('export_members_csv'), {
            'sector': 'all',
            'q': 'juan',
        })
        pdf_response = self.client.get(reverse('export_members_pdf'), {
            'sector': 'all',
            'q': 'juan',
        })

        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('text/csv', csv_response['Content-Type'])
        self.assertIn('Dela Cruz, Juan', csv_response.content.decode('utf-8'))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertIn('application/pdf', pdf_response['Content-Type'])

    def test_export_members_pdf_preview_returns_inline_header(self):
        response = self.client.get(reverse('export_members_pdf'), {
            'sector': 'all',
            'q': 'juan',
            'preview': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response['Content-Type'])
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))

    def test_edit_user_requires_assigned_sector_when_marking_member_verified(self):
        response = self.client.post(
            reverse('edit_user', args=[self.member_user.id]),
            {
                'username': self.member_user.username,
                'email': self.member_user.email,
                'first_name': self.member_user.first_name,
                'last_name': self.member_user.last_name,
                'role': self.member_user.role,
                'phone_number': self.member_user.phone_number,
                'address': self.member_user.address,
                'assigned_sector': '',
                'is_verified': 'on',
                'membership_form_submitted': 'on',
                'membership_form_date': '',
                'membership_approved_date': '',
                'membership_rejected_reason': '',
                'password': '',
                'confirm_password': '',
                'next': f'/members/masterlist/?sector_id={self.sector.id}',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assigned sector is required before a member can be marked as verified.')
        self.member.refresh_from_db()
        self.assertEqual(self.member.assigned_sector, self.sector)

    def test_edit_user_page_includes_membership_application_fields(self):
        response = self.client.get(reverse('edit_user', args=[self.member_user.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Membership Application Details')
        self.assertContains(response, 'name="place_of_birth"')
        self.assertContains(response, 'name="farm_location"')
        self.assertContains(response, 'name="land_proof_document"')
        self.assertContains(response, 'name="land_proof_notes"')
        self.assertContains(response, 'name="payment_status"')

    def test_edit_user_page_shows_missing_land_proof_message_without_media_link(self):
        self.member.land_proof_document.name = 'membership/land_proofs/7.jpg'
        self.member.save(update_fields=['land_proof_document'])

        response = self.client.get(reverse('edit_user', args=[self.member_user.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current proof file is missing from storage.')
        self.assertNotContains(response, '/media/membership/land_proofs/7.jpg')

    def test_edit_user_redirects_back_to_sector_id_masterlist_and_syncs_membership(self):
        next_url = f'/members/masterlist/?sector_id={self.sector.id}'

        response = self.client.post(
            reverse('edit_user', args=[self.member_user.id]),
            {
                'username': self.member_user.username,
                'email': self.member_user.email,
                'first_name': self.member_user.first_name,
                'last_name': self.member_user.last_name,
                'role': self.member_user.role,
                'phone_number': self.member_user.phone_number,
                'address': 'Updated member address',
                'assigned_sector': str(self.sector.id),
                'is_verified': 'on',
                'membership_form_date': '',
                'membership_approved_date': '',
                'membership_rejected_reason': '',
                'password': '',
                'confirm_password': '',
                'next': next_url,
            },
        )

        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.member_user.refresh_from_db()
        self.member.refresh_from_db()
        self.assertTrue(self.member_user.is_verified)
        self.assertTrue(self.member_user.membership_form_submitted)
        self.assertTrue(self.member.is_approved)
        self.assertFalse(self.member.is_rejected)
        self.assertEqual(self.member.assigned_sector, self.sector)

    def test_edit_user_updates_membership_application_detail_fields(self):
        response = self.client.post(
            reverse('edit_user', args=[self.member_user.id]),
            {
                'username': self.member_user.username,
                'email': self.member_user.email,
                'first_name': self.member_user.first_name,
                'last_name': self.member_user.last_name,
                'role': self.member_user.role,
                'phone_number': self.member_user.phone_number,
                'address': self.member_user.address,
                'assigned_sector': str(self.sector.id),
                'membership_form_submitted': 'on',
                'membership_form_date': '',
                'membership_approved_date': '',
                'membership_rejected_reason': '',
                'middle_name': 'S',
                'gender': 'male',
                'birth_date': '1990-01-15',
                'place_of_birth': 'Bohol',
                'civil_status': 'married',
                'education': 'college',
                'sector': str(self.sector.id),
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Proper',
                'city': 'Tagbilaran',
                'province': 'Bohol',
                'is_tiller': 'on',
                'lot_number': 'LOT-55',
                'ownership_type': 'owned',
                'land_owner': 'Juan Dela Cruz',
                'farm_manager': 'Maria Dela Cruz',
                'farm_location': 'Farm Lot 10',
                'bufia_farm_location': 'BUFIA Block C',
                'farm_size': '3.75',
                'payment_method': 'face_to_face',
                'payment_status': 'paid',
                'password': '',
                'confirm_password': '',
                'next': '/members/masterlist/',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/members/masterlist/')
        self.member.refresh_from_db()
        self.assertEqual(self.member.place_of_birth, 'Bohol')
        self.assertEqual(self.member.city, 'Tagbilaran')
        self.assertEqual(self.member.farm_location, 'Farm Lot 10')
        self.assertEqual(self.member.bufia_farm_location, 'BUFIA Block C')
        self.assertEqual(str(self.member.farm_size), '3.75')
        self.assertEqual(self.member.payment_status, 'paid')
        self.assertIsNotNone(self.member.payment_date)
        payment = Payment.objects.get(
            user=self.member_user,
            payment_type='membership',
            object_id=self.member.pk,
        )
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(str(payment.amount), '500.00')

    def test_edit_user_updates_land_proof_document_and_notes(self):
        proof_file = SimpleUploadedFile(
            'admin-land-proof.pdf',
            b'%PDF-1.4 fake pdf bytes',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('edit_user', args=[self.member_user.id]),
            {
                'username': self.member_user.username,
                'email': self.member_user.email,
                'first_name': self.member_user.first_name,
                'last_name': self.member_user.last_name,
                'role': self.member_user.role,
                'phone_number': self.member_user.phone_number,
                'address': self.member_user.address,
                'assigned_sector': str(self.sector.id),
                'membership_form_submitted': 'on',
                'membership_form_date': '',
                'membership_approved_date': '',
                'membership_rejected_reason': '',
                'middle_name': self.member.middle_name,
                'gender': self.member.gender or 'male',
                'birth_date': '1990-01-15',
                'place_of_birth': 'Iloilo',
                'civil_status': 'single',
                'education': 'college',
                'sector': str(self.sector.id),
                'sitio': 'Sitio Uno',
                'barangay': 'Barangay Proper',
                'city': 'Leganes',
                'province': 'Iloilo',
                'ownership_type': 'owned',
                'land_owner': 'Juan Dela Cruz',
                'farm_manager': 'Maria Dela Cruz',
                'farm_location': 'Farm Lot 8',
                'bufia_farm_location': 'BUFIA Block A',
                'farm_size': '2.50',
                'land_proof_document': proof_file,
                'land_proof_notes': 'Admin uploaded a clearer copy for the record.',
                'payment_method': 'face_to_face',
                'payment_status': 'pending',
                'password': '',
                'confirm_password': '',
                'next': '/members/masterlist/',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.land_proof_notes, 'Admin uploaded a clearer copy for the record.')
        self.assertTrue(self.member.land_proof_document.name.endswith('admin-land-proof.pdf'))


class SectorFlowRegressionTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='sectoradmin',
            email='sectoradmin@example.com',
            password='testpassword123',
            is_superuser=True,
            is_staff=True,
        )
        Sector.objects.all().delete()
        self.sector = Sector.objects.create(
            sector_number=1,
            name='Original Sector Name',
            description='Original description',
            area_coverage='Original area',
            is_active=True,
        )
        self.client.force_login(self.admin)

    def test_edit_sector_updates_name_without_forcing_number_change(self):
        response = self.client.post(
            reverse('edit_sector', args=[self.sector.pk]),
            {
                'name': 'Sector 1-B',
                'description': 'Updated description',
                'area_coverage': 'Updated area',
                'is_active': 'on',
            },
        )

        self.assertRedirects(
            response,
            reverse('sector_detail', args=[self.sector.pk]),
            fetch_redirect_response=False,
        )
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.sector_number, 1)
        self.assertEqual(self.sector.name, 'Sector 1-B')
        self.assertEqual(self.sector.description, 'Updated description')
        self.assertEqual(self.sector.area_coverage, 'Updated area')
        self.assertTrue(self.sector.is_active)

    def test_sector_detail_shows_useful_actions_without_summary_report_button(self):
        response = self.client.get(reverse('sector_detail', args=[self.sector.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Members Masterlist')
        self.assertContains(response, 'Member List Report')
        self.assertContains(response, 'Edit Sector')
        self.assertContains(response, 'Back to Sectors')
        self.assertNotContains(response, 'Summary Report')


class ProfileRecentActivityFeedTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='activity-user',
            email='activity-user@example.com',
            password='testpassword123',
            first_name='Activity',
            last_name='User',
        )
        self.other_user = User.objects.create_user(
            username='other-activity-user',
            email='other-activity@example.com',
            password='testpassword123',
            first_name='Other',
            last_name='Member',
        )
        self.admin = User.objects.create_superuser(
            username='activity-admin',
            email='activity-admin@example.com',
            password='testpassword123',
        )

    def test_regular_profile_only_shows_personal_activity(self):
        ActivityLog.objects.create(
            actor=self.user,
            subject_user=self.user,
            activity_type=ActivityLog.TYPE_SUBMIT,
            visibility=ActivityLog.VISIBILITY_BOTH,
            title='Unique own activity entry',
            description='Should be visible to the owner.',
            created_at=timezone.now(),
        )
        ActivityLog.objects.create(
            actor=self.other_user,
            subject_user=self.other_user,
            activity_type=ActivityLog.TYPE_SUBMIT,
            visibility=ActivityLog.VISIBILITY_BOTH,
            title='Unique other activity entry',
            description='Should stay hidden from another user.',
            created_at=timezone.now(),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))

        titles = [item['title'] for item in response.context['recent_activities']]
        self.assertIn('Unique own activity entry', titles)
        self.assertNotIn('Unique other activity entry', titles)

    def test_admin_profile_shows_system_activity(self):
        ActivityLog.objects.create(
            actor=self.user,
            subject_user=self.user,
            activity_type=ActivityLog.TYPE_PAYMENT,
            visibility=ActivityLog.VISIBILITY_BOTH,
            title='Unique system payment activity',
            description='Admin should see this.',
            created_at=timezone.now(),
        )
        ActivityLog.objects.create(
            actor=self.other_user,
            subject_user=self.other_user,
            activity_type=ActivityLog.TYPE_APPROVE,
            visibility=ActivityLog.VISIBILITY_BOTH,
            title='Unique system approval activity',
            description='Admin should see this too.',
            created_at=timezone.now(),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('profile'))

        titles = [item['title'] for item in response.context['recent_activities']]
        self.assertIn('Unique system payment activity', titles)
        self.assertIn('Unique system approval activity', titles)


class WalkInMemberCreateViewTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='walkinadmin',
            email='walkinadmin@example.com',
            password='testpassword123',
            is_superuser=True,
            is_staff=True,
        )
        self.sector, _ = Sector.objects.get_or_create(
            sector_number=9,
            defaults={
                'name': 'Sector 9',
                'description': 'Walk-in assignment sector',
            },
        )
        self.client.force_login(self.admin)

    def _valid_payload(self, **overrides):
        payload = {
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'email': 'maria.walkin@example.com',
            'phone_number': '09171234567',
            'address': 'Barangay Proper',
            'middle_name': 'S',
            'gender': 'female',
            'birth_date': '1992-04-15',
            'civil_status': 'single',
            'education': 'college',
            'national_id_number': '9999-8888-7777',
            'sitio': 'Sitio Uno',
            'barangay': 'Barangay Proper',
            'city': 'Tagbilaran',
            'province': 'Bohol',
            'is_tiller': 'on',
            'ownership_type': 'owned',
            'land_owner': 'Maria Lopez',
            'farm_manager': '',
            'farm_location': 'Farm Lot 11',
            'bufia_farm_location': 'BUFIA Block D',
            'farm_size': '2.50',
            'land_proof_notes': 'Walk-in registration proof noted by admin.',
            'sector': str(self.sector.pk),
            'rcba_number': 'RCBA-2026-003',
            'payment_method': 'face_to_face',
            'payment_status': 'pending',
            'approve_if_ready': 'on',
        }
        payload.update(overrides)
        return payload

    def test_get_walkin_member_page_renders_both_forms(self):
        response = self.client.get(reverse('create_walkin_member'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Walk-in Member')
        self.assertContains(response, 'name="first_name"')
        self.assertContains(response, 'name="sector"')
        self.assertContains(response, 'name="payment_status"')

    def test_post_walkin_member_creates_pending_account_and_membership(self):
        response = self.client.post(reverse('create_walkin_member'), self._valid_payload())

        self.assertEqual(response.status_code, 200)
        created_user = User.objects.get(email='maria.walkin@example.com')
        application = MembershipApplication.objects.get(user=created_user)

        self.assertContains(response, 'Walk-in member created successfully.')
        self.assertFalse(created_user.is_verified)
        self.assertTrue(created_user.membership_form_submitted)
        self.assertTrue(created_user.must_change_password)
        self.assertFalse(application.is_approved)
        self.assertEqual(application.sector, self.sector)
        self.assertEqual(application.assigned_sector, self.sector)
        self.assertEqual(application.national_id_number, '9999-8888-7777')
        self.assertEqual(application.rcba_number, 'RCBA-2026-003')
        self.assertEqual(application.payment_status, 'pending')
        self.assertContains(response, created_user.username)
        self.assertContains(response, 'Pending Review')
        self.assertNotContains(response, 'name="first_name"')
        self.assertNotContains(response, 'One organized flow for walk-in membership registration')

    def test_post_walkin_member_can_auto_approve_when_ready(self):
        response = self.client.post(
            reverse('create_walkin_member'),
            self._valid_payload(
                email='approved.walkin@example.com',
                payment_status='paid',
                requirements_complete='on',
            ),
        )

        self.assertEqual(response.status_code, 200)
        created_user = User.objects.get(email='approved.walkin@example.com')
        application = MembershipApplication.objects.get(user=created_user)

        self.assertTrue(created_user.is_verified)
        self.assertIsNotNone(created_user.membership_approved_date)
        self.assertTrue(application.is_approved)
        self.assertEqual(application.reviewed_by, self.admin)
        self.assertIsNotNone(application.payment_date)
        payment = Payment.objects.get(
            user=created_user,
            payment_type='membership',
            object_id=application.pk,
        )
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(str(payment.amount), '500.00')
        self.assertContains(response, 'The account is already approved.')
        self.assertContains(response, 'Approved')
