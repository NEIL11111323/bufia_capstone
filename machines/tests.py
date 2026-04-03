import json
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from .models import DryerRental, Machine, RiceMillAppointment
from bufia.models import Payment


User = get_user_model()


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
        self.machine = Machine.objects.create(
            name='Flatbed Dryer 1',
            machine_type='flatbed_dryer',
            description='Dryer for testing',
            status='available',
            rental_fee_per_day=150,
            current_price='150/hour',
        )
        self.rental_date = date.today() + timedelta(days=1)
        self.existing_rental = DryerRental.objects.create(
            machine=self.machine,
            user=self.joel,
            rental_date=self.rental_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            status='approved',
        )

    def test_dryer_form_shows_other_users_booked_time_ranges(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose a rental date to view booked dryer time ranges for that day.')
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
                'rental_date': self.rental_date.isoformat(),
                'start_time': '10:00',
                'end_time': '11:00',
                'notes': 'Overlap attempt',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The selected dryer time range conflicts with Joel Dela Cruz')
        self.assertContains(response, '9:00 AM - 12:00 PM')
        self.assertContains(response, 'Approved - Waiting for Payment')

    def test_dryer_form_redirects_to_detail_page_after_successful_submit(self):
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse('machines:dryer_rental_create_for_machine', args=[self.machine.pk]),
            {
                'machine': self.machine.pk,
                'rental_date': self.rental_date.isoformat(),
                'start_time': '13:00',
                'end_time': '15:00',
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

    def test_dryer_form_still_loads_when_dryer_machine_status_is_not_available(self):
        self.machine.status = 'rented'
        self.machine.save(update_fields=['status'])
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule Dryer Booking')
        self.assertContains(response, self.machine.name)

    def test_dryer_form_creates_default_dryer_unit_when_none_exists(self):
        DryerRental.objects.all().delete()
        Machine.objects.filter(machine_type='flatbed_dryer').delete()
        self.client.force_login(self.viewer)

        response = self.client.get(reverse('machines:dryer_rental_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Flatbed Dryer')
        self.assertTrue(Machine.objects.filter(machine_type='flatbed_dryer', name='Flatbed Dryer').exists())

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
                'rental_date': self.rental_date.isoformat(),
                'start_time': '10:00',
                'end_time': '11:00',
                'notes': 'Overlap with pending request',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The selected dryer time range conflicts with Joel Dela Cruz')
        self.assertContains(response, 'Pending Approval')


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
        self.machine = Machine.objects.create(
            name='Flatbed Dryer 2',
            machine_type='flatbed_dryer',
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
            status='approved',
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

        self.assertEqual(self.dryer_rental.status, 'approved')
        self.assertEqual(self.dryer_rental.payment_method, 'face_to_face')
        self.assertEqual(self.payment.status, 'pending')
        mock_create_user_notification.assert_not_called()
        mock_notify_staff.assert_not_called()


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
        self.appointment.status = 'approved'
        self.appointment.payment_method = 'face_to_face'
        self.appointment.save(update_fields=['status', 'payment_method', 'updated_at'])
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
                'rice_quantity': '200',
                'notes': '',
            },
        )

        created = RiceMillAppointment.objects.exclude(pk=self.appointment.pk).get(user=self.user)
        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_pending', args=[created.pk]),
            fetch_redirect_response=False,
        )
        self.assertIsNone(created.start_time)
        self.assertIsNone(created.end_time)
        self.assertEqual(created.display_time_range, 'Flexible daytime arrival')

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
                'rice_quantity': '200',
                'notes': '',
            },
        )

        created = RiceMillAppointment.objects.exclude(pk__in=[self.appointment.pk]).filter(user=self.user).first()
        self.assertIsNotNone(created)
        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_pending', args=[created.pk]),
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
                'rice_quantity': '550',
                'notes': 'Updated booking request',
            },
        )

        self.assertRedirects(
            response,
            reverse('machines:ricemill_appointment_pending', args=[self.appointment.pk]),
            fetch_redirect_response=False,
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')
