import os
import shutil
import json
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from notifications.models import UserNotification

from .forms import MachineForm, RentalForm, RentalPackageRequestForm
from .models import (
    DryerRental,
    Machine,
    MachineImage,
    Rental,
    RiceMillAppointment,
    Maintenance,
    MaintenancePartUsed,
    RentalPackage,
    RentalPackageItem,
)
from bufia.models import Payment, Refund


User = get_user_model()


class RentalOnlinePaymentLimitTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='online_limit_user',
            email='online_limit_user@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Limit Test Hand Tractor',
            machine_type='tractor_4wd',
            description='Machine used to validate online payment limits.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='4000/hectare',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        self.start_date = date.today() + timedelta(days=2)
        self.end_date = self.start_date + timedelta(days=2)

    def test_rental_form_blocks_online_payment_when_total_exceeds_stripe_limit(self):
        form = RentalForm(
            data={
                'machine': self.machine.pk,
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
                'area': '1000',
                'payment_method': 'online',
                'service_type': 'harvesting',
                'purpose': 'Large area booking for payment limit validation',
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)
        self.assertIn(
            'Online payment is limited to PHP 999,999.99',
            form.errors['payment_method'][0],
        )

    def test_create_rental_payment_redirects_before_stripe_when_total_exceeds_limit(self):
        rental = Rental.objects.create(
            machine=self.machine,
            user=self.user,
            start_date=self.start_date,
            end_date=self.end_date,
            area=Decimal('1000.0000'),
            purpose='Create checkout session with over-limit amount',
            status='approved',
            payment_type='cash',
            payment_method='online',
            payment_status='pending',
        )
        rental.payment_amount = rental.calculate_payment_amount()
        rental.save(update_fields=['payment_amount'])

        self.client.force_login(self.user)

        with patch('bufia.views.payment_views._stripe_is_configured', return_value=True), patch(
            'bufia.views.payment_views.stripe'
        ) as mock_stripe:
            response = self.client.get(
                reverse('create_rental_payment', args=[rental.pk]),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Online payment is limited to PHP 999,999.99 per transaction.',
        )
        mock_stripe.checkout.Session.create.assert_not_called()

    def test_day_priced_online_payment_validation_uses_dates_without_crashing(self):
        day_machine = Machine.objects.create(
            name='Day Rate Tractor',
            machine_type='tractor_4wd',
            description='Machine used to validate day-priced rental calculations.',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000/day',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        form = RentalForm(
            data={
                'machine': day_machine.pk,
                'start_date': self.start_date.isoformat(),
                'end_date': (self.start_date + timedelta(days=2)).isoformat(),
                'area': '4.99',
                'payment_method': 'online',
                'purpose': 'Day-priced online validation',
                'service_type': 'harvesting',
                'requester_name': 'Test User',
                'farm_area': 'Bayawan City',
            },
            user=self.user,
            machine_id=day_machine.pk,
        )

        self.assertTrue(form.is_valid(), form.errors)


class MachineImageDisplayTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='machineimageviewer',
            email='machineimageviewer@example.com',
            password='testpassword123',
        )

    def _create_machine(self, name):
        return Machine.objects.create(
            name=name,
            machine_type='tractor_4wd',
            description='Machine image fallback test.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/hectare',
        )

    def test_get_display_image_url_ignores_missing_direct_image_file(self):
        machine = self._create_machine('Broken Direct Image Tractor')
        machine.image = 'machines/images/missing-direct.gif'
        machine.save(update_fields=['image'])

        machine.refresh_from_db()

        self.assertIsNone(machine.get_display_image_url())

    def test_get_display_image_url_ignores_missing_related_image_file(self):
        machine = self._create_machine('Broken Gallery Image Tractor')
        MachineImage.objects.create(
            machine=machine,
            image='machines/images/missing-gallery.gif',
            is_primary=True,
        )

        machine.refresh_from_db()

        self.assertIsNone(machine.get_display_image_url())

    def test_machine_detail_hides_missing_related_images(self):
        machine = self._create_machine('Broken Detail Image Tractor')
        MachineImage.objects.create(
            machine=machine,
            image='machines/images/missing-detail.gif',
            is_primary=True,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:machine_detail', args=[machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No images available for this machine')
        self.assertNotContains(response, 'missing-detail.gif')


class MachineCardSummaryTestCase(TestCase):
    def _create_machine(self, **overrides):
        payload = {
            'name': 'Card Summary Tractor',
            'machine_type': 'tractor_4wd',
            'description': 'Configured machine summary',
            'status': 'available',
            'rental_fee_per_day': Decimal('1200.00'),
            'current_price': '1200/hectare',
            'rental_price_type': 'cash',
            'allow_online_payment': True,
            'allow_face_to_face_payment': True,
            'settlement_type': 'immediate',
        }
        payload.update(overrides)
        return Machine.objects.create(**payload)

    def test_payment_summary_reflects_enabled_methods_only(self):
        online_only = self._create_machine(
            name='Online Only Tractor',
            allow_online_payment=True,
            allow_face_to_face_payment=False,
        )
        counter_only = self._create_machine(
            name='Counter Only Tractor',
            allow_online_payment=False,
            allow_face_to_face_payment=True,
        )
        no_methods = self._create_machine(
            name='Unset Payment Tractor',
            allow_online_payment=False,
            allow_face_to_face_payment=False,
        )

        self.assertEqual(online_only.get_payment_summary(), 'Gcash payment')
        self.assertEqual(counter_only.get_payment_summary(), 'Over the counter')
        self.assertEqual(no_methods.get_payment_summary(), 'Payment method not set')

    def test_future_active_workflow_does_not_mark_machine_as_currently_in_use(self):
        machine = self._create_machine(name='Future Reserved Tractor')
        user = User.objects.create_user(
            username='future_machine_member',
            email='future_machine_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        Rental.objects.create(
            machine=machine,
            user=user,
            customer_name='Future Member',
            customer_address='Future Farm',
            field_location='Future Farm',
            area=Decimal('1.5000'),
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=4),
            purpose='Future scheduled work',
            status='approved',
            workflow_state='in_progress',
            operator_status='operating',
            payment_type='cash',
            settlement_type='immediate',
            payment_status='paid',
        )

        self.assertFalse(machine.is_currently_rented())
        self.assertFalse(machine.has_active_rental())
        self.assertEqual(machine.get_operational_status(), 'available')

    def test_machine_card_note_and_settlement_use_configured_values(self):
        machine = self._create_machine(
            allow_online_payment=False,
            allow_face_to_face_payment=False,
            settlement_type='after_harvest',
        )

        self.assertEqual(machine.get_settlement_summary(), 'After Harvest')
        self.assertEqual(machine.get_card_note(), 'Payment method not set by admin.')


class AdminRentalCreateRedirectTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='rentaladmin',
            email='rentaladmin@example.com',
            password='testpassword123',
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='rentalmember',
            email='rentalmember@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Redirect Test Tractor',
            machine_type='tractor_4wd',
            description='Machine for admin rental redirect coverage.',
            status='available',
            rental_fee_per_day=Decimal('1500.00'),
            current_price='1500/hectare',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
            settlement_type='immediate',
        )

    def test_admin_rental_create_redirects_to_admin_approval_page(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:admin_rental_create'),
            {
                'selected_member_id': str(self.member.pk),
                'renter_name': self.member.get_full_name() or self.member.username,
                'renter_contact_number': '09123456789',
                'renter_address': 'Sample Address',
                'machine': str(self.machine.pk),
                'start_date': (date.today() + timedelta(days=2)).isoformat(),
                'end_date': (date.today() + timedelta(days=3)).isoformat(),
                'area': '1.5',
                'purpose': 'Admin-created rental redirect test',
                'status': 'pending',
                'payment_method': 'online',
            },
        )

        rental = Rental.objects.latest('id')
        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            fetch_redirect_response=False,
        )

    def test_admin_same_day_walk_in_rental_stays_approved_without_becoming_active(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:admin_rental_create'),
            {
                'selected_member_id': '',
                'renter_name': 'Walk-In Farmer',
                'renter_contact_number': '09123456789',
                'renter_address': 'Walk-In Farm',
                'machine': str(self.machine.pk),
                'start_date': date.today().isoformat(),
                'end_date': date.today().isoformat(),
                'area': '1.5',
                'purpose': 'Same-day walk-in rental',
                'status': 'pending',
                'payment_method': 'face_to_face',
            },
        )

        rental = Rental.objects.latest('id')
        self.machine.refresh_from_db()

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.status, 'approved')
        self.assertEqual(rental.workflow_state, 'approved')
        self.assertTrue(rental.customer_is_walk_in)
        self.assertFalse(self.machine.has_active_rental())
        self.assertFalse(self.machine.is_currently_rented())
        self.assertEqual(self.machine.get_operational_status(), 'available')


class AdminAssistedRentalFormRuleTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='assistedrentaladmin',
            email='assistedrentaladmin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='assistedrentalmember',
            email='assistedrentalmember@example.com',
            password='testpassword123',
            first_name='Maria',
            last_name='Santos',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Admin Assisted Tractor',
            machine_type='tractor_4wd',
            description='Machine for admin-assisted rental form rules.',
            status='available',
            rental_fee_per_day=Decimal('2000.00'),
            current_price='2000/hectare',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
            settlement_type='immediate',
        )

    def _build_form(self, **overrides):
        payload = {
            'selected_member_id': '',
            'requester_name': 'Walk-In Farmer',
            'requester_contact_number': '09123456789',
            'farm_area': 'Sitio Maligaya',
            'machine': str(self.machine.pk),
            'start_date': timezone.localdate().isoformat(),
            'end_date': timezone.localdate().isoformat(),
            'area': '1.50',
            'purpose': 'Admin-assisted rental',
            'payment_method': 'face_to_face',
            'service_type': 'land_preparation',
        }
        payload.update(overrides)
        return RentalForm(data=payload, user=self.admin)

    def test_admin_can_create_same_day_walk_in_rental(self):
        form = self._build_form()

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_selected_member_must_book_one_day_ahead(self):
        form = self._build_form(
            selected_member_id=str(self.member.pk),
            requester_name=self.member.get_full_name(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertIn(
            'Same-day rentals are for walk-in bookings only.',
            form.errors['start_date'][0],
        )

    def test_admin_selected_member_checks_member_overlap_not_admin_overlap(self):
        start_date = timezone.localdate() + timedelta(days=2)
        Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=start_date,
            end_date=start_date,
            area=Decimal('1.00'),
            purpose='Existing member booking',
            status='pending',
            workflow_state='pending_approval',
            payment_type='cash',
            payment_method='face_to_face',
            payment_status='pending',
        )

        form = self._build_form(
            selected_member_id=str(self.member.pk),
            requester_name=self.member.get_full_name(),
            start_date=start_date.isoformat(),
            end_date=start_date.isoformat(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            'You already have an active rental for Admin Assisted Tractor',
            form.non_field_errors()[0],
        )

    def test_admin_walk_in_cannot_use_online_payment(self):
        form = self._build_form(payment_method='online')

        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)
        self.assertIn(
            'not one of the available choices',
            form.errors['payment_method'][0],
        )

    def test_admin_selected_member_can_use_online_payment(self):
        form = self._build_form(
            selected_member_id=str(self.member.pk),
            requester_name=self.member.get_full_name(),
            start_date=(timezone.localdate() + timedelta(days=2)).isoformat(),
            end_date=(timezone.localdate() + timedelta(days=2)).isoformat(),
            payment_method='online',
        )

        self.assertTrue(form.is_valid(), form.errors)


class MachineImageUploadFlowTestCase(TestCase):
    VALID_GIF_BYTES = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
        b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )

    def setUp(self):
        self.media_root_base = os.path.join(settings.BASE_DIR, 'tmp_test_media')
        os.makedirs(self.media_root_base, exist_ok=True)
        self.media_root = os.path.join(self.media_root_base, f'{self.__class__.__name__}_{self._testMethodName}')
        os.makedirs(self.media_root, exist_ok=True)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        self.admin = User.objects.create_superuser(
            username='machineimageadmin',
            email='machineimageadmin@example.com',
            password='testpassword123',
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _machine_payload(self, **overrides):
        payload = {
            'name': 'Upload Tractor',
            'description': 'Machine with uploaded gallery images.',
            'status': 'available',
            'machine_type': 'tractor_4wd',
            'current_price': '4000',
            'pricing_unit': 'hectare',
            'rental_price_type': 'cash',
            'allow_online_payment': 'on',
            'allow_face_to_face_payment': 'on',
            'settlement_type': 'immediate',
            'in_kind_farmer_share': '9',
            'in_kind_organization_share': '1',
        }
        payload.update(overrides)
        return payload

    def _uploaded_image(self, name='machine.gif'):
        return SimpleUploadedFile(name, self.VALID_GIF_BYTES, content_type='image/gif')

    def test_create_machine_saves_uploaded_image(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:machine_create'),
            self._machine_payload(
                **{
                    'form-TOTAL_FORMS': '1',
                    'form-INITIAL_FORMS': '0',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-image': self._uploaded_image('front-view.gif'),
                    'form-0-caption': 'Front view',
                    'form-0-is_primary': 'on',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse('machines:machine_list'),
            fetch_redirect_response=False,
        )

        machine = Machine.objects.get(name='Upload Tractor')
        self.assertEqual(machine.images.count(), 1)
        image = machine.images.first()
        self.assertEqual(image.caption, 'Front view')
        self.assertTrue(image.is_primary)
        self.assertTrue(image.image.name.endswith('.gif'))
        self.assertIsNotNone(machine.get_display_image_url())

    def test_create_machine_saves_uploaded_image_from_uploaded_images_field(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:machine_create'),
            self._machine_payload(
                name='Uploaded Images Tractor',
                **{
                    'form-TOTAL_FORMS': '0',
                    'form-INITIAL_FORMS': '0',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'uploaded_images': self._uploaded_image('uploaded-images.gif'),
                    'new-image-0-caption': 'Uploaded images field',
                    'new-image-0-is_primary': 'on',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse('machines:machine_list'),
            fetch_redirect_response=False,
        )

        machine = Machine.objects.get(name='Uploaded Images Tractor')
        self.assertEqual(machine.images.count(), 1)
        image = machine.images.first()
        self.assertEqual(image.caption, 'Uploaded images field')
        self.assertTrue(image.is_primary)
        self.assertTrue(image.image.name.endswith('.gif'))

    @override_settings(CLOUDINARY_ENABLED=True)
    @patch('machines.models.cloudinary_uploader.upload')
    def test_create_machine_uploads_image_to_cloudinary_when_enabled(self, mock_upload):
        mock_upload.return_value = {
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/v1/bufia/machines/cloudinary-tractor/front-view.gif',
            'public_id': 'bufia/machines/cloudinary-tractor/front-view',
        }

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:machine_create'),
            self._machine_payload(
                name='Cloudinary Tractor',
                **{
                    'form-TOTAL_FORMS': '1',
                    'form-INITIAL_FORMS': '0',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-image': self._uploaded_image('front-view.gif'),
                    'form-0-caption': 'Cloudinary front view',
                    'form-0-is_primary': 'on',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse('machines:machine_list'),
            fetch_redirect_response=False,
        )

        image = Machine.objects.get(name='Cloudinary Tractor').images.first()
        self.assertEqual(image.cloudinary_public_id, 'bufia/machines/cloudinary-tractor/front-view')
        self.assertEqual(
            image.cloudinary_url,
            'https://res.cloudinary.com/demo/image/upload/v1/bufia/machines/cloudinary-tractor/front-view.gif',
        )
        self.assertFalse(bool(image.image))
        self.assertEqual(image.get_image_url(), image.cloudinary_url)

    def test_edit_machine_can_add_new_uploaded_image(self):
        self.client.force_login(self.admin)
        machine = Machine.objects.create(
            name='Edit Tractor',
            machine_type='tractor_4wd',
            description='Editable machine with gallery.',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000/hectare',
        )
        existing_image = MachineImage.objects.create(
            machine=machine,
            image=self._uploaded_image('existing.gif'),
            caption='Existing image',
            is_primary=True,
        )

        response = self.client.post(
            reverse('machines:edit_machine', args=[machine.pk]),
            self._machine_payload(
                name='Edit Tractor',
                **{
                    'form-TOTAL_FORMS': '2',
                    'form-INITIAL_FORMS': '1',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-id': str(existing_image.pk),
                    'form-0-caption': 'Existing image',
                    'form-0-is_primary': 'on',
                    'form-1-image': self._uploaded_image('new-side.gif'),
                    'form-1-caption': 'Side view',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse('machines:machine_detail', args=[machine.pk]),
            fetch_redirect_response=False,
        )

        machine.refresh_from_db()
        self.assertEqual(machine.images.count(), 2)
        self.assertTrue(machine.images.filter(caption='Side view').exists())

    def test_edit_machine_can_add_uploaded_images_field_image(self):
        self.client.force_login(self.admin)
        machine = Machine.objects.create(
            name='Uploaded Images Edit Tractor',
            machine_type='tractor_4wd',
            description='Editable machine with uploaded_images field.',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000/hectare',
        )
        existing_image = MachineImage.objects.create(
            machine=machine,
            image=self._uploaded_image('existing-uploaded-images.gif'),
            caption='Existing image',
            is_primary=True,
        )

        response = self.client.post(
            reverse('machines:edit_machine', args=[machine.pk]),
            self._machine_payload(
                name='Uploaded Images Edit Tractor',
                **{
                    'form-TOTAL_FORMS': '1',
                    'form-INITIAL_FORMS': '1',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-id': str(existing_image.pk),
                    'form-0-caption': 'Existing image',
                    'form-0-is_primary': 'on',
                    'uploaded_images': self._uploaded_image('uploaded-images-side.gif'),
                    'new-image-0-caption': 'Uploaded images edit field',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse('machines:machine_detail', args=[machine.pk]),
            fetch_redirect_response=False,
        )

        machine.refresh_from_db()
        self.assertEqual(machine.images.count(), 2)
        self.assertTrue(machine.images.filter(caption='Uploaded images edit field').exists())

    def test_create_then_edit_machine_can_add_second_uploaded_image(self):
        self.client.force_login(self.admin)

        create_response = self.client.post(
            reverse('machines:machine_create'),
            self._machine_payload(
                name='Create Then Edit Tractor',
                **{
                    'form-TOTAL_FORMS': '1',
                    'form-INITIAL_FORMS': '0',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-image': self._uploaded_image('first.gif'),
                    'form-0-caption': 'First photo',
                    'form-0-is_primary': 'on',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            create_response,
            reverse('machines:machine_list'),
            fetch_redirect_response=False,
        )

        machine = Machine.objects.get(name='Create Then Edit Tractor')
        existing_image = machine.images.get(caption='First photo')

        edit_response = self.client.post(
            reverse('machines:edit_machine', args=[machine.pk]),
            self._machine_payload(
                name='Create Then Edit Tractor',
                **{
                    'form-TOTAL_FORMS': '2',
                    'form-INITIAL_FORMS': '1',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-id': str(existing_image.pk),
                    'form-0-caption': 'First photo',
                    'form-0-is_primary': 'on',
                    'form-1-image': self._uploaded_image('second.gif'),
                    'form-1-caption': 'Second photo',
                }
            ),
            follow=False,
        )

        self.assertRedirects(
            edit_response,
            reverse('machines:machine_detail', args=[machine.pk]),
            fetch_redirect_response=False,
        )

        machine.refresh_from_db()
        self.assertEqual(machine.images.count(), 2)
        self.assertTrue(machine.images.filter(caption='First photo').exists())
        self.assertTrue(machine.images.filter(caption='Second photo').exists())
        self.assertIsNotNone(machine.get_display_image_url())

    def test_create_machine_with_invalid_image_formset_returns_400_without_saving_machine(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:machine_create'),
            self._machine_payload(
                name='Too Many Uploads',
                **{
                    'form-TOTAL_FORMS': '4',
                    'form-INITIAL_FORMS': '0',
                    'form-MIN_NUM_FORMS': '0',
                    'form-MAX_NUM_FORMS': '3',
                    'form-0-image': self._uploaded_image('one.gif'),
                    'form-1-image': self._uploaded_image('two.gif'),
                    'form-2-image': self._uploaded_image('three.gif'),
                    'form-3-image': self._uploaded_image('four.gif'),
                }
            ),
            follow=False,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Machine.objects.filter(name='Too Many Uploads').exists())


class ServiceTransactionIdTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tx_member',
            email='tx_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='tx_admin',
            email='tx_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.rice_mill = Machine.objects.create(
            name='TX Rice Mill',
            machine_type='rice_mill',
            description='Rice mill for transaction ID tests',
            status='available',
            rental_fee_per_day=Decimal('3.00'),
            current_price='3',
        )
        self.dryer = Machine.objects.create(
            name='TX Flatbed Dryer',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            dryer_hourly_rate=Decimal('150.00'),
            description='Dryer for transaction ID tests',
            status='available',
            rental_fee_per_day=Decimal('150.00'),
            current_price='150/hour',
        )

    def test_ricemill_receipt_backfills_transaction_id_when_missing_payment_record(self):
        appointment = RiceMillAppointment.objects.create(
            machine=self.rice_mill,
            user=self.user,
            appointment_date=date.today() + timedelta(days=1),
            sacks=5,
            rice_quantity=Decimal('200.00'),
            final_weight=Decimal('180.00'),
            price_per_kg=Decimal('3.00'),
            payment_method='face_to_face',
            status='completed',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_receipt', args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.filter(
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=appointment.id,
        ).first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.internal_transaction_id)
        self.assertEqual(response.context['transaction_id'], payment.internal_transaction_id)

    def test_dryer_receipt_backfills_transaction_id_when_missing_payment_record(self):
        dryer_rental = DryerRental.objects.create(
            machine=self.dryer,
            user=self.user,
            rental_type='hourly',
            rental_date=date.today() + timedelta(days=1),
            start_time=time(8, 0),
            end_time=time(10, 0),
            requested_hours=Decimal('2.00'),
            total_amount=Decimal('300.00'),
            payment_method='face_to_face',
            status='completed',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:dryer_rental_receipt', args=[dryer_rental.pk]))

        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.filter(
            content_type=ContentType.objects.get_for_model(DryerRental),
            object_id=dryer_rental.id,
        ).first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.internal_transaction_id)
        self.assertEqual(response.context['transaction_id'], payment.internal_transaction_id)
        self.assertContains(response, self.dryer.name)
        self.assertContains(response, 'Duration: 2.00 hour(s)')
        self.assertContains(response, 'Rate: PHP 150.00 per hour')

    def test_dryer_receipt_shows_refund_totals_when_refunded(self):
        dryer_rental = DryerRental.objects.create(
            machine=self.dryer,
            user=self.user,
            rental_type='hourly',
            rental_date=date.today() + timedelta(days=1),
            start_time=time(8, 0),
            end_time=time(10, 0),
            requested_hours=Decimal('2.00'),
            total_amount=Decimal('300.00'),
            payment_method='face_to_face',
            status='completed',
        )
        payment = Payment.objects.create(
            user=self.user,
            payment_type='dryer',
            amount=Decimal('300.00'),
            amount_received=Decimal('300.00'),
            change_given=Decimal('0.00'),
            status='completed',
            processed_by=self.admin,
            content_type=ContentType.objects.get_for_model(DryerRental),
            object_id=dryer_rental.id,
        )
        Refund.objects.create(
            payment=payment,
            amount=Decimal('75.00'),
            method='cash',
            reason='Drying service adjustment',
            status='refunded',
            refunded_by=self.admin,
            refunded_at=timezone.now(),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:dryer_rental_receipt', args=[dryer_rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Refunded:')
        self.assertContains(response, 'Refund Status:')
        self.assertContains(response, 'Net Retained:')
        self.assertContains(response, 'PHP 75.00')
        self.assertContains(response, 'Partially Refunded')


class DryerSchedulingVisibilityTestCase(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.joel = User.objects.create_user(
            username='joel',
            email='joel@example.com',
            password='testpassword123',
            first_name='Joel',
            last_name='Dela Cruz',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='dryerstaff',
            email='dryerstaff@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Flatbed Dryer 1',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            dryer_hourly_rate=Decimal('150.00'),
            description='Dryer for testing',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        self.rental_date = date.today() + timedelta(days=1)
        self.existing_rental = DryerRental.objects.create(
            machine=self.machine,
            user=self.joel,
            rental_type='hourly',
            rental_date=self.rental_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            requested_hours=Decimal('3.00'),
            status='approved',
        )

    def test_dryer_form_shows_other_users_booked_time_ranges(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose a dryer and rental date to view availability.')
        events = json.loads(response.context['calendar_events_json'])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['range_label'], '9:00 AM - 12:00 PM')
        self.assertEqual(events[0]['booked_by'], 'Joel Dela Cruz')

    def test_dryer_form_allows_overlapping_time_ranges_for_admin_review(self):
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk]),
            {
                'machine': self.machine.pk,
                'rental_type': 'hourly',
                'rental_date': self.rental_date.isoformat(),
                'start_time': '10:00',
                'requested_hours': '1.00',
                'notes': 'Overlap attempt',
            },
        )

        self.assertEqual(response.status_code, 302)
        created_rental = DryerRental.objects.exclude(pk=self.existing_rental.pk).get(user=self.viewer)
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')
        self.assertEqual(created_rental.start_time, time(10, 0))
        self.assertEqual(created_rental.end_time, time(11, 0))

    def test_dryer_form_redirects_to_detail_page_after_successful_submit(self):
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk]),
            {
                'machine': self.machine.pk,
                'rental_type': 'hourly',
                'rental_date': self.rental_date.isoformat(),
                'start_time': '13:00',
                'requested_hours': '2.00',
                'notes': 'Afternoon drying session',
            },
        )

        created_rental = DryerRental.objects.exclude(pk=self.existing_rental.pk).get(user=self.viewer)
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')
        self.assertEqual(created_rental.total_amount, Decimal('300.00'))

    def test_legacy_dryer_pending_route_redirects_to_detail(self):
        self.client.force_login(self.joel)

        response = self.client.get(
            reverse('machines:dryer_rental_pending', args=[self.existing_rental.pk])
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.existing_rental.pk]),
            fetch_redirect_response=False,
        )

    def test_member_generic_dryer_create_redirects_to_services_page(self):
        self.machine.status = 'rented'
        self.machine.save(update_fields=['status'])
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_create'))

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_list'),
            fetch_redirect_response=False,
        )

    def test_member_generic_dryer_create_redirects_even_without_admin_added_dryers(self):
        DryerRental.objects.all().delete()
        Machine.objects.filter(machine_type__in=Machine.DRYER_MACHINE_TYPES).delete()
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_create'))

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_list'),
            fetch_redirect_response=False,
        )
        self.assertFalse(Machine.objects.filter(machine_type__in=Machine.DRYER_MACHINE_TYPES).exists())

    def test_dryer_form_shows_pending_requests_in_availability(self):
        self.existing_rental.status = 'pending'
        self.existing_rental.save(update_fields=['status'])
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        events = json.loads(response.context['calendar_events_json'])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['range_label'], '9:00 AM - 12:00 PM')
        self.assertEqual(events[0]['status'], 'pending')

    def test_dryer_form_rejects_overlapping_pending_time_ranges(self):
        self.existing_rental.status = 'pending'
        self.existing_rental.save(update_fields=['status'])
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk]),
            {
                'machine': self.machine.pk,
                'rental_type': 'hourly',
                'rental_date': self.rental_date.isoformat(),
                'start_time': '10:00',
                'requested_hours': '1.00',
                'notes': 'Overlap with pending request',
            },
        )

        self.assertEqual(response.status_code, 302)
        created_rental = DryerRental.objects.exclude(pk=self.existing_rental.pk).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')

    def test_until_dried_dryer_request_does_not_require_time_inputs(self):
        until_dried_machine = Machine.objects.create(
            name='Solar Dryer 1',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            description='Until-dried solar dryer',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[until_dried_machine.pk]),
            {
                'machine': until_dried_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'goods_description': 'Fresh palay for drying',
                'quantity': '20 sacks',
                'notes': 'Dry this batch until finished',
            },
        )

        created_rental = DryerRental.objects.filter(machine=until_dried_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.rental_type, 'until_dried')
        self.assertIsNone(created_rental.start_time)
        self.assertIsNone(created_rental.end_time)
        self.assertIsNone(created_rental.requested_hours)
        self.assertEqual(created_rental.goods_description, 'Fresh palay for drying')
        self.assertEqual(created_rental.quantity, '20 sacks')
        self.assertEqual(created_rental.total_amount, Decimal('0.00'))

    def test_until_dried_request_requires_goods_details_and_quantity(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Required Fields',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            description='Solar dryer validation test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {
                'machine': solar_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'notes': 'Missing goods information',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Describe the rice grain batch for an until-dried rental.')
        self.assertContains(response, 'Enter the rice grain quantity for an until-dried rental.')

    def test_until_dried_request_allows_overlapping_active_window_for_admin_review(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Overlap',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            description='Solar overlap test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        DryerRental.objects.create(
            machine=solar_machine,
            user=self.joel,
            rental_date=self.rental_date,
            rental_type='until_dried',
            estimated_end_date=self.rental_date + timedelta(days=2),
            goods_description='Existing drying batch',
            quantity='15 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {
                'machine': solar_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': (self.rental_date + timedelta(days=1)).isoformat(),
                'goods_description': 'Needs full-day sun exposure',
                'quantity': '10 sacks',
            },
        )

        created_rental = DryerRental.objects.filter(machine=solar_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')
        self.assertEqual(created_rental.quantity, '10 sacks')

    def test_solar_until_dried_request_blocks_when_capacity_limit_is_reached(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Capacity Limit',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('40.00'),
            description='Solar capacity limit test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        DryerRental.objects.create(
            machine=solar_machine,
            user=self.joel,
            rental_date=self.rental_date,
            rental_type='until_dried',
            estimated_end_date=self.rental_date + timedelta(days=1),
            goods_description='Existing solar drying batch',
            quantity='30 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {
                'machine': solar_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'goods_description': 'Second solar drying batch',
                'quantity': '20 sacks',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This dryer only has 10.00 sack(s) remaining')
        self.assertFalse(DryerRental.objects.filter(machine=solar_machine, user=self.viewer).exists())

    def test_solar_until_dried_request_can_reuse_capacity_after_prior_rental_end_date(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Capacity Release',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('40.00'),
            description='Solar capacity release test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        DryerRental.objects.create(
            machine=solar_machine,
            user=self.joel,
            rental_date=self.rental_date,
            rental_type='until_dried',
            estimated_end_date=self.rental_date,
            goods_description='Completed same-day solar batch',
            quantity='40 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {
                'machine': solar_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': (self.rental_date + timedelta(days=1)).isoformat(),
                'goods_description': 'Next-day solar drying batch',
                'quantity': '40 sacks',
            },
        )

        created_rental = DryerRental.objects.filter(machine=solar_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')

    def test_per_sack_dryer_request_form_shows_saved_pricing(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Per Sack Form',
            machine_type='solar_dryer',
            dryer_pricing_type='per_sack',
            description='Per sack dryer form test',
            status='available',
            rental_fee_per_day=30,
            current_price='30/sack',
        )
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pricing Setup')
        self.assertContains(response, 'Configured Rate')
        self.assertContains(response, 'Per Sack')
        self.assertContains(response, 'PHP 30.00 / sack')
        self.assertNotContains(response, 'Hourly Rate')

    def test_per_sack_dryer_rejects_hourly_request_flow(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Per Sack Validation',
            machine_type='solar_dryer',
            dryer_pricing_type='per_sack',
            description='Per sack validation test',
            status='available',
            rental_fee_per_day=45,
            current_price='45/sack',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {
                'machine': solar_machine.pk,
                'rental_type': 'hourly',
                'rental_date': self.rental_date.isoformat(),
                'start_time': '09:00',
                'requested_hours': '2.00',
                'notes': 'This should follow the saved pricing setup',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is configured as Per Sack')
        self.assertFalse(DryerRental.objects.filter(machine=solar_machine, user=self.viewer).exists())

    def test_flatbed_until_dried_request_stays_pending_for_admin_review(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Admin Review',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            description='Flatbed admin review test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        DryerRental.objects.create(
            machine=flatbed_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date,
            estimated_end_date=self.rental_date + timedelta(days=2),
            goods_description='Existing drying batch',
            quantity='100 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[flatbed_machine.pk]),
            {
                'machine': flatbed_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'goods_description': 'Second shared flatbed batch',
                'quantity': '30 sacks',
            },
        )

        created_rental = DryerRental.objects.filter(machine=flatbed_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')

    def test_flatbed_until_dried_request_blocks_when_capacity_limit_is_reached(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Large Quantity',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            flatbed_max_sack_capacity=Decimal('150.00'),
            description='Flatbed unlimited quantity test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        DryerRental.objects.create(
            machine=flatbed_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date,
            estimated_end_date=self.rental_date + timedelta(days=2),
            goods_description='Existing drying batch',
            quantity='100 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[flatbed_machine.pk]),
            {
                'machine': flatbed_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'goods_description': 'Large flatbed drying load',
                'quantity': '260 sacks',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This dryer only has 50.00 sack(s) remaining')
        self.assertFalse(DryerRental.objects.filter(machine=flatbed_machine, user=self.viewer).exists())

    def test_flatbed_until_dried_request_can_start_after_existing_estimated_end_date(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Shared Capacity Later',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            description='Flatbed later-start test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        DryerRental.objects.create(
            machine=flatbed_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date,
            estimated_end_date=self.rental_date + timedelta(days=2),
            goods_description='Existing drying batch',
            quantity='100 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[flatbed_machine.pk]),
            {
                'machine': flatbed_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': (self.rental_date + timedelta(days=3)).isoformat(),
                'goods_description': 'Later shared flatbed batch',
                'quantity': '60 sacks',
            },
        )

        created_rental = DryerRental.objects.filter(machine=flatbed_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )

    def test_flatbed_large_request_stays_single_request(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Single Large Request',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            flatbed_max_sack_capacity=Decimal('250.00'),
            description='Flatbed single request test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[flatbed_machine.pk]),
            {
                'machine': flatbed_machine.pk,
                'rental_type': 'until_dried',
                'rental_date': self.rental_date.isoformat(),
                'goods_description': 'Large shared flatbed request',
                'quantity': '220 sacks',
            },
        )

        created_rental = DryerRental.objects.get(machine=flatbed_machine, user=self.viewer)
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.quantity, '220 sacks')
        self.assertEqual(created_rental.batch_number, 1)
        self.assertEqual(created_rental.batch_total, 1)
        self.assertIsNone(created_rental.parent_rental)

    def test_grouped_flatbed_approve_page_shows_linked_batches(self):
        root_batch = DryerRental.objects.create(
            machine=self.machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date,
            goods_description='Grouped flatbed root batch',
            quantity='150 sacks',
            status='pending',
            batch_total=2,
        )
        second_batch = DryerRental.objects.create(
            machine=self.machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date + timedelta(days=1),
            goods_description='Grouped flatbed second batch',
            quantity='70 sacks',
            status='pending',
            parent_rental=root_batch,
            batch_number=2,
            batch_total=2,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_approve', args=[root_batch.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Linked Batches')
        self.assertContains(response, 'Batch 1 of 2')
        self.assertContains(response, 'Batch 2 of 2')
        self.assertContains(response, second_batch.reference_number)

    def test_approve_flow_keeps_large_flatbed_request_as_single_record(self):
        approval_machine = Machine.objects.create(
            name='Flatbed Approval Request',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            flatbed_max_sack_capacity=Decimal('250.00'),
            description='Flatbed approval scheduling test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        legacy_request = DryerRental.objects.create(
            machine=approval_machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date,
            goods_description='Large flatbed request',
            quantity='200 sacks',
            status='pending',
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_approve', args=[legacy_request.pk]),
            {
                'estimated_end_date': (self.rental_date + timedelta(days=2)).isoformat(),
                'estimated_end_time': '16:00',
                'admin_note': '',
            },
        )

        legacy_request.refresh_from_db()

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[legacy_request.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(legacy_request.quantity, '200 sacks')
        self.assertEqual(legacy_request.batch_total, 1)
        self.assertEqual(legacy_request.status, 'in_progress')
        self.assertEqual(legacy_request.estimated_end_date, self.rental_date + timedelta(days=2))
        self.assertFalse(legacy_request.child_batches.exists())

    def test_until_dried_approval_blocks_when_capacity_limit_would_be_exceeded(self):
        approval_machine = Machine.objects.create(
            name='Solar Approval Capacity',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('100.00'),
            description='Solar approval capacity test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        DryerRental.objects.create(
            machine=approval_machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date,
            estimated_end_date=self.rental_date + timedelta(days=2),
            estimated_end_time=time(16, 0),
            goods_description='Existing approved load',
            quantity='70 sacks',
            status='in_progress',
        )
        pending_request = DryerRental.objects.create(
            machine=approval_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date,
            goods_description='Pending solar load',
            quantity='40 sacks',
            status='pending',
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_approve', args=[pending_request.pk]),
            {
                'estimated_end_date': (self.rental_date + timedelta(days=2)).isoformat(),
                'estimated_end_time': '16:00',
                'admin_note': '',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[pending_request.pk]),
            fetch_redirect_response=False,
        )
        pending_request.refresh_from_db()
        self.assertEqual(pending_request.status, 'pending')

    def test_cancelling_grouped_flatbed_request_removes_all_batches(self):
        root_batch = DryerRental.objects.create(
            machine=self.machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date,
            goods_description='Grouped flatbed root batch',
            quantity='150 sacks',
            status='pending',
            batch_total=2,
        )
        second_batch = DryerRental.objects.create(
            machine=self.machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date + timedelta(days=1),
            goods_description='Grouped flatbed second batch',
            quantity='70 sacks',
            status='pending',
            parent_rental=root_batch,
            batch_number=2,
            batch_total=2,
        )
        self.client.force_login(self.viewer)

        response = self.client.post(reverse('machines:dryer_rental_delete', args=[second_batch.pk]))

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_list'),
            fetch_redirect_response=False,
        )
        self.assertFalse(DryerRental.objects.filter(pk__in=[root_batch.pk, second_batch.pk]).exists())

    def test_flatbed_availability_events_include_quantity_data(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Availability Feed',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            flatbed_max_sack_capacity=Decimal('180.00'),
            description='Flatbed availability payload test',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        DryerRental.objects.create(
            machine=flatbed_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date,
            estimated_end_date=self.rental_date + timedelta(days=2),
            goods_description='Existing drying batch',
            quantity='100 sacks',
            status='in_progress',
        )
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[flatbed_machine.pk])
        )

        events = json.loads(response.context['calendar_events_json'])
        self.assertEqual(events[0]['quantity_sacks'], '100.00')
        self.assertTrue(events[0]['uses_shared_capacity'])
        self.assertEqual(events[0]['shared_capacity_sacks'], '180.00')

    def test_dryer_list_shows_configured_dryer_options(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer 2',
            machine_type='solar_dryer',
            dryer_pricing_type='per_sack',
            description='Solar dryer listing test',
            status='available',
            rental_fee_per_day=35,
            current_price='35/sack',
        )
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.machine.name)
        self.assertContains(response, solar_machine.name)
        self.assertContains(response, self.machine.get_dryer_pricing_type_display())
        self.assertContains(response, self.machine.get_rate_display())
        self.assertContains(response, solar_machine.get_dryer_pricing_type_display())
        self.assertContains(response, solar_machine.get_rate_display())
        self.assertContains(response, 'Per Hour')
        self.assertContains(response, 'Per Sack')

    def test_member_dryer_list_includes_quick_view_and_cancel_modals(self):
        self.client.force_login(self.joel)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick View')
        self.assertContains(response, 'showDryerRentalQuickView(this)', html=False)
        self.assertContains(response, 'id="dryerRentalQuickViewModal"', html=False)
        self.assertContains(response, 'id="bufiaDeleteActionModal"', html=False)
        self.assertContains(response, 'data-delete-title="Cancel Dryer Request"', html=False)
        self.assertContains(response, 'data-delete-action="Cancel"', html=False)
        self.assertContains(
            response,
            reverse('machines:dryer_rental_delete', args=[self.existing_rental.pk]),
        )

    def test_admin_dryer_list_allows_modal_cancel_for_visible_requests(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="bufiaDeleteActionModal"', html=False)
        self.assertContains(response, 'data-delete-title="Cancel Dryer Request"', html=False)
        self.assertContains(response, 'data-delete-action="Cancel"', html=False)
        self.assertContains(
            response,
            reverse('machines:dryer_rental_delete', args=[self.existing_rental.pk]),
        )

    def test_admin_dryer_form_uses_dropdown_assignment_flow(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assign Dryer Service')
        self.assertContains(response, 'Choose a dryer unit, fill in the renter details, then set the rental date and service type.')
        self.assertContains(response, 'name="machine"', html=False)
        self.assertContains(response, 'Select a dryer')
        self.assertContains(response, self.machine.name)

    def test_admin_assign_service_prefills_selected_dryer(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk]),
            {'selected_machine': self.machine.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_machine_id'], str(self.machine.pk))
        self.assertEqual(response.context['form']._selected_machine, self.machine)
        self.assertNotContains(response, 'aria-label="Available dryer units"', html=False)

    def test_admin_dryer_assignment_payload_includes_saved_pricing(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Assignment Payload',
            machine_type='solar_dryer',
            dryer_pricing_type='per_sack',
            description='Per sack payload test',
            status='available',
            rental_fee_per_day=32,
            current_price='32/sack',
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[solar_machine.pk]),
            {'selected_machine': solar_machine.pk},
        )

        self.assertEqual(response.status_code, 200)
        dryer_options = json.loads(str(response.context['dryer_options_json']))
        selected_payload = next(item for item in dryer_options if item['id'] == solar_machine.pk)
        self.assertEqual(selected_payload['pricing_type'], 'per_sack')
        self.assertEqual(selected_payload['pricing_type_display'], 'Per Sack')
        self.assertEqual(selected_payload['rate_display'], 'PHP 32.00 / sack')

    def test_admin_can_assign_walk_in_dryer_transaction_from_dropdown(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_create'),
            {
                'machine': self.machine.pk,
                'rental_type': 'hourly',
                'renter_name': 'Walk-in Farmer',
                'renter_contact_number': '09123456789',
                'farm_location': 'Sitio Riverside',
                'rental_date': self.rental_date.isoformat(),
                'start_time': '13:00',
                'requested_hours': '2.00',
                'notes': 'Walk-in dryer assignment',
            },
        )

        created_rental = DryerRental.objects.exclude(pk=self.existing_rental.pk).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.machine, self.machine)
        self.assertEqual(created_rental.customer_name, 'Walk-in Farmer')
        self.assertEqual(created_rental.total_amount, Decimal('300.00'))
        self.assertEqual(created_rental.user.username, 'system')

    def test_admin_dryer_list_hides_member_service_cards(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dryer Unit Directory')
        self.assertContains(response, 'Add Flatbed Dryer')
        self.assertNotContains(response, 'Assign Dryer Service')
        self.assertContains(response, 'Delete')
        self.assertContains(response, self.machine.name)
        self.assertContains(response, 'Limit: 150 sacks')
        self.assertNotContains(response, 'Request This Dryer')

    def test_admin_dryer_list_shows_live_availability_board(self):
        current_now = timezone.localtime()
        active_machine = Machine.objects.create(
            name='Solar Dryer Active Board',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('80.00'),
            description='Active dryer availability row',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        available_machine = Machine.objects.create(
            name='Circulating Dryer Available Board',
            machine_type='circulating_dryer',
            dryer_service_type='circulating',
            dryer_pricing_type='hourly',
            flatbed_max_sack_capacity=Decimal('100.00'),
            dryer_hourly_rate=Decimal('180.00'),
            description='Available dryer availability row',
            status='available',
            rental_fee_per_day=180,
            current_price='180/hour',
        )
        active_rental = DryerRental.objects.create(
            machine=active_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=current_now.date(),
            goods_description='Palay batch',
            quantity='35 sacks',
            estimated_end_date=current_now.date(),
            estimated_end_time=(current_now + timedelta(hours=2)).time().replace(second=0, microsecond=0),
            status='in_progress',
        )
        DryerRental.objects.filter(pk=active_rental.pk).update(updated_at=current_now - timedelta(hours=1))

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Dryer Availability')
        availability_rows = response.context['dryer_availability_rows']
        active_row = next(row for row in availability_rows if row['dryer'].pk == active_machine.pk)
        available_row = next(row for row in availability_rows if row['dryer'].pk == available_machine.pk)
        self.assertEqual(active_row['current_renter'], 'Joel Dela Cruz')
        self.assertEqual(active_row['status_label'], 'Occupied')
        self.assertEqual(active_row['freed_sacks_label'], '35 sacks')
        self.assertEqual(active_row['visible_rental_count'], 1)
        self.assertEqual(active_row['locked_rental_count'], 1)
        self.assertEqual(active_row['activity_items'][0]['stage_label'], 'Current')
        self.assertEqual(available_row['status_label'], 'Available')

    def test_dryer_availability_marks_future_booking_as_available_soon(self):
        future_machine = Machine.objects.create(
            name='Future Dryer Board',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('70.00'),
            description='Future dryer board',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        future_date = timezone.localdate() + timedelta(days=1)
        DryerRental.objects.create(
            machine=future_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=future_date,
            goods_description='Future solar batch',
            quantity='20 sacks',
            estimated_end_date=future_date,
            estimated_end_time=time(15, 0),
            status='in_progress',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:dryer_rental_list'))

        availability_rows = response.context['dryer_availability_rows']
        future_row = next(row for row in availability_rows if row['dryer'].pk == future_machine.pk)
        self.assertEqual(future_row['status_label'], 'Available Soon')
        self.assertIn('next scheduled dryer service starts', future_row['availability_message'])
        self.assertEqual(future_row['activity_items'][0]['stage_label'], 'Next Scheduled')

    def test_dryer_availability_releases_unit_after_expected_end_passes(self):
        current_now = timezone.localtime()
        ended_machine = Machine.objects.create(
            name='Ended Dryer Board',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='until_dried',
            flatbed_max_sack_capacity=Decimal('100.00'),
            description='Ended dryer board',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        ended_rental = DryerRental.objects.create(
            machine=ended_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=current_now.date(),
            goods_description='Ended batch',
            quantity='40 sacks',
            estimated_end_date=current_now.date(),
            estimated_end_time=(current_now - timedelta(hours=1)).time().replace(second=0, microsecond=0),
            status='in_progress',
        )
        DryerRental.objects.filter(pk=ended_rental.pk).update(updated_at=current_now - timedelta(hours=3))

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:dryer_rental_list'))

        availability_rows = response.context['dryer_availability_rows']
        ended_row = next(row for row in availability_rows if row['dryer'].pk == ended_machine.pk)
        self.assertEqual(ended_row['status_label'], 'Available')
        self.assertEqual(ended_row['freed_sacks_label'], '0 sacks')

    def test_dryer_availability_reflects_pending_and_waiting_confirmation_rentals(self):
        queue_machine = Machine.objects.create(
            name='Queued Dryer Board',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='per_sack',
            flatbed_max_sack_capacity=Decimal('90.00'),
            description='Queued dryer board',
            status='available',
            rental_fee_per_day=40,
            current_price='40/sack',
        )
        DryerRental.objects.create(
            machine=queue_machine,
            user=self.viewer,
            rental_type='until_dried',
            rental_date=self.rental_date,
            goods_description='Pending batch',
            quantity='12 sacks',
            status='pending',
        )
        DryerRental.objects.create(
            machine=queue_machine,
            user=self.joel,
            rental_type='until_dried',
            rental_date=self.rental_date + timedelta(days=1),
            goods_description='Waiting confirmation batch',
            quantity='18 sacks',
            status='waiting_confirmation',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Queued Dryer Board')
        self.assertContains(response, 'Pending')
        self.assertContains(response, 'Waiting for Confirmation')
        availability_rows = response.context['dryer_availability_rows']
        queue_row = next(row for row in availability_rows if row['dryer'].pk == queue_machine.pk)
        self.assertEqual(queue_row['status_label'], 'Available')
        self.assertEqual(queue_row['pending_count'], 1)
        self.assertEqual(queue_row['waiting_confirmation_count'], 1)
        self.assertEqual(queue_row['visible_rental_count'], 2)
        self.assertEqual(len(queue_row['activity_items']), 2)
        self.assertEqual(queue_row['activity_items'][0]['stage_label'], 'For Review')

    def test_admin_can_delete_dryer_unit_and_return_to_dryer_services(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:delete_machine', args=[self.machine.pk]) + '?service=dryer',
            {'delete_confirmation': 'CONFIRM'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_list'),
            fetch_redirect_response=False,
        )
        self.assertFalse(Machine.objects.filter(pk=self.machine.pk).exists())

    def test_admin_cannot_delete_dryer_unit_without_typing_confirm(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:delete_machine', args=[self.machine.pk]) + '?service=dryer',
            {'delete_confirmation': ''},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Type CONFIRM before deleting this item.', status_code=400)
        self.assertTrue(Machine.objects.filter(pk=self.machine.pk).exists())

    def test_admin_dryer_list_includes_delete_modal_markup(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="deleteDryerModal"', html=False)
        self.assertContains(response, 'data-delete-machine-name')
        self.assertContains(response, 'data-delete-url')
        self.assertContains(response, 'data-delete-confirmation-word="CONFIRM"', html=False)

    def test_machine_create_dryer_mode_prefills_dryer_setup_context(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:machine_create') + '?service=dryer&machine_type=solar_dryer'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_dryer_setup_flow'])
        self.assertEqual(response.context['form'].initial['machine_type'], 'solar_dryer')
        self.assertEqual(response.context['form'].initial['dryer_pricing_type'], 'per_sack')
        self.assertFalse(response.context['show_machine_type_field'])
        self.assertContains(response, 'Create Solar Dryer')
        self.assertContains(response, 'Back to Dryer Services')
        self.assertContains(response, 'Solar dryer tip')
        self.assertContains(response, 'type="hidden"', html=False)
        self.assertNotContains(response, 'id="div_id_machine_type"', html=False)
        self.assertContains(response, 'id="id_dryer_pricing_type"', html=False)
        self.assertContains(response, 'id="id_flatbed_max_sack_capacity"', html=False)
        self.assertContains(response, 'value="hourly"', html=False)
        self.assertContains(response, 'value="per_sack"', html=False)
        self.assertNotContains(response, 'value="until_dried"', html=False)
        self.assertContains(response, 'Per Hour')
        self.assertContains(response, 'Per Sack')
        self.assertContains(response, 'By Hour')
        self.assertContains(response, 'Until Dried')

    def test_flatbed_dryer_create_page_shows_sack_capacity_field(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:machine_create') + '?service=dryer&machine_type=flatbed_dryer'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dryer Sack Capacity')
        self.assertContains(response, 'id="id_flatbed_max_sack_capacity"', html=False)

    def test_machine_form_requires_flatbed_capacity_for_flatbed_dryers(self):
        form = MachineForm(
            data={
                'name': 'Flatbed Dryer Missing Capacity',
                'description': 'Missing flatbed capacity field',
                'status': 'available',
                'machine_type': 'flatbed_dryer',
                'dryer_pricing_type': 'hourly',
                'dryer_hourly_rate': '175',
                'flatbed_max_sack_capacity': '',
                'current_price': '',
                'rental_price_type': 'cash',
                'allow_online_payment': 'on',
                'allow_face_to_face_payment': 'on',
                'settlement_type': 'immediate',
                'in_kind_farmer_share': '9',
                'in_kind_organization_share': '1',
            },
            is_dryer_setup_flow=True,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('flatbed_max_sack_capacity', form.errors)

    def test_generic_dryer_create_page_prompts_for_dryer_type_first(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:machine_create') + '?service=dryer'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_dryer_setup_flow'])
        self.assertFalse(response.context['dryer_type_is_locked'])
        self.assertContains(response, 'Create Dryer Unit')
        self.assertContains(response, 'PHP 35/sack.')
        self.assertContains(response, 'Solar Dryer')
        self.assertContains(response, '?service=dryer&machine_type=solar_dryer')
        self.assertNotContains(response, 'id="machine-form"', html=False)

    def test_machine_form_accepts_hourly_dryer_without_current_price_input(self):
        form = MachineForm(
            data={
                'name': 'Flatbed Dryer 2',
                'description': 'Hourly dryer validation',
                'status': 'available',
                'machine_type': 'flatbed_dryer',
                'dryer_pricing_type': 'hourly',
                'dryer_hourly_rate': '175',
                'flatbed_max_sack_capacity': '180',
                'current_price': '',
                'rental_price_type': 'cash',
                'allow_online_payment': 'on',
                'allow_face_to_face_payment': 'on',
                'settlement_type': 'immediate',
                'in_kind_farmer_share': '9',
                'in_kind_organization_share': '1',
            },
            is_dryer_setup_flow=True,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_machine_form_accepts_solar_dryer_per_sack_pricing(self):
        form = MachineForm(
            data={
                'name': 'Solar Dryer 1',
                'description': 'Solar dryer priced by sack',
                'status': 'available',
                'machine_type': 'solar_dryer',
                'dryer_pricing_type': 'per_sack',
                'dryer_hourly_rate': '',
                'flatbed_max_sack_capacity': '80',
                'current_price': '45',
                'rental_price_type': 'cash',
                'allow_online_payment': 'on',
                'allow_face_to_face_payment': 'on',
                'settlement_type': 'immediate',
                'in_kind_farmer_share': '9',
                'in_kind_organization_share': '1',
            },
            is_dryer_setup_flow=True,
        )

        self.assertTrue(form.is_valid(), form.errors)
        machine = form.save(commit=False)
        self.assertEqual(machine.dryer_pricing_type, 'per_sack')
        self.assertEqual(machine.current_price, '45.00/sack')

    def test_machine_form_accepts_asset_tracking_fields(self):
        form = MachineForm(
            data={
                'name': 'Tracked Tractor',
                'brand_name': 'Kubota',
                'model_name': 'L4708',
                'model_year': '2024',
                'horsepower': '45.50',
                'acquisition_date': '2026-04-01',
                'acquisition_amount': '650000.00',
                'description': 'Machine with acquisition details',
                'status': 'available',
                'machine_type': 'tractor_4wd',
                'dryer_pricing_type': 'hourly',
                'dryer_hourly_rate': '',
                'current_price': '4000',
                'pricing_unit': 'hectare',
                'rental_price_type': 'cash',
                'allow_online_payment': 'on',
                'allow_face_to_face_payment': 'on',
                'settlement_type': 'immediate',
                'in_kind_farmer_share': '9',
                'in_kind_organization_share': '1',
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        machine = form.save(commit=False)
        self.assertEqual(machine.brand_name, 'Kubota')
        self.assertEqual(machine.model_name, 'L4708')
        self.assertEqual(machine.model_year, 2024)
        self.assertEqual(machine.horsepower, Decimal('45.50'))
        self.assertEqual(str(machine.acquisition_date), '2026-04-01')
        self.assertEqual(machine.acquisition_amount, Decimal('650000.00'))


class RentalPackageRequestFormTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='package_form_admin',
            email='package_form_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='package_form_member',
            email='package_form_member@example.com',
            password='testpassword123',
            first_name='Juan',
            last_name='Dela Cruz',
            address='Barangay San Roque',
            is_verified=True,
        )
        self.tractor_a = Machine.objects.create(
            name='Package Tractor A',
            machine_type='tractor_4wd',
            description='First tractor option for package form tests.',
            brand_name='Kubota',
            model_name='L4708',
            model_year=2024,
            status='available',
            rental_fee_per_day=Decimal('3000.00'),
            current_price='3000/hectare',
        )
        self.tractor_b = Machine.objects.create(
            name='Package Tractor B',
            machine_type='tractor_4wd',
            description='Second tractor option for package form tests.',
            status='available',
            rental_fee_per_day=Decimal('4500.00'),
            current_price='4500/hectare',
        )
        self.planter = Machine.objects.create(
            name='Package Planter',
            machine_type='transplanter_walking',
            description='Planter option for package form tests.',
            status='available',
            rental_fee_per_day=Decimal('1800.00'),
            current_price='1800/flat',
        )
        self.harvester = Machine.objects.create(
            name='Package Harvester',
            machine_type='harvester',
            description='Harvester option for package form tests.',
            status='available',
            rental_fee_per_day=Decimal('0.00'),
            current_price='0',
        )
        self.thresher = Machine.objects.create(
            name='Package Thresher',
            machine_type='thresher',
            description='Thresher option for package form tests.',
            status='available',
            rental_fee_per_day=Decimal('0.00'),
            current_price='0',
        )
        self.start_date = date.today() + timedelta(days=5)
        self.required_service_selection = {
            'include_tractor': 'on',
            'include_rotavator': 'on',
            'include_planter': 'on',
            'tractor_machine': str(self.tractor_a.pk),
            'rotavator_machine': str(self.tractor_b.pk),
            'planter_machine': str(self.planter.pk),
        }

    def test_admin_package_form_accepts_selected_member(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'selected_member_id': str(self.member.pk),
                'farmer_name': 'Ju',
                'location': '',
                'area': '2.50',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'As soon as possible',
                'payment_preference': 'face_to_face',
                'notes': 'Admin-assisted booking',
                **self.required_service_selection,
            },
            user=self.admin,
        )

        self.assertTrue(form.is_valid(), form.errors)
        package = form.save(commit=False)
        self.assertEqual(package.user, self.member)
        self.assertEqual(package.farmer_name, 'Juan Dela Cruz')
        self.assertEqual(package.location, 'Barangay San Roque')
        self.assertEqual(package.area, Decimal('2.50'))

    def test_admin_package_form_accepts_walk_in_renter(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'selected_member_id': '',
                'farmer_name': 'Walk-In Farmer',
                'location': 'Sitio Maligaya',
                'area': '1.75',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Walk-in request',
                'payment_preference': 'face_to_face',
                'notes': 'Booked by admin for walk-in',
                **self.required_service_selection,
            },
            user=self.admin,
        )

        self.assertTrue(form.is_valid(), form.errors)
        package = form.save(commit=False)
        self.assertEqual(package.user.username, 'system')
        self.assertEqual(package.farmer_name, 'Walk-In Farmer')
        self.assertEqual(package.location, 'Sitio Maligaya')
        self.assertEqual(package.area, Decimal('1.75'))

    def test_package_form_persists_selected_service_machine(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay San Roque',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Use the selected tractor',
                'payment_preference': 'face_to_face',
                'notes': 'Specific tractor requested',
                **self.required_service_selection,
                'tractor_machine': str(self.tractor_b.pk),
            },
            user=self.member,
        )

        self.assertTrue(form.is_valid(), form.errors)
        package = form.save()
        item = package.items.get(service_code='tractor')

        self.assertEqual(item.machine, self.tractor_b)
        self.assertEqual(item.rate, Decimal('4500.00'))
        self.assertEqual(item.pricing_unit, 'hectare')
        self.assertEqual(item.machine_type_required, 'tractor')

    def test_package_form_machine_dropdown_shows_model_and_price_summary(self):
        form = RentalPackageRequestForm(user=self.member)

        label = form.fields['tractor_machine'].label_from_instance(self.tractor_a)

        self.assertEqual(
            label,
            'Package Tractor A | Kubota L4708 (2024) | PHP 3,000.00 / hectare',
        )

    def test_package_form_rejects_fewer_than_two_selected_services(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay San Roque',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Too few services selected',
                'payment_preference': 'face_to_face',
                'notes': 'Should fail validation',
                'include_tractor': 'on',
                'include_rotavator': 'on',
                'tractor_machine': str(self.tractor_a.pk),
                'rotavator_machine': str(self.tractor_b.pk),
            },
            user=self.member,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_package_form_accepts_five_selected_services(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay San Roque',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Use all services',
                'payment_preference': 'face_to_face',
                'notes': 'Should pass validation',
                'include_tractor': 'on',
                'include_rotavator': 'on',
                'include_planter': 'on',
                'include_harvester': 'on',
                'include_thresher': 'on',
                'tractor_machine': str(self.tractor_a.pk),
                'rotavator_machine': str(self.tractor_b.pk),
                'planter_machine': str(self.planter.pk),
                'harvester_machine': str(self.harvester.pk),
                'thresher_machine': str(self.thresher.pk),
            },
            user=self.member,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_machine_package_price_preview_estimates_hectare_total(self):
        preview = self.tractor_a.get_package_price_preview(area=Decimal('3.00'))

        self.assertEqual(preview['mode'], 'per_hectare')
        self.assertEqual(preview['estimate_label'], 'Estimated total')
        self.assertEqual(preview['estimate_value'], '9000.00')

    def test_machine_package_price_preview_estimates_flat_fee_total(self):
        hand_tractor = Machine.objects.create(
            name='Package Hand Tractor',
            machine_type='hand_tractor',
            description='Flat-fee machine for package price preview.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/flat',
        )

        preview = hand_tractor.get_package_price_preview(area=Decimal('3.00'))

        self.assertEqual(preview['mode'], 'flat_fee')
        self.assertEqual(preview['estimate_label'], 'Estimated total')
        self.assertEqual(preview['estimate_value'], '1000.00')

    def test_machine_package_price_preview_marks_sack_pricing_as_rate_only(self):
        harvester = Machine.objects.create(
            name='Package Harvester',
            machine_type='harvester',
            description='Sack-based machine for package price preview.',
            status='available',
            rental_fee_per_day=Decimal('0.00'),
            current_price='0',
        )

        preview = harvester.get_package_price_preview(area=Decimal('3.00'))

        self.assertEqual(preview['mode'], 'rate_only_sack')
        self.assertEqual(preview['estimate_label'], 'Rate only')
        self.assertEqual(preview['estimate_value'], '')

    def test_machine_category_is_derived_from_specific_machine_type(self):
        self.assertEqual(self.tractor_a.machine_category, 'tractor')
        self.assertEqual(self.tractor_b.machine_category, 'tractor')

    def test_tractor_service_category_accepts_hand_tractor_choice(self):
        hand_tractor = Machine.objects.create(
            name='Package Hand Tractor',
            machine_type='hand_tractor',
            description='Hand tractor grouped under tractor category.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/flat',
        )

        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay San Roque',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Allow grouped tractor category',
                'payment_preference': 'face_to_face',
                'notes': 'Hand tractor selected under tractor service',
                **self.required_service_selection,
                'tractor_machine': str(hand_tractor.pk),
            },
            user=self.member,
        )

        self.assertTrue(form.is_valid(), form.errors)
        package = form.save()
        item = package.items.get(service_code='tractor')
        self.assertEqual(item.machine, hand_tractor)

    def test_package_form_requires_machine_for_each_selected_service(self):
        form = RentalPackageRequestForm(
            data={
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay San Roque',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Missing planter machine',
                'payment_preference': 'face_to_face',
                'notes': 'Should fail when a selected service has no machine',
                'include_tractor': 'on',
                'include_rotavator': 'on',
                'include_planter': 'on',
                'tractor_machine': str(self.tractor_a.pk),
                'rotavator_machine': str(self.tractor_b.pk),
            },
            user=self.member,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('planter_machine', form.errors)


class RentalPackageNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='package_notify_admin',
            email='package_notify_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='package_notify_member',
            email='package_notify_member@example.com',
            password='testpassword123',
            first_name='Nelsie',
            last_name='Farmer',
            address='Barangay Proper',
            is_verified=True,
        )
        self.tractor = Machine.objects.create(
            name='Notify Tractor',
            machine_type='tractor_4wd',
            description='Machine for package notification tests.',
            status='available',
            rental_fee_per_day=Decimal('3000.00'),
            current_price='3000/hectare',
        )
        self.rotavator = Machine.objects.create(
            name='Notify Rotavator',
            machine_type='hand_tractor',
            description='Machine for package notification tests.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/flat',
        )
        self.start_date = date.today() + timedelta(days=5)

    def test_package_create_sends_member_and_admin_notifications(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('machines:rental_package_create'),
            {
                'package_name': 'Whole Farming Service Package',
                'farmer_name': self.member.get_full_name(),
                'location': 'Barangay Proper',
                'area': '3.00',
                'preferred_start_date': self.start_date.isoformat(),
                'payment_preference': 'face_to_face',
                'notes': 'Package request notification test',
                'include_tractor': 'on',
                'include_rotavator': 'on',
                'tractor_machine': str(self.tractor.pk),
                'rotavator_machine': str(self.rotavator.pk),
            },
            follow=False,
        )

        package = RentalPackage.objects.latest('id')

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[package.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_package_submitted',
                related_object_id=package.pk,
            ).exists()
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.admin,
                notification_type='rental_package_new_request',
                related_object_id=package.pk,
            ).exists()
        )


class OperatorAllJobsCountTests(TestCase):
    def setUp(self):
        self.operator = User.objects.create_user(
            username='operator_jobs_viewer',
            email='operator_jobs_viewer@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.member = User.objects.create_user(
            username='operator_jobs_member',
            email='operator_jobs_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Operator Queue Tractor',
            machine_type='tractor_4wd',
            description='Machine used for operator queue tests.',
            status='available',
            rental_fee_per_day=Decimal('3000.00'),
            current_price='3000/hectare',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        self.client.force_login(self.operator)

    def _create_job(self, **overrides):
        payload = {
            'machine': self.machine,
            'user': self.member,
            'assigned_operator': self.operator,
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'status': 'approved',
            'workflow_state': 'approved',
            'operator_status': 'assigned',
            'payment_type': 'cash',
            'payment_status': 'pending',
            'payment_method': 'face_to_face',
            'purpose': 'Operator queue classification test',
        }
        payload.update(overrides)
        return Rental.objects.create(**payload)

    def test_operator_all_jobs_counts_do_not_treat_waiting_validation_as_ongoing(self):
        active_job = self._create_job(
            workflow_state='in_progress',
            operator_status='operating',
        )
        waiting_admin_job = self._create_job(
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=2),
            workflow_state='in_progress',
            operator_status='completed',
            actual_completion_time=timezone.now(),
        )
        assigned_job = self._create_job(
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=3),
            workflow_state='approved',
            operator_status='assigned',
        )

        response = self.client.get(reverse('machines:operator_all_jobs'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filter_counts']['all'], 3)
        self.assertEqual(response.context['filter_counts']['assigned'], 1)
        self.assertEqual(response.context['filter_counts']['ongoing'], 1)
        self.assertEqual(response.context['filter_counts']['completed'], 1)
        self.assertEqual(response.context['current_ongoing_job_id'], active_job.id)
        self.assertIn(assigned_job.id, [job.id for job in response.context['jobs']])
        self.assertIn(waiting_admin_job.id, [job.id for job in response.context['jobs']])

    def test_operator_all_jobs_assigned_filter_only_shows_waiting_jobs(self):
        self._create_job(
            workflow_state='in_progress',
            operator_status='operating',
        )
        self._create_job(
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=2),
            workflow_state='in_progress',
            operator_status='completed',
            actual_completion_time=timezone.now(),
        )
        assigned_job = self._create_job(
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=3),
            workflow_state='approved',
            operator_status='assigned',
        )

        response = self.client.get(reverse('machines:operator_all_jobs'), {'status': 'assigned'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([job.id for job in response.context['jobs']], [assigned_job.id])

    def test_operator_all_jobs_treats_completed_rental_as_finished_even_if_operator_status_is_stale(self):
        completed_job = self._create_job(
            workflow_state='completed',
            status='completed',
            operator_status='assigned',
            actual_completion_time=timezone.now(),
        )

        response = self.client.get(reverse('machines:operator_all_jobs'))

        self.assertEqual(response.status_code, 200)
        rendered_job = next(job for job in response.context['jobs'] if job.id == completed_job.id)
        self.assertEqual(rendered_job.priority, 3)
        self.assertTrue(rendered_job.operator_card_is_completed)
        self.assertFalse(rendered_job.operator_card_is_assigned)
        self.assertFalse(rendered_job.operator_card_can_accept)
        self.assertEqual(rendered_job.operator_card_status_label, 'Completed')


class AdminRentalDashboardAccessTestCase(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username='member_redirect',
            email='member_redirect@example.com',
            password='testpassword123',
            is_verified=True,
        )

    def test_member_is_redirected_to_rental_list_from_admin_dashboard(self):
        self.client.force_login(self.member)

        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertRedirects(
            response,
            reverse('machines:rental_list'),
            fetch_redirect_response=False,
        )


class AdminConflictsReportViewTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='conflicts_admin',
            email='conflicts_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )

    def test_conflicts_report_uses_simplified_sections(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:admin_conflicts_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rental Conflicts')
        self.assertContains(response, 'Conflict Review Queue')
        self.assertContains(response, 'Approved Rental Conflicts')
        self.assertNotContains(response, 'Pending Requests With Conflict Risk')
        self.assertNotContains(response, 'Review Pending Rental')


class AdminRentalDashboardConflictBadgeTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='dashboard_conflicts_admin',
            email='dashboard_conflicts_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member_a = User.objects.create_user(
            username='dashboard_conflict_member_a',
            email='dashboard_conflict_member_a@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.member_b = User.objects.create_user(
            username='dashboard_conflict_member_b',
            email='dashboard_conflict_member_b@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Dashboard Conflict Tractor',
            machine_type='tractor_4wd',
            description='Dashboard conflict badge test tractor',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000.00/hectare',
        )
        Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=7),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
            payment_method='face_to_face',
            payment_amount=Decimal('8000.00'),
            area=Decimal('2.0000'),
        )
        rental_b = Rental.objects.create(
            user=self.member_b,
            machine=self.machine,
            start_date=date.today() + timedelta(days=9),
            end_date=date.today() + timedelta(days=10),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
            payment_method='face_to_face',
            payment_amount=Decimal('8000.00'),
            area=Decimal('2.0000'),
        )
        Rental.objects.filter(pk=rental_b.pk).update(
            start_date=date.today() + timedelta(days=6),
            end_date=date.today() + timedelta(days=8),
        )

    def test_dashboard_conflict_button_shows_conflict_alert_badge(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.context['conflict_alert_count'], 0)
        self.assertContains(response, 'Conflict Review')
        self.assertContains(response, f'>{response.context["conflict_alert_count"]}<', html=False)


class AdminSettlementQueueActionTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='settlement_admin',
            email='settlement_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='settlement_member',
            email='settlement_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Harvest Tractor',
            machine_type='tractor_4wd',
            description='In-kind tractor for settlement queue tests',
            status='rented',
            rental_fee_per_day=Decimal('1500.00'),
            current_price='in-kind',
            rental_price_type='in_kind',
            settlement_type='after_harvest',
            in_kind_farmer_share=Decimal('9.00'),
            in_kind_organization_share=Decimal('1.00'),
        )
        self.rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            payment_type='in_kind',
            payment_status='pending',
            settlement_status='waiting_for_delivery',
            status='approved',
            workflow_state='harvest_report_submitted',
            total_harvest_sacks=Decimal('10.00'),
            organization_share_required=Decimal('0.00'),
        )

    def test_dashboard_shows_confirm_delivery_for_waiting_in_kind_rental(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Delivery')
        self.assertContains(response, 'dashboardActionModal')
        self.assertContains(response, 'js-dashboard-confirm')
        self.assertNotContains(response, "return confirm('Confirm rice delivery and complete this rental?');")
        self.assertNotContains(response, "prompt('Enter rejection reason (optional):')")


class MachineMaintenanceVisibilityTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='maintenance_member',
            email='maintenance_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='maintenance_admin',
            email='maintenance_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_superuser=True,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Field Tractor',
            machine_type='tractor_4wd',
            description='Primary field tractor',
            status='maintenance',
            rental_fee_per_day=Decimal('1500.00'),
            current_price='1500/day',
        )
        start = timezone.now() - timedelta(days=1)
        end = timezone.now() + timedelta(days=5)
        self.maintenance = Maintenance.objects.create(
            machine=self.machine,
            description='Repair work on the hydraulic system. Hydraulic pump failed during field operation.',
            maintenance_type='emergency',
            start_date=start,
            end_date=end,
            status='in_progress',
            created_by=self.user,
        )

    def _create_available_machine(self, name='Ready Tractor'):
        return Machine.objects.create(
            name=name,
            machine_type='tractor_4wd',
            description='Available machine for rental flow tests.',
            status='available',
            rental_fee_per_day=Decimal('1200.00'),
            current_price='1200/day',
        )

    def test_machine_list_shows_issue_button_and_hides_rent_link(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Issue')
        self.assertContains(response, 'Hydraulic pump failed during field operation.')
        self.assertNotContains(response, reverse('machines:rent_machine', args=[self.machine.pk]))

    def test_machine_list_view_button_uses_rent_preview_for_standard_machine(self):
        rentable_machine = self._create_available_machine(name='Preview Flow Tractor')
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("machines:rent_machine", args=[rentable_machine.pk])}" class="machine-btn machine-btn-outline"',
            html=False,
        )
        self.assertContains(response, '<span>View</span>', html=False)

    def test_machine_list_shows_machine_data_specs_on_card(self):
        Machine.objects.create(
            name='Spec Display Tractor',
            machine_type='tractor_4wd',
            description='Machine used to verify machine data details on the list card.',
            status='available',
            rental_fee_per_day=Decimal('2500.00'),
            current_price='2500/day',
            brand_name='AgriMax',
            model_name='TRX-9000',
            horsepower=Decimal('88.50'),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machine data')
        self.assertContains(response, 'AgriMax')
        self.assertContains(response, 'TRX-9000')
        self.assertContains(response, '88.50 HP')

    def test_machine_delete_actions_require_confirm_text(self):
        self.client.force_login(self.admin)

        list_response = self.client.get(reverse('machines:machine_list'))
        detail_response = self.client.get(reverse('machines:machine_detail', args=[self.machine.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(list_response, 'data-delete-confirmation-word="CONFIRM"', html=False)
        self.assertContains(detail_response, 'data-delete-confirmation-word="CONFIRM"', html=False)

    def test_machine_list_keeps_future_reserved_machine_available(self):
        future_machine = self._create_available_machine(name='Future Reserved List Tractor')
        future_member = User.objects.create_user(
            username='future_list_member',
            email='future_list_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        Rental.objects.create(
            machine=future_machine,
            user=future_member,
            customer_name='Future List Member',
            customer_address='Future List Farm',
            field_location='Future List Farm',
            area=Decimal('1.2500'),
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=3),
            purpose='Future list reservation',
            status='approved',
            workflow_state='in_progress',
            operator_status='operating',
            payment_type='cash',
            settlement_type='immediate',
            payment_status='paid',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Future Reserved List Tractor')
        self.assertNotContains(response, '<span class="machine-status-badge in-use">In Use</span>', html=False)

    def test_machine_list_hides_filter_card_for_regular_users(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'machine-list-page')
        self.assertNotContains(response, 'page-filter-card__title">Filter Machines', html=False)
        self.assertNotContains(response, 'placeholder="Machine name or description"', html=False)
        self.assertNotContains(response, 'machine-filter-control')

    def test_machine_list_keeps_filter_card_for_admin_users(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filter Machines')
        self.assertContains(response, 'machine-filter-form')
        self.assertContains(response, 'machine-filter-control')

    def test_machine_list_unverified_user_gets_submit_membership_modal_on_rent_click(self):
        rentable_machine = self._create_available_machine(name='Rentable Tractor')
        unverified_user = User.objects.create_user(
            username='rent_unverified',
            email='rent_unverified@example.com',
            password='testpassword123',
            is_verified=False,
            membership_form_submitted=False,
        )
        self.client.force_login(unverified_user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'onclick="showVerificationModal()"', html=False)
        self.assertContains(response, 'Please submit your membership form first.')
        self.assertContains(
            response,
            'After submission, wait for the admin to verify your account before renting equipment.',
        )
        self.assertContains(response, reverse('submit_membership_form'))
        self.assertNotContains(response, reverse('machines:rent_machine', args=[rentable_machine.pk]))

    def test_machine_list_unverified_user_with_submitted_form_gets_wait_for_admin_message(self):
        self._create_available_machine(name='Pending Verification Tractor')
        pending_user = User.objects.create_user(
            username='rent_pending_verification',
            email='rent_pending_verification@example.com',
            password='testpassword123',
            is_verified=False,
            membership_form_submitted=True,
        )
        self.client.force_login(pending_user)

        response = self.client.get(reverse('machines:machine_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your membership form is already submitted.')
        self.assertContains(
            response,
            'Please wait for the admin to verify your account before renting equipment.',
        )
        self.assertContains(response, reverse('profile'))

    def test_machine_detail_unverified_user_can_click_rent_and_view_membership_modal(self):
        rentable_machine = self._create_available_machine(name='Detail Rent Tractor')
        unverified_user = User.objects.create_user(
            username='detail_unverified',
            email='detail_unverified@example.com',
            password='testpassword123',
            is_verified=False,
            membership_form_submitted=False,
        )
        self.client.force_login(unverified_user)

        response = self.client.get(reverse('machines:machine_detail', args=[rentable_machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'onclick="showVerificationModal()"', html=False)
        self.assertContains(response, 'Please submit your membership form first.')
        self.assertContains(response, reverse('submit_membership_form'))

    def test_machine_detail_exposes_active_maintenance_issue(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:machine_detail', args=[self.machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_maintenance_record'], self.maintenance)
        self.assertContains(response, 'Hydraulic pump failed during field operation.')
        self.assertContains(response, 'View Issue')

    def test_rent_preview_redirects_when_machine_is_under_maintenance(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rent_machine', args=[self.machine.pk]))

        self.assertRedirects(
            response,
            reverse('machines:machine_detail', args=[self.machine.pk]),
            fetch_redirect_response=False,
        )

    def test_rent_preview_primary_action_points_to_rental_form(self):
        rentable_machine = self._create_available_machine(name='Preview CTA Tractor')
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rent_machine', args=[rentable_machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('machines:rental_create_for_machine', args=[rentable_machine.pk]))
        self.assertContains(response, 'Rent This Machine')

    def test_rental_detail_url_redirects_to_confirmation(self):
        rentable_machine = self._create_available_machine(name='Redirect Tractor')
        rental = Rental.objects.create(
            machine=rentable_machine,
            user=self.user,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=3),
            status='pending',
            workflow_state='requested',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rental_detail', args=[rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:rental_confirmation', args=[rental.pk]),
            fetch_redirect_response=False,
        )

    def test_rental_confirmation_hides_receipt_until_payment_is_made(self):
        rentable_machine = self._create_available_machine(name='Receipt Guard Tractor')
        rental = Rental.objects.create(
            machine=rentable_machine,
            user=self.user,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=2),
            status='pending',
            workflow_state='pending_approval',
            payment_method='face_to_face',
            payment_status='pending',
            payment_verified=False,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rental_confirmation', args=[rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Open Receipt')
        self.assertContains(response, 'View My Rentals')

    def test_rental_confirmation_shows_machine_details_with_formatted_rate(self):
        rentable_machine = self._create_available_machine(name='Detail Tractor')
        rentable_machine.current_price = '4000/day'
        rentable_machine.allow_online_payment = True
        rentable_machine.allow_face_to_face_payment = True
        rentable_machine.save(update_fields=['current_price', 'allow_online_payment', 'allow_face_to_face_payment'])
        rental = Rental.objects.create(
            machine=rentable_machine,
            user=self.user,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=4),
            status='pending',
            workflow_state='pending_approval',
            payment_method='online',
            payment_status='pending',
            payment_verified=False,
        )
        rental.payment_amount = rental.calculate_payment_amount()
        rental.save(update_fields=['payment_amount'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rental_confirmation', args=[rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machine')
        self.assertContains(response, 'Detail Tractor')
        self.assertContains(response, 'PHP 4,000.00 / day')
        self.assertContains(response, 'PHP 12000.00')
        self.assertContains(response, 'Gcash payment or Over the counter')

    def test_rental_confirmation_formats_purpose_as_compact_detail_rows(self):
        rentable_machine = self._create_available_machine(name='Purpose Layout Tractor')
        rental = Rental.objects.create(
            machine=rentable_machine,
            user=self.user,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=2),
            status='pending',
            workflow_state='pending_approval',
            purpose='Requester: Neil Micho Valiao\n\nOperator: BUFIA Operator\nService Type: Harvesting\nLand Area: 3.00 hectares',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:rental_confirmation', args=[rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Purpose / Notes')
        self.assertContains(response, 'purpose-detail-list__row', html=False)
        self.assertContains(response, 'Requester')
        self.assertContains(response, 'Neil Micho Valiao')
        self.assertContains(response, 'Operator')
        self.assertContains(response, 'BUFIA Operator')

    def test_daily_priced_rental_uses_duration_not_area_for_payment_amount(self):
        rentable_machine = self._create_available_machine(name='Daily Rate Tractor')
        rentable_machine.current_price = '4000/day'
        rentable_machine.save(update_fields=['current_price'])

        rental = Rental.objects.create(
            machine=rentable_machine,
            user=self.user,
            start_date=timezone.localdate() + timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=3),
            area=Decimal('1.00'),
            status='pending',
            workflow_state='pending_approval',
        )

        self.assertEqual(rental.get_duration_days(), 3)
        self.assertEqual(rental.calculate_payment_amount(), Decimal('12000.00'))

    def test_rental_form_excludes_machines_with_active_maintenance(self):
        form = RentalForm(user=self.user)

        self.assertNotIn(self.machine, form.fields['machine'].queryset)

    def test_maintenance_update_marks_machine_back_under_maintenance(self):
        self.client.force_login(self.admin)
        self.machine.status = 'available'
        self.machine.save(update_fields=['status'])
        self.maintenance.status = 'scheduled'
        self.maintenance.actual_completion_date = None
        self.maintenance.save(update_fields=['status', 'actual_completion_date'])

        response = self.client.post(
            reverse('machines:maintenance_update', args=[self.maintenance.pk]),
            {
                'machine': self.machine.pk,
                'maintenance_type': self.maintenance.maintenance_type,
                'description': self.maintenance.description,
                'start_date': self.maintenance.start_date.strftime('%Y-%m-%dT%H:%M'),
                'end_date': self.maintenance.end_date.strftime('%Y-%m-%dT%H:%M'),
                'technician_name': '',
                'status': 'in_progress',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:maintenance_detail', args=[self.maintenance.pk]),
            fetch_redirect_response=False,
        )
        self.machine.refresh_from_db()
        self.maintenance.refresh_from_db()
        self.assertEqual(self.machine.status, 'maintenance')
        self.assertIsNone(self.maintenance.actual_completion_date)

    def test_machine_sync_status_returns_to_rented_when_maintenance_finishes_during_active_rental(self):
        today = timezone.localdate()
        Rental.objects.create(
            machine=self.machine,
            user=self.user,
            start_date=today,
            end_date=today + timedelta(days=1),
            status='approved',
            workflow_state='in_progress',
        )
        self.maintenance.status = 'completed'
        self.maintenance.actual_completion_date = timezone.now()
        self.maintenance.save(update_fields=['status', 'actual_completion_date'])

        self.machine.sync_status()

        self.machine.refresh_from_db()
        self.assertEqual(self.machine.status, 'rented')

    def test_admin_can_start_scheduled_maintenance_and_machine_stays_blocked(self):
        self.client.force_login(self.admin)
        self.maintenance.status = 'scheduled'
        self.maintenance.actual_completion_date = None
        self.maintenance.save(update_fields=['status', 'actual_completion_date'])
        self.machine.status = 'available'
        self.machine.save(update_fields=['status'])

        response = self.client.post(reverse('machines:maintenance_start', args=[self.maintenance.pk]))

        self.assertRedirects(
            response,
            reverse('machines:maintenance_detail', args=[self.maintenance.pk]),
            fetch_redirect_response=False,
        )
        self.maintenance.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(self.maintenance.status, 'in_progress')
        self.assertEqual(self.machine.status, 'maintenance')

    def test_finish_maintenance_requires_part_row_or_checkbox(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:maintenance_complete', args=[self.maintenance.pk]),
            {
                'repair_summary': 'Hydraulic system repaired and tested.',
                'no_parts_replaced': '',
                'labor_cost': '500.00',
                'other_cost': '0.00',
                'technician_name': 'Mario Santos',
                'completion_notes': 'Ready for field deployment.',
                'actual_completion_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'parts-TOTAL_FORMS': '1',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-part_name': '',
                'parts-0-quantity': '',
                'parts-0-unit_price': '',
                'parts-0-subtotal': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add at least one part row or select &quot;No parts replaced&quot;.')
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.status, 'in_progress')

    def test_finish_maintenance_saves_parts_and_releases_machine(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:maintenance_complete', args=[self.maintenance.pk]),
            {
                'repair_summary': 'Replaced the damaged hydraulic pump and seals.',
                'no_parts_replaced': '',
                'labor_cost': '500.00',
                'other_cost': '125.00',
                'technician_name': 'Mario Santos',
                'completion_notes': 'Pressure test passed after replacement.',
                'actual_completion_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'parts-TOTAL_FORMS': '2',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-part_name': 'Hydraulic Pump',
                'parts-0-quantity': '1',
                'parts-0-unit_price': '2500.00',
                'parts-0-subtotal': '2500.00',
                'parts-1-part_name': 'Seal Kit',
                'parts-1-quantity': '2',
                'parts-1-unit_price': '300.00',
                'parts-1-subtotal': '600.00',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:maintenance_detail', args=[self.maintenance.pk]),
            fetch_redirect_response=False,
        )

        self.maintenance.refresh_from_db()
        self.machine.refresh_from_db()

        self.assertEqual(self.maintenance.status, 'completed')
        self.assertEqual(self.maintenance.technician_name, 'Mario Santos')
        self.assertEqual(self.maintenance.parts_used.count(), 2)
        self.assertEqual(self.maintenance.parts_total, Decimal('3100.00'))
        self.assertEqual(self.maintenance.actual_cost, Decimal('3725.00'))
        self.assertEqual(self.machine.status, 'available')
        self.assertTrue(
            MaintenancePartUsed.objects.filter(
                maintenance_record=self.maintenance,
                part_name='Hydraulic Pump',
                subtotal=Decimal('2500.00'),
            ).exists()
        )

    def test_finish_maintenance_keeps_machine_in_maintenance_when_another_record_is_active(self):
        self.client.force_login(self.admin)
        Maintenance.objects.create(
            machine=self.machine,
            description='Follow-up brake inspection. Brake pedal response is inconsistent.',
            maintenance_type='corrective',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=2),
            status='scheduled',
            created_by=self.admin,
        )

        response = self.client.post(
            reverse('machines:maintenance_complete', args=[self.maintenance.pk]),
            {
                'repair_summary': 'Hydraulic work completed.',
                'no_parts_replaced': 'on',
                'labor_cost': '',
                'other_cost': '',
                'technician_name': 'Mario Santos',
                'completion_notes': 'Waiting on separate brake job.',
                'actual_completion_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'parts-TOTAL_FORMS': '1',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-part_name': '',
                'parts-0-quantity': '',
                'parts-0-unit_price': '',
                'parts-0-subtotal': '',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:maintenance_detail', args=[self.maintenance.pk]),
            fetch_redirect_response=False,
        )
        self.maintenance.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(self.maintenance.status, 'completed')
        self.assertEqual(self.machine.status, 'maintenance')


class DryerOnlinePaymentFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dryerpayuser',
            email='dryerpay@example.com',
            password='testpassword123',
            first_name='Dryer',
            last_name='Payer',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='dryerstaffpay',
            email='dryerstaffpay@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Flatbed Dryer 2',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            dryer_hourly_rate=Decimal('150.00'),
            description='Dryer for payment flow testing',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        self.dryer_rental = DryerRental.objects.create(
            machine=self.machine,
            user=self.user,
            rental_date=date.today() + timedelta(days=2),
            start_time=time(13, 0),
            end_time=time(15, 0),
            requested_hours=Decimal('2.00'),
            status='paid',
            payment_method='online',
        )
        self.payment = Payment.objects.create(
            user=self.user,
            payment_type='dryer',
            amount=Decimal('300.00'),
            currency='PHP',
            status='pending',
            stripe_session_id='cs_test_dryer_123',
            content_type=ContentType.objects.get_for_model(DryerRental),
            object_id=self.dryer_rental.id,
        )

    def test_select_dryer_face_to_face_resets_payment_record_to_pending(self):
        self.payment.status = 'completed'
        self.payment.stripe_session_id = 'cs_old_dryer'
        self.payment.stripe_payment_intent_id = 'pi_old_dryer'
        self.payment.paid_at = timezone.now()
        self.payment.save(update_fields=['status', 'stripe_session_id', 'stripe_payment_intent_id', 'paid_at'])

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:dryer_rental_payment_method', args=[self.dryer_rental.pk]),
            {'payment_method': 'face_to_face'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )

        self.dryer_rental.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.dryer_rental.payment_method, 'face_to_face')
        self.assertEqual(self.payment.status, 'pending')
        self.assertIsNone(self.payment.stripe_session_id)
        self.assertIsNone(self.payment.stripe_payment_intent_id)
        self.assertIsNone(self.payment.paid_at)

    def test_hourly_dryer_detail_page_shows_payment_actions_for_member(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Proceed to Gcash Payment')
        self.assertContains(response, 'Choose Over the Counter')
        self.assertNotContains(response, 'Cancel Request')

    def test_admin_confirm_face_to_face_dryer_payment_marks_confirmed(self):
        admin = User.objects.create_user(
            username='dryeradmin',
            email='dryeradmin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.dryer_rental.payment_method = 'face_to_face'
        self.dryer_rental.save(update_fields=['payment_method'])
        self.payment.status = 'pending'
        self.payment.stripe_session_id = None
        self.payment.stripe_payment_intent_id = None
        self.payment.paid_at = None
        self.payment.save(update_fields=['status', 'stripe_session_id', 'stripe_payment_intent_id', 'paid_at'])

        self.client.force_login(admin)
        response = self.client.post(
            reverse('machines:dryer_rental_confirm_payment', args=[self.dryer_rental.pk]),
            {'amount_received': '800.00'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )

        self.dryer_rental.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.dryer_rental.status, 'confirmed')
        self.assertEqual(self.dryer_rental.payment_method, 'face_to_face')
        self.assertEqual(self.payment.status, 'completed')
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.payment.amount, self.dryer_rental.total_amount)
        self.assertEqual(self.payment.amount_received, Decimal('800.00'))
        self.assertEqual(self.payment.change_given, Decimal('500.00'))
        self.assertEqual(self.payment.processed_by, admin)

    @patch('bufia.views.payment_views.notify_staff')
    @patch('bufia.views.payment_views.create_user_notification')
    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.retrieve')
    def test_payment_success_marks_dryer_rental_paid(
        self,
        mock_retrieve,
        mock_configured,
        mock_create_user_notification,
        mock_notify_staff,
    ):
        mock_retrieve.return_value = {
            'status': 'complete',
            'payment_status': 'paid',
            'amount_total': 30000,
            'payment_intent': 'pi_test_dryer_123',
        }

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('payment_success'),
            {
                'session_id': 'cs_test_dryer_123',
                'type': 'dryer',
                'id': self.dryer_rental.id,
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )

        self.dryer_rental.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.dryer_rental.status, 'paid')
        self.assertEqual(self.dryer_rental.payment_method, 'online')
        self.assertEqual(self.payment.status, 'completed')
        self.assertEqual(self.payment.stripe_payment_intent_id, 'pi_test_dryer_123')
        self.assertIsNotNone(self.payment.paid_at)
        mock_create_user_notification.assert_called_once()
        mock_notify_staff.assert_called_once()

    def test_admin_approval_forces_dryer_payment_method_to_face_to_face(self):
        self.dryer_rental.status = 'pending'
        self.dryer_rental.payment_method = 'online'
        self.dryer_rental.save(update_fields=['status', 'payment_method', 'updated_at'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:dryer_rental_approve', args=[self.dryer_rental.pk]),
            {'admin_note': 'Proceed with office payment.'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )

        self.dryer_rental.refresh_from_db()
        self.assertEqual(self.dryer_rental.payment_method, 'face_to_face')

    @patch('bufia.views.payment_views.notify_staff')
    @patch('bufia.views.payment_views.create_user_notification')
    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.retrieve')
    def test_payment_success_does_not_mark_face_to_face_dryer_paid(
        self,
        mock_retrieve,
        mock_configured,
        mock_create_user_notification,
        mock_notify_staff,
    ):
        self.dryer_rental.payment_method = 'face_to_face'
        self.dryer_rental.save(update_fields=['payment_method'])
        mock_retrieve.return_value = {
            'status': 'complete',
            'payment_status': 'paid',
            'amount_total': 30000,
            'payment_intent': 'pi_test_dryer_123',
        }

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('payment_success'),
            {
                'session_id': 'cs_test_dryer_123',
                'type': 'dryer',
                'id': self.dryer_rental.id,
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )

        self.dryer_rental.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.dryer_rental.status, 'paid')
        self.assertEqual(self.dryer_rental.payment_method, 'face_to_face')
        self.assertEqual(self.payment.status, 'pending')
        mock_create_user_notification.assert_not_called()
        mock_notify_staff.assert_not_called()


class DryerUntilDriedCompletionFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dryuser',
            email='dryuser@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='dryadmin',
            email='dryadmin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Circulating Dryer 1',
            machine_type='flatbed_dryer',
            dryer_service_type='circulating',
            dryer_pricing_type='until_dried',
            dryer_hourly_rate=Decimal('150.00'),
            description='Completion flow test dryer',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        self.dryer_rental = DryerRental.objects.create(
            machine=self.machine,
            user=self.user,
            rental_date=date.today() + timedelta(days=2),
            status='approved',
            notes='Until dried service',
        )

    def test_admin_can_record_until_dried_request_payment_with_actual_hours(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_complete', args=[self.dryer_rental.pk]),
            {'actual_drying_hours': '4.50'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )
        self.dryer_rental.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(DryerRental),
            object_id=self.dryer_rental.id,
        )

        self.assertEqual(self.dryer_rental.status, 'paid')
        self.assertEqual(self.dryer_rental.actual_drying_hours, Decimal('4.50'))
        self.assertEqual(self.dryer_rental.hourly_rate_snapshot, Decimal('150.00'))
        self.assertEqual(self.dryer_rental.total_amount, Decimal('675.00'))
        self.assertEqual(payment.status, 'pending')

    def test_admin_can_mark_dryer_completed_after_payment_confirmation(self):
        Payment.objects.create(
            user=self.user,
            payment_type='dryer',
            amount=Decimal('675.00'),
            currency='PHP',
            status='completed',
            paid_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(DryerRental),
            object_id=self.dryer_rental.id,
        )
        self.dryer_rental.status = 'confirmed'
        self.dryer_rental.actual_drying_hours = Decimal('4.50')
        self.dryer_rental.hourly_rate_snapshot = Decimal('150.00')
        self.dryer_rental.total_amount = Decimal('675.00')
        self.dryer_rental.save(update_fields=['status', 'actual_drying_hours', 'hourly_rate_snapshot', 'total_amount'])

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_complete', args=[self.dryer_rental.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[self.dryer_rental.pk]),
            fetch_redirect_response=False,
        )
        self.dryer_rental.refresh_from_db()
        self.assertEqual(self.dryer_rental.status, 'completed')
        self.assertEqual(self.dryer_rental.actual_drying_hours, Decimal('4.50'))
        self.assertEqual(self.dryer_rental.total_amount, Decimal('675.00'))

    def test_admin_can_compute_solar_dryer_payment_from_confirmed_sacks(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer 1',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='per_sack',
            dryer_hourly_rate=Decimal('35.00'),
            description='Solar dryer payment flow test',
            status='available',
            rental_fee_per_day=0,
            current_price='35/sack',
        )
        solar_rental = DryerRental.objects.create(
            machine=solar_machine,
            user=self.user,
            rental_date=date.today() + timedelta(days=3),
            quantity='20 sacks',
            goods_description='Palay for solar drying',
            status='in_progress',
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:dryer_rental_complete', args=[solar_rental.pk]),
            {'confirmed_quantity_sacks': '18.50'},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[solar_rental.pk]),
            fetch_redirect_response=False,
        )
        solar_rental.refresh_from_db()
        self.assertEqual(solar_rental.status, 'paid')
        self.assertEqual(solar_rental.confirmed_quantity_sacks, Decimal('18.50'))
        self.assertEqual(solar_rental.total_amount, Decimal('647.50'))

    def test_solar_dryer_detail_page_shows_confirmed_sacks_billing_flow(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer Detail Flow',
            machine_type='solar_dryer',
            dryer_service_type='solar',
            dryer_pricing_type='per_sack',
            dryer_hourly_rate=Decimal('35.00'),
            description='Solar dryer detail flow test',
            status='available',
            rental_fee_per_day=0,
            current_price='35/sack',
        )
        solar_rental = DryerRental.objects.create(
            machine=solar_machine,
            user=self.user,
            rental_date=date.today() + timedelta(days=3),
            quantity='20 sacks',
            goods_description='Palay for solar drying',
            status='in_progress',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:dryer_rental_detail', args=[solar_rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmed Final Sacks')
        self.assertContains(response, 'Save Confirmed Sacks and Total')
        self.assertNotContains(response, 'Final Amount')


class RentalPaymentProgressFlowTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='rentaladmin',
            email='rentaladmin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.user = User.objects.create_user(
            username='rentalmember',
            email='rentalmember@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Progress Tractor',
            machine_type='tractor',
            description='Rental progress workflow test machine',
            status='available',
            rental_fee_per_day=1200,
            current_price='1200/day',
        )

    def test_admin_approval_forces_rental_payment_method_to_face_to_face(self):
        rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_type='cash',
            payment_method='online',
            payment_amount=Decimal('2400.00'),
            payment_status='pending',
            status='pending',
            workflow_state='pending_approval',
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            {'status': 'approved'},
        )

        self.assertEqual(response.status_code, 302)

        rental.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=rental.id,
        )

        self.assertEqual(rental.status, 'approved')
        self.assertEqual(rental.payment_method, 'face_to_face')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, rental.payment_amount)

    def test_online_payment_verification_moves_rental_to_in_progress(self):
        rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_method='online',
            payment_amount=Decimal('2400.00'),
            payment_date=timezone.now(),
            payment_status='pending',
            status='approved',
            workflow_state='approved',
        )
        self.client.force_login(self.admin)

        response = self.client.post(reverse('machines:verify_online_payment', args=[rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            fetch_redirect_response=False,
        )
        rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertTrue(rental.payment_verified)
        self.assertEqual(rental.status, 'approved')
        self.assertEqual(rental.workflow_state, 'in_progress')
        self.assertIsNone(rental.actual_completion_time)
        self.assertEqual(self.machine.status, 'available')

    def test_face_to_face_payment_recording_moves_rental_to_in_progress(self):
        rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_method='face_to_face',
            payment_amount=Decimal('2400.00'),
            payment_status='pending',
            status='approved',
            workflow_state='approved',
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:record_face_to_face_payment', args=[rental.pk]),
            {'payment_amount': '2400.00'},
        )

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            fetch_redirect_response=False,
        )
        rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertTrue(rental.payment_verified)
        self.assertEqual(rental.status, 'approved')
        self.assertEqual(rental.workflow_state, 'in_progress')
        self.assertIsNotNone(rental.payment_date)
        self.assertIsNone(rental.actual_completion_time)
        self.assertEqual(self.machine.status, 'available')

    def test_admin_complete_action_finishes_paid_in_progress_rental(self):
        rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_method='face_to_face',
            payment_amount=Decimal('2400.00'),
            payment_date=timezone.now(),
            payment_status='paid',
            payment_verified=True,
            status='approved',
            workflow_state='in_progress',
            verification_date=timezone.now(),
            verified_by=self.admin,
        )
        self.machine.status = 'rented'
        self.machine.save(update_fields=['status'])
        self.client.force_login(self.admin)

        response = self.client.post(reverse('machines:admin_complete_rental_early', args=[rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[rental.pk]),
            fetch_redirect_response=False,
        )
        rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(rental.status, 'completed')
        self.assertEqual(rental.workflow_state, 'completed')
        self.assertIsNotNone(rental.actual_completion_time)
        self.assertEqual(self.machine.status, 'available')


class OperatorAssignmentFlowTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='operatorsuper',
            email='operatorsuper@example.com',
            password='testpassword123',
        )
        self.staff_admin = User.objects.create_user(
            username='operatorstaff',
            email='operatorstaff@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='operatormember',
            email='operatormember@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.operator = User.objects.create_user(
            username='fieldoperator',
            email='fieldoperator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Operator Tractor',
            machine_type='tractor_4wd',
            description='Operator assignment test machine',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000/hectare',
        )
        self.rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_method='face_to_face',
            payment_amount=Decimal('4000.00'),
            payment_status='paid',
            payment_verified=True,
            status='approved',
            workflow_state='approved',
        )

    def test_assign_operator_keeps_rental_status_approved(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:assign_operator', args=[self.rental.pk]),
            {'assigned_operator': str(self.operator.pk), 'operator_notes': ''},
        )

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.status, 'approved')
        self.assertEqual(self.rental.operator_status, 'assigned')
        self.assertEqual(self.rental.assigned_operator, self.operator)

    def test_staff_admin_can_assign_operator(self):
        self.client.force_login(self.staff_admin)

        response = self.client.post(
            reverse('machines:assign_operator', args=[self.rental.pk]),
            {'assigned_operator': str(self.operator.pk), 'operator_notes': ''},
        )

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.assigned_operator, self.operator)
        self.assertEqual(self.rental.operator_status, 'assigned')

    def test_assign_operator_allows_conflict_review_rental(self):
        overdue_rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=self.rental.start_date - timedelta(days=2),
            end_date=self.rental.start_date - timedelta(days=1),
            payment_method='face_to_face',
            payment_amount=Decimal('4000.00'),
            payment_status='paid',
            payment_verified=True,
            status='approved',
            workflow_state='approved',
        )
        Rental.objects.filter(pk=self.rental.pk).update(
            start_date=overdue_rental.end_date,
            end_date=overdue_rental.end_date + timedelta(days=1),
        )
        Rental.sync_overdue_workflow_states(today=self.rental.start_date)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'conflict_review')

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:assign_operator', args=[self.rental.pk]),
            {'assigned_operator': str(self.operator.pk), 'operator_notes': 'Conflict rental assignment'},
        )

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.assigned_operator, self.operator)
        self.assertEqual(self.rental.operator_status, 'assigned')
        self.assertEqual(self.rental.workflow_state, 'conflict_review')
        self.assertEqual(self.rental.operator_notes, 'Conflict rental assignment')

    def test_operator_accept_job_moves_rental_to_in_progress(self):
        self.rental.assigned_operator = self.operator
        self.rental.operator_status = 'assigned'
        self.rental.save(update_fields=['assigned_operator', 'operator_status', 'updated_at'])

        self.client.force_login(self.operator)

        response = self.client.post(reverse('machines:operator_accept_job', args=[self.rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:operator_job_detail', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(self.rental.status, 'approved')
        self.assertEqual(self.rental.workflow_state, 'in_progress')
        self.assertEqual(self.rental.operator_status, 'operating')
        self.assertIsNotNone(self.rental.actual_handover_date)
        self.assertEqual(self.machine.status, 'rented')

    def test_operator_detail_disables_accept_button_after_task_is_accepted(self):
        self.rental.assigned_operator = self.operator
        self.rental.workflow_state = 'in_progress'
        self.rental.operator_status = 'operating'
        self.rental.actual_handover_date = timezone.now()
        self.rental.save(update_fields=[
            'assigned_operator',
            'workflow_state',
            'operator_status',
            'actual_handover_date',
            'updated_at',
        ])

        self.client.force_login(self.operator)
        response = self.client.get(reverse('machines:operator_job_detail', args=[self.rental.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Accept Task')
        self.assertContains(response, 'Task Accepted')
        self.assertContains(response, 'disabled')

    def test_operator_completion_waits_for_admin_validation_on_cash_rental(self):
        self.rental.assigned_operator = self.operator
        self.rental.workflow_state = 'in_progress'
        self.rental.operator_status = 'operating'
        self.rental.actual_handover_date = timezone.now()
        self.rental.save(update_fields=[
            'assigned_operator',
            'workflow_state',
            'operator_status',
            'actual_handover_date',
            'updated_at',
        ])

        self.client.force_login(self.operator)
        response = self.client.post(reverse('machines:operator_complete_job', args=[self.rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:operator_simple_dashboard'),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(self.rental.status, 'approved')
        self.assertEqual(self.rental.workflow_state, 'in_progress')
        self.assertEqual(self.rental.operator_status, 'completed')
        self.assertIsNotNone(self.rental.actual_completion_time)
        self.assertEqual(self.machine.status, 'rented')

        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse('machines:admin_approve_rental', args=[self.rental.pk]))

        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, 'Waiting For Admin Validation')
        self.assertContains(admin_response, 'Mark Rental Completed')


class OperatorHarvestDieselFlowTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='harvestdieseladmin',
            email='harvestdieseladmin@example.com',
            password='testpassword123',
        )
        self.member = User.objects.create_user(
            username='harvestdieselmember',
            email='harvestdieselmember@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.operator = User.objects.create_user(
            username='harvestdieseloperator',
            email='harvestdieseloperator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Harvest Diesel Combine',
            machine_type='combine_harvester',
            description='Machine used for harvest diesel reporting tests.',
            status='rented',
            rental_fee_per_day=Decimal('5000.00'),
            current_price='Rice share basis',
            rental_price_type='in_kind',
            in_kind_farmer_share=9,
            in_kind_organization_share=1,
        )
        self.rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            assigned_operator=self.operator,
            start_date=date.today(),
            end_date=date.today(),
            payment_type='in_kind',
            payment_method='face_to_face',
            status='approved',
            workflow_state='in_progress',
            operator_status='operating',
            actual_handover_date=timezone.now(),
            purpose='Harvest diesel reporting test',
        )

    def test_operator_harvest_report_saves_diesel_fields(self):
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse('machines:operator_report_harvest', args=[self.rental.pk]),
            {
                'total_harvest': '99',
                'diesel_consumed': '18.50',
                'diesel_cost': '1500.00',
                'notes': '',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:operator_job_detail', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.machine.refresh_from_db()
        self.assertEqual(self.rental.total_harvest_sacks, Decimal('99'))
        self.assertEqual(self.rental.diesel_consumed, Decimal('18.50'))
        self.assertEqual(self.rental.diesel_cost, Decimal('1500.00'))
        self.assertEqual(self.rental.workflow_state, 'harvest_report_submitted')
        self.assertEqual(self.rental.operator_status, 'harvest_reported')
        self.assertEqual(self.machine.status, 'available')

    def test_diesel_report_includes_harvest_reported_in_kind_job(self):
        self.rental.total_harvest_sacks = Decimal('99')
        self.rental.total_rice_sacks_harvested = Decimal('99')
        self.rental.bufia_share = Decimal('11')
        self.rental.organization_share_required = Decimal('11')
        self.rental.member_share = Decimal('88')
        self.rental.diesel_consumed = Decimal('18.50')
        self.rental.diesel_cost = Decimal('1500.00')
        self.rental.status = 'completed'
        self.rental.workflow_state = 'harvest_report_submitted'
        self.rental.operator_status = 'harvest_reported'
        self.rental.settlement_status = 'waiting_for_delivery'
        self.rental.actual_completion_time = timezone.now()
        self.rental.save(update_fields=[
            'total_harvest_sacks',
            'total_rice_sacks_harvested',
            'bufia_share',
            'organization_share_required',
            'member_share',
            'diesel_consumed',
            'diesel_cost',
            'status',
            'workflow_state',
            'operator_status',
            'settlement_status',
            'actual_completion_time',
            'updated_at',
        ])

        self.client.force_login(self.operator)
        response = self.client.get(reverse('machines:diesel_consumption_report'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 1)
        self.assertEqual(response.context['total_diesel_cost'], Decimal('1500.00'))
        self.assertIn(self.rental.id, [record.id for record in response.context['recent_records']])

    def test_confirm_rice_received_marks_operator_completed(self):
        self.rental.total_harvest_sacks = Decimal('99')
        self.rental.total_rice_sacks_harvested = Decimal('99')
        self.rental.bufia_share = Decimal('11')
        self.rental.organization_share_required = Decimal('11')
        self.rental.member_share = Decimal('88')
        self.rental.status = 'completed'
        self.rental.workflow_state = 'harvest_report_submitted'
        self.rental.operator_status = 'harvest_reported'
        self.rental.payment_status = 'pending'
        self.rental.settlement_status = 'waiting_for_delivery'
        self.rental.actual_completion_time = timezone.now()
        self.rental.save(update_fields=[
            'total_harvest_sacks',
            'total_rice_sacks_harvested',
            'bufia_share',
            'organization_share_required',
            'member_share',
            'status',
            'workflow_state',
            'operator_status',
            'payment_status',
            'settlement_status',
            'actual_completion_time',
            'updated_at',
        ])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:confirm_rice_received', args=[self.rental.pk]),
            {'organization_share_received': '11'},
        )

        self.assertRedirects(
            response,
            reverse('machines:admin_approve_rental', args=[self.rental.pk]),
            fetch_redirect_response=False,
        )
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.operator_status, 'completed')
        self.assertEqual(self.rental.workflow_state, 'completed')
        self.assertEqual(self.rental.settlement_status, 'paid')

    def test_admin_cannot_open_operator_diesel_report(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:diesel_consumption_report'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())


class AdminApproveRentalMissingRecordTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='missingrentaladmin',
            email='missingrentaladmin@example.com',
            password='testpassword123',
        )

    def test_missing_rental_redirects_admin_to_dashboard_with_message(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:admin_approve_rental', args=[34]),
            follow=True,
        )

        self.assertRedirects(response, reverse('machines:admin_rental_dashboard'))
        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn(
            'Rental #34 could not be found. It may have already been removed.',
            messages,
        )


class OperatorManagementEditTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='operatoradmin',
            email='operatoradmin@example.com',
            password='testpassword123',
        )
        self.operator = User.objects.create_user(
            username='operatoruser',
            email='operatoruser@example.com',
            password='oldpassword123',
            first_name='Old',
            last_name='Operator',
            role=User.OPERATOR,
            is_staff=True,
            is_active=True,
        )

    def test_admin_can_change_operator_password_from_edit_page(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:operator_edit', args=[self.operator.pk]),
            {
                'first_name': 'New',
                'last_name': 'Operator',
                'email': 'operatoruser@example.com',
                'is_active': 'on',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:operator_overview'),
            fetch_redirect_response=False,
        )
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.first_name, 'New')
        self.assertFalse(self.operator.check_password('oldpassword123'))
        self.assertTrue(self.operator.check_password('newpassword123'))

        self.client.logout()
        self.assertFalse(self.client.login(username='operatoruser', password='oldpassword123'))
        self.assertTrue(self.client.login(username='operatoruser', password='newpassword123'))


class OperatorManagementAddTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='operatoraddadmin',
            email='operatoraddadmin@example.com',
            password='testpassword123',
        )

    def test_admin_created_operator_uses_operator_role_without_staff_access(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:operator_add'),
            {
                'username': 'newoperator',
                'password': 'newpassword123',
                'first_name': 'New',
                'last_name': 'Operator',
                'email': 'newoperator@example.com',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:operator_overview'),
            fetch_redirect_response=False,
        )

        operator = User.objects.get(username='newoperator')
        self.assertEqual(operator.role, User.OPERATOR)
        self.assertFalse(operator.is_staff)
        self.assertTrue(operator.is_active)


class OperatorManagementDeleteTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='operatordeleteadmin',
            email='operatordeleteadmin@example.com',
            password='testpassword123',
        )
        self.operator = User.objects.create_user(
            username='deleteoperator',
            email='deleteoperator@example.com',
            password='testpassword123',
            first_name='Delete',
            last_name='Operator',
            role=User.OPERATOR,
            is_staff=True,
            is_active=True,
        )
        self.client.force_login(self.admin)

    def test_operator_delete_requires_typed_confirm(self):
        response = self.client.post(
            reverse('machines:operator_delete', args=[self.operator.pk]),
            {'delete_confirmation': ''},
        )

        self.assertContains(response, 'Type CONFIRM before deactivating this operator.', status_code=400)
        self.operator.refresh_from_db()
        self.assertTrue(self.operator.is_active)
        self.assertTrue(self.operator.is_staff)

    def test_operator_delete_deactivates_with_typed_confirm(self):
        response = self.client.post(
            reverse('machines:operator_delete', args=[self.operator.pk]),
            {'delete_confirmation': 'CONFIRM'},
        )

        self.assertRedirects(response, reverse('machines:operator_overview'), fetch_redirect_response=False)
        self.operator.refresh_from_db()
        self.assertFalse(self.operator.is_active)
        self.assertFalse(self.operator.is_staff)

    def test_operator_overview_exposes_confirm_metadata_on_delete_link(self):
        response = self.client.get(reverse('machines:operator_overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-delete-title="Deactivate Operator"', html=False)
        self.assertContains(response, 'data-delete-confirmation-word="CONFIRM"', html=False)


class RiceMillFaceToFaceFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ricemilluser',
            email='ricemill@example.com',
            password='testpassword123',
            first_name='Rice',
            last_name='Farmer',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='ricemilladmin',
            email='ricemilladmin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Rice Mill 1',
            machine_type='rice_mill',
            description='Rice mill for payment flow testing',
            status='available',
            rental_fee_per_day=150,
            current_price='3/kg',
        )
        self.appointment = RiceMillAppointment.objects.create(
            machine=self.machine,
            user=self.user,
            appointment_date=date.today() + timedelta(days=2),
            start_time=time(8, 0),
            end_time=time(10, 0),
            rice_quantity=Decimal('500.00'),
            status='pending',
        )

    def test_approve_appointment_sets_face_to_face_payment(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_approve', args=[self.appointment.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.assertEqual(self.appointment.status, 'approved')
        self.assertEqual(self.appointment.payment_method, 'face_to_face')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, self.appointment.total_amount)

    def test_approve_appointment_preserves_online_payment_choice(self):
        self.appointment.payment_method = 'online'
        self.appointment.save(update_fields=['payment_method', 'updated_at'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_approve', args=[self.appointment.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()

        self.assertEqual(self.appointment.status, 'approved')
        self.assertEqual(self.appointment.payment_method, 'online')
        self.assertFalse(
            Payment.objects.filter(
                content_type=ContentType.objects.get_for_model(RiceMillAppointment),
                object_id=self.appointment.id,
            ).exists()
        )

    def test_approve_date_only_appointment_sets_face_to_face_payment(self):
        self.appointment.start_time = None
        self.appointment.end_time = None
        self.appointment.time_slot = f"FLEX-{self.appointment.reference_number}"
        self.appointment.save(update_fields=['start_time', 'end_time', 'time_slot', 'updated_at'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_approve', args=[self.appointment.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.assertEqual(self.appointment.status, 'approved')
        self.assertEqual(self.appointment.payment_method, 'face_to_face')
        self.assertEqual(payment.status, 'pending')

    def test_confirm_ricemill_face_to_face_payment_marks_confirmed(self):
        self.appointment.status = 'paid'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.final_weight = Decimal('500.00')
        self.appointment.save(update_fields=['status', 'payment_method', 'final_weight', 'updated_at'])
        payment = Payment.objects.create(
            user=self.user,
            payment_type='appointment',
            amount=self.appointment.total_amount,
            currency='PHP',
            status='pending',
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_confirm_payment', args=[self.appointment.pk]),
            {'amount_received': '1600.00'},
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(self.appointment.status, 'confirmed')
        self.assertEqual(self.appointment.payment_method, 'face_to_face')
        self.assertEqual(payment.status, 'completed')
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(payment.amount, self.appointment.total_amount)
        self.assertEqual(payment.amount_received, Decimal('1600.00'))
        self.assertEqual(payment.change_given, Decimal('100.00'))
        self.assertEqual(payment.processed_by, self.admin)

    def test_confirm_ricemill_face_to_face_payment_rejects_underpayment(self):
        self.appointment.status = 'paid'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.final_weight = Decimal('500.00')
        self.appointment.save(update_fields=['status', 'payment_method', 'final_weight', 'updated_at'])
        payment = Payment.objects.create(
            user=self.user,
            payment_type='appointment',
            amount=self.appointment.total_amount,
            currency='PHP',
            status='pending',
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_confirm_payment', args=[self.appointment.pk]),
            {'amount_received': '1400.00'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.appointment.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(self.appointment.status, 'paid')
        self.assertEqual(payment.status, 'pending')
        self.assertIsNone(payment.amount_received)
        self.assertEqual(payment.change_given, Decimal('0.00'))

    def test_record_final_weight_with_tahop_sale_updates_overall_total(self):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_record_weight', args=[self.appointment.pk]),
            {
                'final_weight': '480.00',
                'sell_tahop': 'on',
                'tahop_weight': '25.00',
                'tahop_price_per_kg': '12.00',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.appointment.refresh_from_db()
        self.assertTrue(self.appointment.sell_tahop)
        self.assertEqual(self.appointment.tahop_weight, Decimal('25.00'))
        self.assertEqual(self.appointment.tahop_price_per_kg, Decimal('12.00'))
        self.assertEqual(self.appointment.tahop_total_amount, Decimal('300.00'))
        self.assertEqual(self.appointment.total_amount, Decimal('1740.00'))

    def test_record_final_weight_keeps_online_appointment_ready_to_pay(self):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'online'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_record_weight', args=[self.appointment.pk]),
            {'final_weight': '480.00'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.appointment.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.assertEqual(self.appointment.status, 'approved')
        self.assertEqual(payment.status, 'pending')

        self.client.force_login(self.user)
        list_response = self.client.get(reverse('machines:ricemill_appointment_list'))

        self.assertContains(list_response, 'Ready to Pay')
        self.assertContains(list_response, reverse('create_appointment_payment', args=[self.appointment.pk]))
        self.assertNotContains(list_response, 'ricemill-badge--paid">Paid', html=False)

    def test_create_appointment_payment_redirects_back_to_detail(self):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('create_appointment_payment', args=[self.appointment.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

    def test_select_ricemill_payment_method_keeps_over_the_counter_only(self):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])
        Payment.objects.create(
            user=self.user,
            payment_type='appointment',
            amount=self.appointment.total_amount,
            currency='PHP',
            status='pending',
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:ricemill_appointment_payment_method', args=[self.appointment.pk]),
            {'payment_method': 'face_to_face'},
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.payment_method, 'face_to_face')

    def test_create_appointment_payment_waits_for_final_weight_when_online(self):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'online'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('create_appointment_payment', args=[self.appointment.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Gcash payment will be available after BUFIA staff records the final milled weight.',
        )

    @patch('bufia.views.payment_views._redirect_to_paymongo_checkout', return_value=HttpResponseRedirect('/mock-checkout/'))
    @patch('bufia.views.payment_views._paymongo_is_configured', return_value=True)
    def test_create_appointment_payment_allows_online_checkout_after_final_weight(
        self,
        _mock_is_configured,
        mock_redirect_to_checkout,
    ):
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'online'
        self.appointment.final_weight = Decimal('480.00')
        self.appointment.total_amount = Decimal('1440.00')
        self.appointment.save(update_fields=['status', 'payment_method', 'final_weight', 'total_amount', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.get(reverse('create_appointment_payment', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/mock-checkout/')
        mock_redirect_to_checkout.assert_called_once()

    def test_ricemill_create_view_auto_creates_default_rice_mill(self):
        RiceMillAppointment.objects.all().delete()
        Machine.objects.filter(machine_type='rice_mill').delete()

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule Rice Mill Appointment')
        self.assertTrue(Machine.objects.filter(machine_type='rice_mill', name='Rice Mill').exists())
        self.assertContains(response, 'Over the Counter')
        self.assertNotContains(response, 'Gcash Payment')

    def test_ricemill_admin_create_view_shows_non_member_source_option(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:ricemill_appointment_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Milling Source')
        self.assertContains(response, 'Non-member Milling')
        self.assertContains(response, 'BUFIA Rice Share')

    def test_ricemill_create_view_accepts_date_only_booking(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:ricemill_appointment_create'),
            {
                'machine': self.machine.pk,
                'appointment_date': self.appointment.appointment_date.isoformat(),
                'sacks': '5',
                'payment_method': 'face_to_face',
                'notes': '',
            },
        )

        created = RiceMillAppointment.objects.exclude(pk=self.appointment.pk).get(user=self.user)
        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[created.pk]),
            fetch_redirect_response=False,
        )
        self.assertIsNone(created.start_time)
        self.assertIsNone(created.end_time)
        self.assertEqual(created.display_time_range, 'Flexible daytime arrival')

    def test_ricemill_pricing_route_renders_separate_service_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:ricemill_pricing_update'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rice Mill Service')
        self.assertContains(response, 'Rice Mill Pricing')
        self.assertContains(response, 'Back to Rice Mill Service')
        self.assertNotContains(response, 'Back to Machines')

    def test_ricemill_list_change_pricing_button_uses_separate_service_url(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:ricemill_appointment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('machines:ricemill_pricing_update'))
        self.assertNotContains(response, reverse('machines:edit_machine', args=[self.machine.pk]))

    def test_ricemill_list_shows_current_milling_rate_to_users(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('machines:ricemill_appointment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current Milling Rate')
        self.assertContains(response, self.machine.get_rate_display())

    def test_ricemill_list_allows_admin_filtering_by_bufia_rice_share(self):
        RiceMillAppointment.objects.create(
            machine=self.machine,
            user=self.user,
            appointment_date=self.appointment.appointment_date,
            sacks=2,
            rice_quantity=Decimal('100.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE,
            customer_name='BUFIA Rice Share',
            customer_contact_number='09123456789',
            customer_address='BUFIA Storage',
            status='approved',
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('machines:ricemill_appointment_list'),
            {'booking_source': RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BUFIA Rice Share')
        self.assertNotContains(response, self.appointment.reference_number)

    def test_ricemill_admin_can_create_non_member_booking(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_appointment_create'),
            {
                'machine': self.machine.pk,
                'booking_source': RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER,
                'selected_member_id': '',
                'farmer_name': 'Walk-in Miller',
                'farmer_contact_number': '09171230000',
                'farm_location': 'Poblacion Rice Mill Drop-off',
                'appointment_date': (date.today() + timedelta(days=5)).isoformat(),
                'sacks': '6',
                'payment_method': 'face_to_face',
                'notes': 'Non-member rice mill booking',
            },
        )

        created = RiceMillAppointment.objects.exclude(pk=self.appointment.pk).get()
        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[created.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created.booking_source, RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER)
        self.assertEqual(created.customer_name, 'Walk-in Miller')
        self.assertEqual(created.customer_contact_number, '09171230000')
        self.assertEqual(created.customer_address, 'Poblacion Rice Mill Drop-off')
        self.assertEqual(created.payment_method, 'face_to_face')
        self.assertEqual(created.user.username, 'system')

    def test_ricemill_list_allows_admin_filtering_by_non_member_rice(self):
        non_member_appointment = RiceMillAppointment.objects.create(
            machine=self.machine,
            user=self.admin,
            appointment_date=self.appointment.appointment_date + timedelta(days=1),
            sacks=2,
            rice_quantity=Decimal('100.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER,
            customer_name='Walk-in Miller',
            customer_contact_number='09179990000',
            customer_address='Public Market',
            status='approved',
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('machines:ricemill_appointment_list'),
            {'booking_source': RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Non-member Milling')
        self.assertContains(response, non_member_appointment.reference_number)
        self.assertNotContains(response, self.appointment.reference_number)

    def test_ricemill_receipt_shows_estimated_and_final_weight_breakdown(self):
        self.appointment.final_weight = Decimal('480.00')
        self.appointment.total_amount = Decimal('1440.00')
        self.appointment.price_per_kg = Decimal('3.00')
        self.appointment.save(update_fields=['final_weight', 'total_amount', 'price_per_kg', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_receipt', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Final Weight: 480.00 kg')
        self.assertContains(response, 'PHP 3.00 per kg')
        self.assertContains(response, 'Final Amount: 480.00 kg x PHP 3.00')
        self.assertContains(response, 'PHP 1440.00')

    def test_ricemill_pricing_update_refreshes_existing_appointment_totals(self):
        self.machine.current_price = '5/kg'
        self.machine.rental_fee_per_day = Decimal('5.00')
        self.machine.save(update_fields=['current_price', 'rental_fee_per_day'])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:ricemill_pricing_update'),
            {
                'name': self.machine.name,
                'description': self.machine.description,
                'status': self.machine.status,
                'machine_type': 'rice_mill',
                'rental_price_type': 'cash',
                'current_price': '5.00',
                'pricing_unit': 'kg',
                'allow_online_payment': '',
                'allow_face_to_face_payment': 'on',
                'settlement_type': 'immediate',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.price_per_kg, Decimal('5.00'))
        self.assertEqual(self.appointment.total_amount, Decimal('2500.00'))

    def test_ricemill_receipt_uses_updated_machine_price_for_existing_appointment(self):
        self.machine.current_price = '5/kg'
        self.machine.rental_fee_per_day = Decimal('5.00')
        self.machine.save(update_fields=['current_price', 'rental_fee_per_day'])
        self.appointment.final_weight = Decimal('500.00')
        self.appointment.save(update_fields=['final_weight', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_receipt', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PHP 5.00 per kg')
        self.assertContains(response, 'Final Amount: 500.00 kg x PHP 5.00')
        self.assertContains(response, 'PHP 2500.00')

    def test_ricemill_receipt_shows_tahop_breakdown_when_selected(self):
        self.appointment.final_weight = Decimal('480.00')
        self.appointment.sell_tahop = True
        self.appointment.tahop_weight = Decimal('25.00')
        self.appointment.tahop_price_per_kg = Decimal('12.00')
        self.appointment.save(update_fields=[
            'final_weight',
            'sell_tahop',
            'tahop_weight',
            'tahop_price_per_kg',
            'updated_at',
        ])

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_receipt', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tahop: 25.00 kg x PHP 12.00')
        self.assertContains(response, 'Tahop Total: PHP 300.00')
        self.assertContains(response, 'OVERALL TOTAL:')
        self.assertContains(response, 'PHP 1740.00')

    def test_ricemill_receipt_shows_over_counter_cash_details(self):
        self.appointment.final_weight = Decimal('500.00')
        self.appointment.status = 'confirmed'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['final_weight', 'status', 'payment_method', 'updated_at'])
        payment = Payment.objects.create(
            user=self.user,
            payment_type='appointment',
            amount=self.appointment.total_amount,
            amount_received=Decimal('1600.00'),
            change_given=Decimal('100.00'),
            currency='PHP',
            status='completed',
            paid_at=timezone.now(),
            processed_by=self.admin,
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_receipt', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cash Received:')
        self.assertContains(response, 'PHP 1600.00')
        self.assertContains(response, 'Change Given:')
        self.assertContains(response, 'PHP 100.00')

    def test_ricemill_create_view_allows_multiple_date_only_bookings_on_same_day(self):
        other_user = User.objects.create_user(
            username='ricemillother',
            email='ricemillother@example.com',
            password='testpassword123',
            is_verified=True,
        )
        RiceMillAppointment.objects.create(
            machine=self.machine,
            user=other_user,
            appointment_date=self.appointment.appointment_date,
            rice_quantity=Decimal('100.00'),
            status='pending',
        )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:ricemill_appointment_create'),
            {
                'machine': self.machine.pk,
                'appointment_date': self.appointment.appointment_date.isoformat(),
                'sacks': '5',
                'payment_method': 'face_to_face',
                'notes': '',
            },
        )

        created = RiceMillAppointment.objects.exclude(pk__in=[self.appointment.pk]).filter(user=self.user).first()
        self.assertIsNotNone(created)
        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[created.pk]),
            fetch_redirect_response=False,
        )

    def test_ricemill_update_redirects_to_pending_page_after_submit(self):
        self.appointment.appointment_date = date.today() + timedelta(days=3)
        self.appointment.save(update_fields=['appointment_date', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:ricemill_appointment_update', args=[self.appointment.pk]),
            {
                'machine': self.machine.pk,
                'appointment_date': (date.today() + timedelta(days=4)).isoformat(),
                'sacks': '14',
                'payment_method': 'face_to_face',
                'notes': 'Updated booking request',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')

    def test_ricemill_update_keeps_member_payment_method_over_the_counter(self):
        self.appointment.appointment_date = date.today() + timedelta(days=3)
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['appointment_date', 'payment_method', 'updated_at'])

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('machines:ricemill_appointment_update', args=[self.appointment.pk]),
            {
                'machine': self.machine.pk,
                'appointment_date': (date.today() + timedelta(days=4)).isoformat(),
                'sacks': '15',
                'payment_method': 'face_to_face',
                'notes': 'Keep over-the-counter payment',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.payment_method, 'face_to_face')
        self.assertEqual(self.appointment.status, 'pending')

    def test_legacy_ricemill_pending_route_redirects_to_detail(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('machines:ricemill_appointment_pending', args=[self.appointment.pk])
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )


class RentalCalendarVisibilityTestCase(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            username='calendar_viewer',
            email='calendar_viewer@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.owner = User.objects.create_user(
            username='calendar_owner',
            email='calendar_owner@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Calendar Tractor',
            machine_type='hand_tractor',
            description='Machine for rental calendar visibility tests.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='4000',
        )
        self.start_date = date.today() + timedelta(days=5)
        self.end_date = self.start_date + timedelta(days=1)
        self.pending_rental = Rental.objects.create(
            machine=self.machine,
            user=self.owner,
            customer_name='Calendar Owner',
            start_date=self.start_date,
            end_date=self.end_date,
            area=Decimal('1.0'),
            purpose='Pending rental',
            status='pending',
        )
        self.approved_rental = Rental.objects.create(
            machine=self.machine,
            user=self.owner,
            customer_name='Calendar Owner',
            start_date=self.start_date + timedelta(days=3),
            end_date=self.end_date + timedelta(days=3),
            area=Decimal('1.0'),
            purpose='Approved rental',
            status='approved',
        )
        self.rejected_rental = Rental.objects.create(
            machine=self.machine,
            user=self.owner,
            customer_name='Calendar Owner',
            start_date=self.start_date + timedelta(days=6),
            end_date=self.end_date + timedelta(days=6),
            area=Decimal('1.0'),
            purpose='Rejected rental',
            status='rejected',
        )

    def test_shared_calendar_shows_pending_and_approved_but_hides_rejected(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:machine_calendar_events', args=[self.machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        events = response.json()
        titles = [event['title'] for event in events]
        statuses = [event['extendedProps'].get('status') for event in events]

        self.assertIn('Pending Request', titles)
        self.assertIn('Approved Booking', titles)
        self.assertNotIn('Rejected Request', titles)
        self.assertNotIn(self.owner.username, ''.join(titles))
        self.assertIn('pending', statuses)
        self.assertIn('approved', statuses)
        self.assertNotIn('rejected', statuses)

    def test_owner_can_see_their_rejected_request_on_calendar(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('machines:machine_calendar_events', args=[self.machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        events = response.json()
        titles = [event['title'] for event in events]

        self.assertIn('Rejected Request', titles)


class RentalPackageCloseFlowTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='package_admin',
            email='package_admin@example.com',
            password='testpassword123',
            is_staff=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            username='package_member',
            email='package_member@example.com',
            password='testpassword123',
            is_verified=True,
        )
        self.machine = Machine.objects.create(
            name='Package Tractor',
            machine_type='tractor_4wd',
            description='Machine reserved through rental package.',
            status='available',
            rental_fee_per_day=Decimal('4000.00'),
            current_price='4000/hectare',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        self.package = RentalPackage.objects.create(
            user=self.member,
            package_name='Whole Farming Service Package',
            farmer_name='Package Member',
            location='Test Farm',
            area=Decimal('3.0000'),
            preferred_start_date=date.today() + timedelta(days=7),
            preferred_timeline_notes='Urgent',
            status='partially_scheduled',
            total_amount=Decimal('4000.00'),
            payment_status='pending',
        )
        self.item = RentalPackageItem.objects.create(
            rental_package=self.package,
            machine=self.machine,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('4000.00'),
            quantity=Decimal('3.0000'),
            suggested_start=self.package.preferred_start_date,
            suggested_end=self.package.preferred_start_date,
            scheduled_start=self.package.preferred_start_date,
            scheduled_end=self.package.preferred_start_date + timedelta(days=1),
            is_tentative=False,
            status='scheduled',
            subtotal=Decimal('12000.00'),
            sequence_order=1,
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            customer_name='Package Member',
            customer_address='Test Farm',
            field_location='Test Farm',
            area=Decimal('3.0000'),
            start_date=self.item.scheduled_start,
            end_date=self.item.scheduled_end,
            purpose='Package reservation',
            status='approved',
            workflow_state='approved',
            operator_status='unassigned',
            payment_type='cash',
            settlement_type='immediate',
            payment_status='pending',
        )
        self.item.linked_rental = self.rental
        self.item.save(update_fields=['linked_rental', 'updated_at'])
        self.machine.sync_status()

    def test_reject_package_clears_reserved_machine_and_schedule(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {'action': 'reject_package'},
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.package.refresh_from_db()
        self.item.refresh_from_db()
        self.rental.refresh_from_db()
        self.machine.refresh_from_db()

        self.assertEqual(self.package.status, 'cancelled')
        self.assertEqual(self.item.status, 'cancelled')
        self.assertIsNone(self.item.machine)
        self.assertIsNone(self.item.scheduled_start)
        self.assertIsNone(self.item.scheduled_end)
        self.assertIsNone(self.item.linked_rental)
        self.assertEqual(self.rental.status, 'cancelled')
        self.assertEqual(self.rental.workflow_state, 'cancelled')
        self.assertEqual(self.machine.get_operational_status(), 'available')
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_package_rejected',
                related_object_id=self.package.pk,
            ).exists()
        )

    def test_cancelled_package_detail_is_read_only_for_admin(self):
        self.package.status = 'cancelled'
        self.package.save(update_fields=['status', 'updated_at'])

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_edit_package'])
        self.assertContains(response, 'Package Services')
        self.assertNotContains(response, 'Package Schedule Builder')
        self.assertNotContains(response, 'Save Draft')
        self.assertNotContains(response, 'Approve Package')

        post_response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {'action': 'save'},
        )
        self.assertEqual(post_response.status_code, 403)

    def test_editable_package_detail_hides_manual_approve_button(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Package Schedule Builder')
        self.assertNotContains(response, 'Approve Package')

    def test_admin_package_list_marks_package_notifications_as_read(self):
        notification = UserNotification.objects.create(
            user=self.admin,
            notification_type='rental_package_new_request',
            message='New rental package request received.',
            related_object_id=self.package.pk,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:rental_package_list'))

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_member_package_detail_marks_package_notifications_as_read(self):
        notification = UserNotification.objects.create(
            user=self.member,
            notification_type='rental_package_approved',
            message='Your rental package request was approved.',
            related_object_id=self.package.pk,
        )
        self.client.force_login(self.member)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_confirm_item_marks_line_as_scheduled_and_creates_reservation(self):
        pending_machine = Machine.objects.create(
            name='Package Rotavator',
            machine_type='hand_tractor',
            description='Pending package machine to confirm.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/flat',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        pending_item = RentalPackageItem.objects.create(
            rental_package=self.package,
            machine=pending_machine,
            service_code='rotavator',
            service_name='Rotavator / Land Cultivation',
            machine_type_required='tractor',
            pricing_unit='flat',
            rate=Decimal('1000.00'),
            quantity=Decimal('1.0000'),
            suggested_start=self.package.preferred_start_date + timedelta(days=1),
            suggested_end=self.package.preferred_start_date + timedelta(days=1),
            scheduled_start=self.package.preferred_start_date + timedelta(days=1),
            scheduled_end=self.package.preferred_start_date + timedelta(days=1),
            is_tentative=True,
            status='requested',
            subtotal=Decimal('1000.00'),
            sequence_order=2,
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {
                'items-TOTAL_FORMS': '2',
                'items-INITIAL_FORMS': '2',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-id': str(self.item.pk),
                'items-0-machine': str(self.item.machine_id),
                'items-0-quantity': '3.0000',
                'items-0-scheduled_start': self.item.scheduled_start.isoformat(),
                'items-0-scheduled_end': self.item.scheduled_end.isoformat(),
                'items-0-status': self.item.status,
                'items-0-notes': '',
                'items-1-id': str(pending_item.pk),
                'items-1-machine': str(pending_machine.pk),
                'items-1-quantity': '1.0000',
                'items-1-is_tentative': '',
                'items-1-scheduled_start': pending_item.scheduled_start.isoformat(),
                'items-1-scheduled_end': pending_item.scheduled_end.isoformat(),
                'items-1-status': 'requested',
                'items-1-notes': 'Ready to finalize',
                'action': f'confirm_item:{pending_item.pk}',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        pending_item.refresh_from_db()
        self.assertEqual(pending_item.status, 'scheduled')
        self.assertFalse(pending_item.is_tentative)
        self.assertIsNotNone(pending_item.linked_rental)
        self.assertEqual(pending_item.linked_rental.machine, pending_machine)

    def test_confirm_item_auto_approves_package_when_last_schedule_is_confirmed(self):
        pending_machine = Machine.objects.create(
            name='Package Planter',
            machine_type='transplanter_walking',
            description='Final package machine to confirm.',
            status='available',
            rental_fee_per_day=Decimal('1500.00'),
            current_price='1500/flat',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        pending_item = RentalPackageItem.objects.create(
            rental_package=self.package,
            machine=pending_machine,
            service_code='planter',
            service_name='Planter',
            machine_type_required='transplanter_walking',
            pricing_unit='flat',
            rate=Decimal('1500.00'),
            quantity=Decimal('1.0000'),
            suggested_start=self.package.preferred_start_date + timedelta(days=2),
            suggested_end=self.package.preferred_start_date + timedelta(days=2),
            scheduled_start=self.package.preferred_start_date + timedelta(days=2),
            scheduled_end=self.package.preferred_start_date + timedelta(days=2),
            is_tentative=True,
            status='requested',
            subtotal=Decimal('1500.00'),
            sequence_order=2,
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {
                'items-TOTAL_FORMS': '2',
                'items-INITIAL_FORMS': '2',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-id': str(self.item.pk),
                'items-0-machine': str(self.item.machine_id),
                'items-0-quantity': '3.0000',
                'items-0-scheduled_start': self.item.scheduled_start.isoformat(),
                'items-0-scheduled_end': self.item.scheduled_end.isoformat(),
                'items-0-status': self.item.status,
                'items-0-notes': '',
                'items-1-id': str(pending_item.pk),
                'items-1-machine': str(pending_machine.pk),
                'items-1-quantity': '1.0000',
                'items-1-is_tentative': '',
                'items-1-scheduled_start': pending_item.scheduled_start.isoformat(),
                'items-1-scheduled_end': pending_item.scheduled_end.isoformat(),
                'items-1-status': 'requested',
                'items-1-notes': 'Ready to finalize',
                'action': f'confirm_item:{pending_item.pk}',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.package.refresh_from_db()
        pending_item.refresh_from_db()

        self.assertEqual(self.package.status, 'approved')
        self.assertEqual(self.package.approved_by, self.admin)
        self.assertIsNotNone(self.package.approved_at)
        self.assertEqual(pending_item.status, 'scheduled')
        self.assertIsNotNone(pending_item.linked_rental)
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_package_approved',
                related_object_id=self.package.pk,
            ).exists()
        )

    def test_confirm_item_conflict_stays_on_page_with_validation_error(self):
        conflict_machine = Machine.objects.create(
            name='HAND TRACTOR',
            machine_type='hand_tractor',
            description='Conflicting machine for package validation test.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='1000/flat',
            rental_price_type='cash',
            allow_online_payment=True,
            allow_face_to_face_payment=True,
        )
        conflicting_member = User.objects.create_user(
            username='conflictmember',
            email='conflictmember@example.com',
            password='testpassword123',
            is_verified=True,
        )
        Rental.objects.create(
            machine=conflict_machine,
            user=conflicting_member,
            customer_name='Conflict Member',
            customer_address='Another Farm',
            field_location='Another Farm',
            area=Decimal('1.0000'),
            start_date=self.package.preferred_start_date + timedelta(days=1),
            end_date=self.package.preferred_start_date + timedelta(days=1),
            purpose='Existing booked rental',
            status='approved',
            workflow_state='approved',
            operator_status='unassigned',
            payment_type='cash',
            settlement_type='immediate',
            payment_status='pending',
        )

        pending_item = RentalPackageItem.objects.create(
            rental_package=self.package,
            machine=conflict_machine,
            service_code='rotavator',
            service_name='Rotavator / Land Cultivation',
            machine_type_required='tractor',
            pricing_unit='flat',
            rate=Decimal('1000.00'),
            quantity=Decimal('1.0000'),
            suggested_start=self.package.preferred_start_date + timedelta(days=1),
            suggested_end=self.package.preferred_start_date + timedelta(days=1),
            scheduled_start=self.package.preferred_start_date + timedelta(days=1),
            scheduled_end=self.package.preferred_start_date + timedelta(days=1),
            is_tentative=True,
            status='requested',
            subtotal=Decimal('1000.00'),
            sequence_order=2,
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {
                'items-TOTAL_FORMS': '2',
                'items-INITIAL_FORMS': '2',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-id': str(self.item.pk),
                'items-0-machine': str(self.item.machine_id),
                'items-0-quantity': '3.0000',
                'items-0-scheduled_start': self.item.scheduled_start.isoformat(),
                'items-0-scheduled_end': self.item.scheduled_end.isoformat(),
                'items-0-status': self.item.status,
                'items-0-notes': '',
                'items-1-id': str(pending_item.pk),
                'items-1-machine': str(conflict_machine.pk),
                'items-1-quantity': '1.0000',
                'items-1-scheduled_start': pending_item.scheduled_start.isoformat(),
                'items-1-scheduled_end': pending_item.scheduled_end.isoformat(),
                'items-1-status': 'requested',
                'items-1-notes': '',
                'action': f'confirm_item:{pending_item.pk}',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'HAND TRACTOR is already booked from {pending_item.scheduled_start} to {pending_item.scheduled_end}. Please choose different dates.',
        )

        pending_item.refresh_from_db()
        self.assertEqual(pending_item.status, 'requested')
        self.assertTrue(pending_item.is_tentative)
        self.assertIsNone(pending_item.linked_rental)

    def test_approve_promotes_schedule_ready_line_and_creates_linked_rental(self):
        self.rental.delete()
        self.item.refresh_from_db()
        self.package.status = 'pending'
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['status', 'payment_preference', 'updated_at'])
        self.item.linked_rental = None
        self.item.status = 'requested'
        self.item.is_tentative = False
        self.item.save(update_fields=['linked_rental', 'status', 'is_tentative', 'updated_at'])

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {
                'items-TOTAL_FORMS': '1',
                'items-INITIAL_FORMS': '1',
                'items-MIN_NUM_FORMS': '0',
                'items-MAX_NUM_FORMS': '1000',
                'items-0-id': str(self.item.pk),
                'items-0-machine': str(self.item.machine_id),
                'items-0-quantity': '3.0000',
                'items-0-is_tentative': '',
                'items-0-scheduled_start': self.item.scheduled_start.isoformat(),
                'items-0-scheduled_end': self.item.scheduled_end.isoformat(),
                'items-0-status': 'requested',
                'items-0-notes': 'Ready for approval',
                'action': 'approve',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.package.refresh_from_db()
        self.item.refresh_from_db()

        self.assertEqual(self.package.status, 'approved')
        self.assertEqual(self.package.payment_status, 'pending')
        self.assertEqual(self.item.status, 'scheduled')
        self.assertIsNotNone(self.item.linked_rental)
        self.assertEqual(self.item.linked_rental.status, 'approved')
        self.assertEqual(self.item.linked_rental.payment_method, 'online')
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_package_approved',
                related_object_id=self.package.pk,
            ).exists()
        )

    def test_member_cancel_package_creates_member_and_admin_notifications(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            {'action': 'cancel_package'},
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_package_cancelled',
                related_object_id=self.package.pk,
            ).exists()
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.admin,
                notification_type='rental_package_cancelled',
                related_object_id=self.package.pk,
            ).exists()
        )

    def test_member_package_detail_shows_linked_rental_payment_actions(self):
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.save(update_fields=['payment_method', 'payment_status', 'updated_at'])

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assign Operators')
        self.assertContains(response, 'BUFIA is preparing the operator assignment for this machine.')
        self.assertContains(response, reverse('machines:rental_confirmation', args=[self.rental.pk]))
        self.assertNotContains(response, reverse('create_rental_payment', args=[self.rental.pk]))

    def test_member_package_detail_shows_advance_payment_after_operator_assignment(self):
        operator = User.objects.create_user(
            username='package_day_operator',
            email='package_day_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'preferred_start_date', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ready for Payment')
        self.assertContains(response, reverse('create_rental_payment', args=[self.rental.pk]))

    def test_member_package_detail_shows_payment_method_selector_when_ready_rental_is_blank(self):
        operator = User.objects.create_user(
            username='package_blank_method_operator',
            email='package_blank_method_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = ''
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = ''
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose Payment Method')
        self.assertContains(
            response,
            reverse('machines:set_package_rental_payment_method', args=[self.rental.pk]),
        )
        self.assertNotContains(response, reverse('create_rental_payment', args=[self.rental.pk]))

    def test_member_package_detail_shows_single_flow_board_without_transaction_column(self):
        operator = User.objects.create_user(
            username='package_clean_flow_operator',
            email='package_clean_flow_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('machines:rental_package_detail', args=[self.package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current Package Status')
        self.assertContains(response, 'Package Rental Flow')
        self.assertContains(response, 'Cash Rental Flow')
        self.assertContains(response, 'In-Kind Rental Flow')
        self.assertContains(response, 'Package Services')
        self.assertNotContains(response, '<div class="package-service-table__head-item">Transaction</div>', html=False)
        self.assertNotContains(response, 'Choose the payment method from the Ready for Payment card above before continuing.')

    def test_member_can_set_package_rental_payment_method_from_package_page(self):
        operator = User.objects.create_user(
            username='package_method_operator',
            email='package_method_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = ''
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = ''
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.post(
            reverse('machines:set_package_rental_payment_method', args=[self.rental.pk]),
            {'payment_method': 'online'},
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.package.refresh_from_db()

        self.assertEqual(self.rental.payment_method, 'online')
        self.assertEqual(self.rental.workflow_state, 'ready_for_payment')
        self.assertEqual(self.package.payment_preference, 'online')

    def test_member_cannot_set_package_rental_payment_method_until_ready_for_payment(self):
        operator = User.objects.create_user(
            username='package_method_wait_operator',
            email='package_method_wait_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = ''
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = ''
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'approved'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.post(
            reverse('machines:set_package_rental_payment_method', args=[self.rental.pk]),
            {'payment_method': 'online'},
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.assertEqual(self.rental.payment_method, '')
        self.assertEqual(self.rental.workflow_state, 'approved')

    def test_package_pages_sync_stale_status_and_payment_preference_from_linked_rental_state(self):
        operator = User.objects.create_user(
            username='package_sync_operator',
            email='package_sync_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = 'online'
        self.package.status = 'partially_scheduled'
        self.package.save(update_fields=['payment_preference', 'status', 'updated_at'])
        self.rental.payment_method = ''
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'approved'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(reverse('machines:rental_package_list'))
        detail_response = self.client.get(reverse('machines:rental_package_detail', args=[self.package.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)

        self.package.refresh_from_db()
        self.rental.refresh_from_db()

        self.assertEqual(self.package.status, 'approved')
        self.assertEqual(self.rental.payment_method, 'online')
        self.assertEqual(self.rental.workflow_state, 'ready_for_payment')
        self.assertContains(detail_response, reverse('create_rental_payment', args=[self.rental.pk]))

    def test_create_rental_payment_redirects_package_rental_to_package_detail(self):
        self.package.payment_preference = 'face_to_face'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'face_to_face'
        self.rental.save(update_fields=['payment_method', 'updated_at'])

        self.client.force_login(self.member)

        response = self.client.get(reverse('create_rental_payment', args=[self.rental.pk]))

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

    def test_create_rental_payment_allows_package_rental_before_operation_day_after_operator_assignment(self):
        operator = User.objects.create_user(
            username='package_future_operator',
            email='package_future_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('create_rental_payment', args=[self.rental.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'This package rental becomes payable on')

    def test_create_rental_payment_blocks_package_rental_until_ready_for_payment(self):
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.workflow_state = 'approved'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('create_rental_payment', args=[self.rental.pk]),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
        )
        self.assertContains(response, 'This rental is not yet ready for payment.')

    def test_create_rental_payment_does_not_auto_promote_package_rental_into_ready_for_payment(self):
        operator = User.objects.create_user(
            username='package_payment_gate_operator',
            email='package_payment_gate_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.payment_preference = 'online'
        self.package.save(update_fields=['payment_preference', 'updated_at'])
        self.rental.payment_method = 'online'
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'approved'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.member)

        response = self.client.get(
            reverse('create_rental_payment', args=[self.rental.pk]),
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.assertEqual(self.rental.workflow_state, 'approved')

    def test_admin_cannot_record_package_cash_payment_until_ready_for_payment(self):
        operator = User.objects.create_user(
            username='package_cash_wait_operator',
            email='package_cash_wait_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.rental.payment_method = ''
        self.rental.payment_status = 'pending'
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'assigned'
        self.rental.workflow_state = 'approved'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'assigned_operator',
                'operator_status',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:record_face_to_face_payment', args=[self.rental.pk]),
            {
                'payment_amount': '12000.00',
                'next': reverse('machines:rental_package_detail', args=[self.package.pk]),
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.assertFalse(self.rental.payment_verified)
        self.assertEqual(self.rental.workflow_state, 'approved')

    def test_recording_package_cash_payment_syncs_payment_and_package_records(self):
        self.rental.payment_method = ''
        self.rental.payment_amount = Decimal('12000.00')
        self.rental.workflow_state = 'ready_for_payment'
        self.rental.save(
            update_fields=[
                'payment_method',
                'payment_amount',
                'workflow_state',
                'updated_at',
            ]
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:record_face_to_face_payment', args=[self.rental.pk]),
            {
                'payment_amount': '12000.00',
                'next': reverse('machines:rental_package_detail', args=[self.package.pk]),
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[self.package.pk]),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.package.refresh_from_db()
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.rental.pk,
        )

        self.assertTrue(self.rental.payment_verified)
        self.assertEqual(self.rental.payment_status, 'paid')
        self.assertEqual(self.rental.workflow_state, 'in_progress')
        self.assertEqual(self.package.payment_status, 'paid')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.payment_provider, 'manual')
        self.assertEqual(payment.amount_received, Decimal('12000.00'))
        self.assertEqual(payment.change_given, Decimal('0.00'))
        self.assertEqual(payment.processed_by, self.admin)
        self.assertEqual(payment.payment_channel_display, 'Over the Counter')

    def test_refresh_package_payment_status_uses_linked_rental_payment_record(self):
        payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('12000.00'),
            currency='PHP',
            status='completed',
            payment_provider='paymongo',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.rental.pk,
        )

        self.package.refresh_payment_status(save=True)
        self.package.refresh_from_db()

        self.assertEqual(payment.status, 'completed')
        self.assertEqual(self.package.payment_status, 'paid')

    def test_completing_linked_rental_auto_completes_package(self):
        operator = User.objects.create_user(
            username='package_complete_operator',
            email='package_complete_operator@example.com',
            password='testpassword123',
            role=User.OPERATOR,
        )
        self.package.status = 'approved'
        self.package.approved_by = self.admin
        self.package.approved_at = timezone.now()
        self.package.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        self.rental.assigned_operator = operator
        self.rental.operator_status = 'operating'
        self.rental.payment_verified = True
        self.rental.payment_status = 'paid'
        self.rental.workflow_state = 'in_progress'
        self.rental.status = 'approved'
        self.rental.save(
            update_fields=[
                'assigned_operator',
                'operator_status',
                'payment_verified',
                'payment_status',
                'workflow_state',
                'status',
                'updated_at',
            ]
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:admin_approve_rental', args=[self.rental.pk]),
            {'status': 'completed'},
        )

        self.assertRedirects(
            response,
            reverse('machines:rental_list'),
            fetch_redirect_response=False,
        )

        self.rental.refresh_from_db()
        self.item.refresh_from_db()
        self.package.refresh_from_db()

        self.assertEqual(self.rental.status, 'completed')
        self.assertEqual(self.rental.workflow_state, 'completed')
        self.assertEqual(self.item.status, 'completed')
        self.assertEqual(self.package.status, 'completed')
