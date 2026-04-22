from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bufia.models import Payment
from irrigation.models import CroppingSeason, IrrigationSeasonRecord
from users.models import MembershipApplication, Sector


User = get_user_model()


class IrrigationAdminPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='irrigation-admin',
            email='irrigation-admin@example.com',
            password='testpass123',
        )
        self.farmer = User.objects.create_user(
            username='irrigation-farmer',
            email='farmer@example.com',
            password='testpass123',
            first_name='Irrigation',
            last_name='Farmer',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.sector, _ = Sector.objects.get_or_create(
            sector_number=1,
            defaults={'name': 'North Sector'},
        )
        self.membership = MembershipApplication.objects.create(
            user=self.farmer,
            is_approved=True,
            assigned_sector=self.sector,
            farm_size=Decimal('2.50'),
        )
        self.available_farmer = User.objects.create_user(
            username='irrigation-available',
            email='available@example.com',
            password='testpass123',
            first_name='Available',
            last_name='Farmer',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.available_membership = MembershipApplication.objects.create(
            user=self.available_farmer,
            is_approved=True,
            assigned_sector=self.sector,
            farm_size=Decimal('1.75'),
        )
        self.other_sector, _ = Sector.objects.get_or_create(
            sector_number=3,
            defaults={'name': 'East Sector'},
        )
        self.other_farmer = User.objects.create_user(
            username='irrigation-other-sector',
            email='other-sector@example.com',
            password='testpass123',
            first_name='Other',
            last_name='Sector',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.other_membership = MembershipApplication.objects.create(
            user=self.other_farmer,
            is_approved=True,
            assigned_sector=self.other_sector,
            farm_size=Decimal('3.10'),
        )
        today = timezone.localdate()
        self.season = CroppingSeason.objects.create(
            name='Wet Season Test',
            planting_date=today - timedelta(days=15),
            harvest_date=today + timedelta(days=30),
            irrigation_rate_per_hectare=Decimal('1200.00'),
            created_by=self.admin,
        )
        self.record = IrrigationSeasonRecord.objects.create(
            season=self.season,
            farmer=self.farmer,
            membership=self.membership,
            sector=self.sector,
            farm_area=Decimal('2.50'),
            irrigation_rate=Decimal('1200.00'),
            total_fee=Decimal('3000.00'),
            amount_paid=Decimal('0.00'),
            status=IrrigationSeasonRecord.STATUS_ACTIVE,
        )
        self.client.force_login(self.admin)

    def test_irrigation_admin_pages_render(self):
        urls = [
            reverse('irrigation:admin_irrigation_request_list'),
            reverse('irrigation:admin_irrigation_request_create'),
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
            reverse('irrigation:admin_irrigation_request_edit', args=[self.season.pk]),
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_irrigation_process_nav_only_shows_on_dashboard(self):
        dashboard_response = self.client.get(
            reverse('irrigation:admin_irrigation_request_list')
        )
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'irrigation-process-nav')
        self.assertNotContains(dashboard_response, '<strong class="irrigation-process-link__title">Payment History</strong>', html=True)

        other_urls = [
            reverse('irrigation:admin_irrigation_request_create'),
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
            reverse('irrigation:admin_irrigation_request_edit', args=[self.season.pk]),
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
        ]

        for url in other_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'irrigation-process-nav')

    def test_admin_detail_header_buttons_render_expected_targets(self):
        response = self.client.get(
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('irrigation:admin_irrigation_request_list'))
        self.assertContains(response, reverse('irrigation:admin_irrigation_request_edit', args=[self.season.pk]))
        self.assertContains(response, reverse('irrigation:admin_irrigation_generate_billing', args=[self.season.pk]))
        self.assertContains(response, reverse('irrigation:admin_irrigation_close_season', args=[self.season.pk]))
        self.assertContains(response, 'season-header-actions__back')
        self.assertContains(
            response,
            f"{reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])}?report=1#tabular-print-report",
        )
        self.assertContains(response, 'View Report')
        self.assertNotContains(response, 'Hide Report')
        self.assertNotContains(response, 'class="btn btn-outline-secondary">History</a>')
        self.assertNotContains(response, 'Printable Tabular Report')

    def test_closed_season_is_not_editable_but_report_button_remains(self):
        self.season.status = CroppingSeason.STATUS_CLOSED
        self.season.closed_at = timezone.now()
        self.season.save(update_fields=['status', 'closed_at', 'updated_at'])
        self.record.status = IrrigationSeasonRecord.STATUS_CLOSED
        self.record.save(update_fields=['status', 'updated_at'])

        edit_response = self.client.get(
            reverse('irrigation:admin_irrigation_request_edit', args=[self.season.pk])
        )
        self.assertRedirects(
            edit_response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )

        record_edit_response = self.client.get(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk])
        )
        self.assertRedirects(
            record_edit_response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )

        detail_response = self.client.get(
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])
        )
        self.assertContains(detail_response, 'Edit Locked')
        self.assertContains(detail_response, 'View Report')
        self.assertNotContains(detail_response, 'Edit Season</a>')

    def test_admin_detail_report_section_is_shown_on_request(self):
        response = self.client.get(
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]) + '?report=1'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Printable Tabular Report')
        self.assertContains(response, 'Print Report')
        self.assertContains(response, 'Hide Report')
        self.assertContains(response, 'BUFIA Irrigation Season Report')
        self.assertNotContains(response, 'Season Summary')
        self.assertNotContains(response, 'Assigned Irrigation Records')
        self.assertNotContains(response, 'Payment History')

    def test_preharvest_payment_confirmation_is_blocked(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_confirm_payment', args=[self.record.pk]),
            {
                'amount_paid': '3000.00',
                'notes': 'Attempted early payment',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.record.refresh_from_db()
        self.season.refresh_from_db()
        self.assertEqual(self.record.amount_paid, Decimal('0.00'))
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_ACTIVE)
        self.assertEqual(self.season.status, CroppingSeason.STATUS_ACTIVE)

    def test_generate_billing_button_flow_marks_records_harvested(self):
        self.season.harvest_date = timezone.localdate() - timedelta(days=1)
        self.season.save(update_fields=['harvest_date', 'updated_at'])

        response = self.client.post(
            reverse('irrigation:admin_irrigation_generate_billing', args=[self.season.pk])
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.season.refresh_from_db()
        self.record.refresh_from_db()

        self.assertIsNotNone(self.season.billing_generated_at)
        self.assertEqual(self.season.status, CroppingSeason.STATUS_HARVESTED)
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_HARVESTED)
        self.assertIsNotNone(self.record.billed_at)

    def test_harvested_record_without_payment_method_shows_confirm_face_to_face_button(self):
        self.season.harvest_date = timezone.localdate() - timedelta(days=1)
        self.season.billing_generated_at = timezone.now()
        self.season.status = CroppingSeason.STATUS_HARVESTED
        self.season.save(update_fields=['harvest_date', 'billing_generated_at', 'status', 'updated_at'])
        self.record.status = IrrigationSeasonRecord.STATUS_HARVESTED
        self.record.payment_method = ''
        self.record.save(update_fields=['status', 'payment_method', 'updated_at'])

        response = self.client.get(
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Over the Counter')
        self.assertContains(
            response,
            reverse("irrigation:admin_irrigation_confirm_payment", args=[self.record.pk]),
        )
        self.assertContains(response, 'name="payment_method" value="face_to_face"', html=False)

    def test_assignment_panel_uses_sector_choices_and_farmer_checkboxes(self):
        response = self.client.get(
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose Sector')
        self.assertContains(response, 'name="sector"', html=False)
        self.assertContains(response, f'id="assign-sector-{self.sector.pk}"', html=False)
        self.assertContains(response, f'id="assign-sector-{self.other_sector.pk}"', html=False)
        self.assertContains(response, 'type="checkbox"', html=False)
        self.assertContains(response, self.available_farmer.get_full_name())
        self.assertContains(response, self.other_farmer.get_full_name())

    def test_admin_can_assign_farmer_from_selected_sector(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_assign_farmers', args=[self.season.pk]),
            {
                'sector': str(self.sector.pk),
                'farmers': [str(self.available_farmer.pk)],
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])}?sector={self.sector.pk}#assign-farmers",
        )
        assigned_record = IrrigationSeasonRecord.objects.get(
            season=self.season,
            farmer=self.available_farmer,
        )
        self.assertEqual(assigned_record.membership, self.available_membership)
        self.assertEqual(assigned_record.sector, self.sector)
        self.assertEqual(assigned_record.farm_area, Decimal('1.75'))

    def test_assignment_rejects_farmer_from_unselected_sector(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_assign_farmers', args=[self.season.pk]),
            {
                'sector': str(self.sector.pk),
                'farmers': [str(self.other_farmer.pk)],
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk])}?sector={self.sector.pk}#assign-farmers",
        )
        self.assertFalse(
            IrrigationSeasonRecord.objects.filter(
                season=self.season,
                farmer=self.other_farmer,
            ).exists()
        )

    def test_harvested_record_can_be_confirmed_over_the_counter_directly_from_request_detail(self):
        self.season.harvest_date = timezone.localdate() - timedelta(days=1)
        self.season.billing_generated_at = timezone.now()
        self.season.status = CroppingSeason.STATUS_HARVESTED
        self.season.save(update_fields=['harvest_date', 'billing_generated_at', 'status', 'updated_at'])
        self.record.status = IrrigationSeasonRecord.STATUS_HARVESTED
        self.record.payment_method = ''
        self.record.amount_paid = Decimal('0.00')
        self.record.save(update_fields=['status', 'payment_method', 'amount_paid', 'updated_at'])

        response = self.client.post(
            reverse('irrigation:admin_irrigation_confirm_payment', args=[self.record.pk]),
            {
                'payment_method': IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
                'amount_paid': '3000.00',
                'notes': 'Confirmed over the counter from irrigation season summary.',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.record.refresh_from_db()

        self.assertEqual(self.record.payment_method, IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE)
        self.assertEqual(self.record.amount_paid, Decimal('3000.00'))
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_PAID)
        self.assertEqual(self.record.payment_confirmed_by, self.admin)

    def test_admin_can_record_walk_in_advance_payment_from_record_edit(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
            {
                'action': 'confirm_payment',
                'amount_paid': '3000.00',
                'notes': 'Walk-in early settlement at office.',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.record.refresh_from_db()
        self.season.refresh_from_db()

        self.assertEqual(self.record.amount_paid, Decimal('3000.00'))
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_PAID)
        self.assertEqual(self.record.payment_method, IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE)
        self.assertEqual(self.record.payment_confirmed_by, self.admin)
        self.assertIn('Walk-in early settlement at office.', self.record.notes)
        self.assertEqual(self.season.status, CroppingSeason.STATUS_ACTIVE)

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
            object_id=self.record.pk,
        )
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.payment_type, 'irrigation')
        self.assertEqual(payment.currency, 'PHP')
        self.assertEqual(payment.amount, Decimal('3000.00'))

    def test_record_edit_prefills_payment_amount_with_current_due_amount(self):
        response = self.client.get(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="amount_paid"')
        self.assertContains(response, 'value="3000.00"')

    def test_admin_can_record_partial_walk_in_advance_payment_from_record_edit(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
            {
                'action': 'confirm_payment',
                'amount_paid': '1000.00',
                'notes': 'Half paid in advance at office.',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.record.refresh_from_db()
        self.season.refresh_from_db()

        self.assertEqual(self.record.amount_paid, Decimal('1000.00'))
        self.assertEqual(self.record.balance_due, Decimal('2000.00'))
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_ACTIVE)
        self.assertEqual(self.record.payment_method, IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE)
        self.assertIn('Half paid in advance at office.', self.record.notes)
        self.assertEqual(self.season.status, CroppingSeason.STATUS_ACTIVE)

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
            object_id=self.record.pk,
        )
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, Decimal('2000.00'))
        self.assertEqual(payment.payment_provider, 'manual')

    def test_close_season_button_flow_closes_paid_season(self):
        self.record.mark_paid(
            confirmed_by=self.admin,
            amount=self.record.total_fee,
            payment_method=IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE,
        )
        self.season.billing_generated_at = timezone.now()
        self.season.save(update_fields=['billing_generated_at', 'updated_at'])
        self.season.sync_status()

        response = self.client.post(
            reverse('irrigation:admin_irrigation_close_season', args=[self.season.pk])
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_request_detail', args=[self.season.pk]),
        )
        self.season.refresh_from_db()
        self.record.refresh_from_db()

        self.assertEqual(self.season.status, CroppingSeason.STATUS_CLOSED)
        self.assertIsNotNone(self.season.closed_at)
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_CLOSED)

    def test_generate_billing_preserves_walk_in_paid_member(self):
        self.client.post(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
            {
                'action': 'confirm_payment',
                'amount_paid': '3000.00',
                'notes': 'Settled in advance.',
            },
        )

        self.membership.farm_size = Decimal('5.00')
        self.membership.save(update_fields=['farm_size'])
        self.season.irrigation_rate_per_hectare = Decimal('2000.00')
        self.season.harvest_date = timezone.localdate() - timedelta(days=1)
        self.season.save(update_fields=['irrigation_rate_per_hectare', 'harvest_date', 'updated_at'])

        self.season.generate_billing()
        self.record.refresh_from_db()
        self.season.refresh_from_db()

        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_PAID)
        self.assertEqual(self.record.total_fee, Decimal('3000.00'))
        self.assertEqual(self.record.amount_paid, Decimal('3000.00'))
        self.assertIsNotNone(self.record.billed_at)

    def test_record_details_are_not_editable_from_record_page(self):
        response = self.client.post(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
            {
                'action': 'update_record',
                'sector': self.sector.pk,
                'farm_area': '3.00',
                'irrigation_rate': '1200.00',
                'total_fee': '3600.00',
                'notes': 'Corrected farm area before harvest billing.',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
        )
        self.record.refresh_from_db()
        self.season.refresh_from_db()
        self.assertEqual(self.record.farm_area, Decimal('2.50'))
        self.assertEqual(self.record.total_fee, Decimal('3000.00'))
        self.assertEqual(self.record.notes, '')
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_ACTIVE)
        self.assertEqual(self.season.status, CroppingSeason.STATUS_PLANNED)

    def test_paid_record_does_not_force_preharvest_season_to_harvested(self):
        self.record.amount_paid = Decimal('3000.00')
        self.record.status = IrrigationSeasonRecord.STATUS_PAID
        self.record.paid_at = timezone.now()
        self.record.save(update_fields=['amount_paid', 'status', 'paid_at', 'updated_at'])

        self.season.sync_status()
        self.season.refresh_from_db()

        self.assertEqual(self.season.status, CroppingSeason.STATUS_ACTIVE)

    def test_partial_payment_balance_is_not_changed_by_blocked_record_edit(self):
        self.record.amount_paid = Decimal('1000.00')
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
        self.record.status = IrrigationSeasonRecord.STATUS_ACTIVE
        self.record.save(update_fields=['amount_paid', 'payment_method', 'status', 'updated_at'])

        response = self.client.post(
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
            {
                'action': 'update_record',
                'sector': self.sector.pk,
                'farm_area': '3.00',
                'irrigation_rate': '1200.00',
                'total_fee': '3600.00',
                'notes': 'Adjusted fee after partial advance payment.',
            },
        )

        self.assertRedirects(
            response,
            reverse('irrigation:admin_irrigation_record_edit', args=[self.record.pk]),
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.total_fee, Decimal('3000.00'))
        self.assertEqual(self.record.amount_paid, Decimal('1000.00'))
        self.assertEqual(self.record.balance_due, Decimal('2000.00'))
        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_ACTIVE)

        self.assertFalse(
            Payment.objects.filter(
                content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
                object_id=self.record.pk,
            ).exists()
        )


class IrrigationMemberPaymentFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='irrigation-superadmin',
            email='irrigation-superadmin@example.com',
            password='testpass123',
        )
        self.farmer = User.objects.create_user(
            username='irrigation-member',
            email='irrigation-member@example.com',
            password='testpass123',
            first_name='Season',
            last_name='Member',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.sector, _ = Sector.objects.get_or_create(
            sector_number=2,
            defaults={'name': 'South Sector'},
        )
        self.membership = MembershipApplication.objects.create(
            user=self.farmer,
            is_approved=True,
            assigned_sector=self.sector,
            farm_size=Decimal('1.50'),
        )
        today = timezone.localdate()
        self.season = CroppingSeason.objects.create(
            name='Harvest Billing Season',
            planting_date=today - timedelta(days=40),
            harvest_date=today - timedelta(days=1),
            irrigation_rate_per_hectare=Decimal('1500.00'),
            status=CroppingSeason.STATUS_HARVESTED,
            billing_generated_at=timezone.now(),
            created_by=self.admin,
        )
        self.record = IrrigationSeasonRecord.objects.create(
            season=self.season,
            farmer=self.farmer,
            membership=self.membership,
            sector=self.sector,
            farm_area=Decimal('1.50'),
            irrigation_rate=Decimal('1500.00'),
            total_fee=Decimal('2250.00'),
            amount_paid=Decimal('0.00'),
            status=IrrigationSeasonRecord.STATUS_HARVESTED,
        )
        self.client.force_login(self.farmer)

    def test_member_can_choose_online_payment_after_billing(self):
        response = self.client.post(
            reverse('irrigation:irrigation_payment_method', args=[self.record.pk]),
            {'payment_method': 'online'},
        )

        self.assertRedirects(
            response,
            reverse('irrigation:irrigation_request_detail', args=[self.record.pk]),
        )
        self.record.refresh_from_db()
        self.assertEqual(self.record.payment_method, IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE)

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
            object_id=self.record.pk,
        )
        self.assertEqual(payment.payment_type, 'irrigation')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.currency, 'PHP')
        self.assertEqual(payment.amount, Decimal('2250.00'))

    def test_member_dashboard_shows_online_and_face_to_face_choices_after_billing(self):
        response = self.client.get(reverse('irrigation:irrigation_request_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Billing is ready for payment selection.')
        self.assertContains(response, '>Online</button>', html=False)
        self.assertContains(response, '>Face-to-Face</button>', html=False)

    def test_member_detail_shows_online_and_face_to_face_choices_after_billing(self):
        response = self.client.get(reverse('irrigation:irrigation_request_detail', args=[self.record.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose Online')
        self.assertContains(response, 'Choose Face-to-Face')

    def test_irrigation_receipt_returns_to_water_irrigation_when_opened_from_dashboard(self):
        self.record.amount_paid = Decimal('2250.00')
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        self.record.status = IrrigationSeasonRecord.STATUS_PAID
        self.record.paid_at = timezone.now()
        self.record.save(update_fields=['amount_paid', 'payment_method', 'status', 'paid_at', 'updated_at'])

        response = self.client.get(
            reverse('irrigation:irrigation_receipt', args=[self.record.pk]),
            {'next': reverse('irrigation:irrigation_request_list')},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to Water Irrigation')
        self.assertContains(response, reverse('irrigation:irrigation_request_list'))

    def test_member_dashboard_shows_remaining_balance_after_partial_advance_payment(self):
        self.record.amount_paid = Decimal('750.00')
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
        self.record.status = IrrigationSeasonRecord.STATUS_HARVESTED
        self.record.save(update_fields=['amount_paid', 'payment_method', 'status', 'updated_at'])

        response = self.client.get(reverse('irrigation:irrigation_request_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PHP 750.00 paid, PHP 1500.00 remaining')

    def test_member_detail_shows_partial_payment_message(self):
        self.record.amount_paid = Decimal('750.00')
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_FACE_TO_FACE
        self.record.status = IrrigationSeasonRecord.STATUS_HARVESTED
        self.record.save(update_fields=['amount_paid', 'payment_method', 'status', 'updated_at'])

        response = self.client.get(reverse('irrigation:irrigation_request_detail', args=[self.record.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Partial payment was recorded.')
        self.assertContains(response, 'Payment status: Partially Paid')

    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.create')
    def test_irrigation_checkout_uses_billed_season_record(self, mock_session_create, _mock_configured):
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        self.record.save(update_fields=['payment_method', 'updated_at'])

        mock_session = type('CheckoutSession', (), {'id': 'cs_test_irrigation', 'url': 'https://example.com/checkout'})()
        mock_session_create.return_value = mock_session

        response = self.client.get(reverse('create_irrigation_payment', args=[self.record.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://example.com/checkout')

        kwargs = mock_session_create.call_args.kwargs
        self.assertEqual(kwargs['line_items'][0]['price_data']['currency'], 'php')
        self.assertEqual(kwargs['metadata']['irrigation_record_id'], str(self.record.pk))

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
            object_id=self.record.pk,
        )
        self.assertEqual(payment.stripe_session_id, 'cs_test_irrigation')

    @patch('bufia.views.payment_views._stripe_is_configured', return_value=True)
    @patch('bufia.views.payment_views.stripe.checkout.Session.retrieve')
    def test_irrigation_payment_success_waits_for_admin_confirmation(self, mock_session_retrieve, _mock_configured):
        self.record.payment_method = IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE
        self.record.save(update_fields=['payment_method', 'updated_at'])

        payment = Payment.objects.create(
            user=self.farmer,
            payment_type='irrigation',
            amount=Decimal('2250.00'),
            currency='PHP',
            status='pending',
            stripe_session_id='cs_paid_irrigation',
            content_type=ContentType.objects.get_for_model(IrrigationSeasonRecord),
            object_id=self.record.pk,
        )

        mock_session_retrieve.return_value = {
            'id': 'cs_paid_irrigation',
            'status': 'complete',
            'payment_status': 'paid',
            'payment_intent': 'pi_irrigation_paid',
            'amount_total': 225000,
        }

        response = self.client.get(reverse('payment_success'), {
            'session_id': 'cs_paid_irrigation',
            'type': 'irrigation',
            'id': self.record.pk,
            'transaction_id': payment.internal_transaction_id,
        })

        self.assertRedirects(
            response,
            reverse('irrigation:irrigation_request_detail', args=[self.record.pk]),
        )
        self.record.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(self.record.status, IrrigationSeasonRecord.STATUS_HARVESTED)
        self.assertEqual(self.record.payment_method, IrrigationSeasonRecord.PAYMENT_METHOD_ONLINE)
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_irrigation_paid')
