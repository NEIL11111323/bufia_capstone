import json
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from .forms import MachineForm, RentalForm
from .models import DryerRental, Machine, MachineImage, Rental, RiceMillAppointment, Maintenance, MaintenancePartUsed
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
            machine_type='hand_tractor',
            description='Machine used to validate online payment limits.',
            status='available',
            rental_fee_per_day=Decimal('1000.00'),
            current_price='4000',
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


class MachineImageDisplayTestCase(TestCase):
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

    def test_dryer_form_rejects_overlapping_time_ranges(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The selected dryer time range conflicts with Joel Dela Cruz')
        self.assertContains(response, '9:00 AM - 12:00 PM')
        self.assertContains(response, 'Approved')

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

    def test_until_dried_request_blocks_overlapping_active_window(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is already occupied from')
        self.assertContains(response, self.joel.get_full_name())

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

    def test_flatbed_until_dried_request_allows_large_quantity_without_capacity_limit(self):
        flatbed_machine = Machine.objects.create(
            name='Flatbed Large Quantity',
            machine_type='flatbed_dryer',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
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

        created_rental = DryerRental.objects.filter(machine=flatbed_machine, user=self.viewer).latest('pk')
        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[created_rental.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(created_rental.status, 'pending')
        self.assertEqual(created_rental.quantity, '260 sacks')

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
        self.assertFalse(events[0]['uses_shared_capacity'])

    def test_dryer_list_shows_configured_dryer_options(self):
        solar_machine = Machine.objects.create(
            name='Solar Dryer 2',
            machine_type='solar_dryer',
            dryer_pricing_type='until_dried',
            description='Solar dryer listing test',
            status='available',
            rental_fee_per_day=0,
            current_price='Until Dried',
        )
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.machine.name)
        self.assertContains(response, solar_machine.name)
        self.assertContains(response, 'By Hour')
        self.assertContains(response, 'Until Dried')

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
        self.assertContains(response, 'Admin users assign dryers through this dropdown.')
        self.assertContains(response, 'Add Dryer Unit')
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
        self.assertContains(response, 'Add Dryer Unit')
        self.assertContains(response, 'Add Flatbed Dryer')
        self.assertContains(response, 'Edit Setup')
        self.assertContains(response, 'Delete')
        self.assertContains(response, self.machine.name)
        self.assertNotContains(response, 'Request This Dryer')

    def test_admin_can_delete_dryer_unit_and_return_to_dryer_services(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('machines:delete_machine', args=[self.machine.pk]) + '?service=dryer'
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_list'),
            fetch_redirect_response=False,
        )
        self.assertFalse(Machine.objects.filter(pk=self.machine.pk).exists())

    def test_admin_dryer_list_includes_delete_modal_markup(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('machines:dryer_rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="deleteDryerModal"', html=False)
        self.assertContains(response, 'data-delete-machine-name')
        self.assertContains(response, 'data-delete-url')

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
        self.assertContains(response, 'value="hourly"', html=False)
        self.assertContains(response, 'value="per_sack"', html=False)
        self.assertNotContains(response, 'value="until_dried"', html=False)
        self.assertContains(response, 'Per Hour')
        self.assertContains(response, 'Per Sack')
        self.assertContains(response, 'By Hour')
        self.assertContains(response, 'Until Dried')

    def test_generic_dryer_create_page_prompts_for_dryer_type_first(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('machines:machine_create') + '?service=dryer'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_dryer_setup_flow'])
        self.assertFalse(response.context['dryer_type_is_locked'])
        self.assertContains(response, 'Create Dryer Unit')
        self.assertContains(response, 'PHP 35 per sack')
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
        self.assertEqual(str(machine.acquisition_date), '2026-04-01')
        self.assertEqual(machine.acquisition_amount, Decimal('650000.00'))


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

    def test_admin_can_auto_compute_solar_dryer_payment_from_sacks(self):
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
            {},
        )

        self.assertRedirects(
            response,
            reverse('machines:dryer_rental_detail', args=[solar_rental.pk]),
            fetch_redirect_response=False,
        )
        solar_rental.refresh_from_db()
        self.assertEqual(solar_rental.status, 'paid')
        self.assertEqual(solar_rental.total_amount, Decimal('700.00'))


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
        self.assertEqual(self.machine.status, 'rented')

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
        self.assertEqual(self.machine.status, 'rented')

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

    def test_approve_appointment_overrides_online_payment_choice_to_face_to_face(self):
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
        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(RiceMillAppointment),
            object_id=self.appointment.id,
        )

        self.assertEqual(self.appointment.status, 'approved')
        self.assertEqual(self.appointment.payment_method, 'face_to_face')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, self.appointment.total_amount)

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

    def test_ricemill_create_view_auto_creates_default_rice_mill(self):
        RiceMillAppointment.objects.all().delete()
        Machine.objects.filter(machine_type='rice_mill').delete()

        self.client.force_login(self.user)
        response = self.client.get(reverse('machines:ricemill_appointment_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule Rice Mill Appointment')
        self.assertTrue(Machine.objects.filter(machine_type='rice_mill', name='Rice Mill').exists())

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

    def test_ricemill_update_allows_member_to_change_payment_method(self):
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
                'payment_method': 'online',
                'notes': 'Switch to online payment',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_detail', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.payment_method, 'online')
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
