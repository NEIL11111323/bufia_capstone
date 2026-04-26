from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from bufia.models import Payment
from machines.models import Machine, Rental


User = get_user_model()


class AdminRentalDashboardStageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='dashboard-admin',
            email='dashboard-admin@example.com',
            password='secret123',
            is_staff=True,
        )
        self.member_a = User.objects.create_user(
            username='dashboard-member-a',
            email='dashboard-member-a@example.com',
            password='secret123',
        )
        self.member_b = User.objects.create_user(
            username='dashboard-member-b',
            email='dashboard-member-b@example.com',
            password='secret123',
        )
        self.machine = Machine.objects.create(
            name='Dashboard Tractor',
            machine_type='tractor_4wd',
            status='available',
            rental_fee_per_day=Decimal('5400.00'),
        )
        self.client = Client()
        self.client.login(username='dashboard-admin', password='secret123')

    def test_dashboard_removes_duplicate_summary_panels_and_limits_bulk_approve_to_pending(self):
        Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today(),
            end_date=date.today(),
            status='completed',
            workflow_state='completed',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )

        response = self.client.get(reverse('machines:admin_rental_dashboard'), {'tab': 'completed'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pickups Today')
        self.assertNotContains(response, 'Overdue Returns')
        self.assertNotContains(response, 'record(s) in the current view.')
        self.assertNotContains(response, 'Pending Requests')
        self.assertNotContains(response, 'Approve Selected')
        self.assertContains(response, 'Delete Selected')

    def test_dashboard_header_shows_conflict_review_management_button(self):
        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('machines:admin_conflicts_report'))
        self.assertContains(response, 'Conflict Review')
        self.assertNotContains(response, 'Conflict Review Queue')

    def test_dashboard_flags_conflicting_approved_rentals(self):
        overlap_day = date.today() + timedelta(days=2)
        safe_day = date.today() + timedelta(days=5)
        Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=overlap_day,
            end_date=overlap_day,
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        Rental.objects.create(
            user=self.member_b,
            machine=self.machine,
            start_date=safe_day,
            end_date=safe_day,
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        Rental.objects.filter(user=self.member_b, machine=self.machine).update(
            start_date=overlap_day,
            end_date=overlap_day,
        )

        response = self.client.get(reverse('machines:admin_rental_dashboard'), {'tab': 'approved'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CONFLICT')
        self.assertContains(response, 'Reschedule')
        self.assertNotContains(response, 'Conflicts Report')

    def test_pending_conflict_row_offers_reschedule(self):
        approved_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=2),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        pending_rental = Rental.objects.create(
            user=self.member_b,
            machine=self.machine,
            start_date=date.today() + timedelta(days=6),
            end_date=date.today() + timedelta(days=6),
            status='pending',
            workflow_state='requested',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        Rental.objects.filter(pk=pending_rental.pk).update(
            start_date=approved_rental.start_date,
            end_date=approved_rental.end_date,
        )

        response = self.client.get(reverse('machines:admin_rental_dashboard'), {'tab': 'pending'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CONFLICT')
        self.assertContains(response, 'Reschedule')
        self.assertNotContains(response, 'Conflicts Report')

        review_response = self.client.get(reverse('machines:admin_approve_rental', args=[pending_rental.pk]))
        self.assertEqual(review_response.status_code, 200)
        self.assertContains(review_response, 'Resolve Schedule Conflict')
        self.assertContains(review_response, 'Open Reschedule')

    def test_cancelled_paid_rental_surfaces_refund_actions(self):
        rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today(),
            end_date=date.today(),
            status='cancelled',
            workflow_state='cancelled',
            payment_type='cash',
            payment_method='online',
            payment_amount=Decimal('10800.00'),
            payment_status='paid',
            payment_verified=True,
        )
        Payment.objects.create(
            user=self.member_a,
            payment_type='rental',
            amount=Decimal('10800.00'),
            currency='PHP',
            status='completed',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=rental.id,
        )

        dashboard_response = self.client.get(reverse('machines:admin_rental_dashboard'), {'tab': 'completed'})
        review_response = self.client.get(reverse('machines:admin_approve_rental', args=[rental.id]))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Refund Available')
        self.assertContains(dashboard_response, 'Open Payment / Refund')

        self.assertEqual(review_response.status_code, 200)
        self.assertContains(review_response, 'Refund Management')
        self.assertContains(review_response, 'Process Refund')

    def test_overdue_report_lists_affected_approved_rentals_and_allows_reschedule(self):
        overdue_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() - timedelta(days=3),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        affected_rental = Rental.objects.create(
            user=self.member_b,
            machine=self.machine,
            start_date=date.today() + timedelta(days=4),
            end_date=date.today() + timedelta(days=5),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        Rental.objects.filter(pk=affected_rental.pk).update(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        affected_rental.refresh_from_db()

        response = self.client.get(reverse('machines:admin_overdue_rentals_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Affected Approved Rentals')
        self.assertContains(response, affected_rental.customer_display_name)
        self.assertContains(response, 'Reschedule')
        self.assertContains(response, 'No current approved overlaps', count=0)

        overdue_review_response = self.client.get(reverse('machines:admin_approve_rental', args=[overdue_rental.id]))
        self.assertEqual(overdue_review_response.status_code, 200)
        self.assertContains(overdue_review_response, 'Affected Approved Rentals')
        self.assertContains(overdue_review_response, affected_rental.customer_display_name)

        reschedule_response = self.client.post(
            reverse('machines:reschedule_rental', args=[affected_rental.id]),
            {
                'new_start_date': (date.today() + timedelta(days=4)).isoformat(),
                'new_end_date': (date.today() + timedelta(days=5)).isoformat(),
                'admin_notes': 'Moved because of overdue rental overlap.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        affected_rental.refresh_from_db()
        overdue_rental.refresh_from_db()

        self.assertRedirects(
            reschedule_response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(affected_rental.workflow_state, 'approved')
        self.assertEqual(affected_rental.start_date, date.today() + timedelta(days=4))
        self.assertIn('Rescheduled by', affected_rental.system_note)
        self.assertEqual(overdue_rental.workflow_state, 'overdue')

    def test_overdue_rental_conflicts_with_current_day_booking(self):
        overdue_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() - timedelta(days=4),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        current_day_rental = Rental.objects.create(
            user=self.member_b,
            machine=self.machine,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=3),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )
        Rental.objects.filter(pk=current_day_rental.pk).update(
            start_date=date.today(),
            end_date=date.today(),
        )

        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(response.status_code, 200)
        overdue_rental.refresh_from_db()
        current_day_rental.refresh_from_db()

        self.assertEqual(overdue_rental.workflow_state, 'overdue')
        self.assertEqual(current_day_rental.workflow_state, 'conflict_review')
        self.assertNotContains(response, 'Conflict Review Queue')

        conflicts_response = self.client.get(reverse('machines:admin_conflicts_report'))
        self.assertEqual(conflicts_response.status_code, 200)
        self.assertContains(conflicts_response, 'Conflict Review Queue')
        self.assertContains(conflicts_response, current_day_rental.customer_display_name)

    def test_overdue_page_manage_link_preserves_return_target(self):
        overdue_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )

        response = self.client.get(
            reverse('machines:admin_approve_rental', args=[overdue_rental.id]),
            {
                'source': 'overdue_rentals',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('machines:admin_overdue_rentals_report'))

    def test_extend_rental_supports_custom_days(self):
        overdue_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() - timedelta(days=3),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )

        response = self.client.post(
            reverse('machines:extend_rental', args=[overdue_rental.id]),
            {
                'extension_days': '',
                'custom_days': '4',
                'extension_reason': 'Field work needs more time.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        overdue_rental.refresh_from_db()

        self.assertRedirects(
            response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(overdue_rental.end_date, date.today() + timedelta(days=3))
        self.assertIn('Extended by 4 day(s)', overdue_rental.system_note)

    def test_complete_overdue_rental_marks_rental_completed_and_returns_to_report(self):
        overdue_rental = Rental.objects.create(
            user=self.member_a,
            machine=self.machine,
            start_date=date.today() - timedelta(days=3),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
            payment_amount=Decimal('5400.00'),
        )

        response = self.client.post(
            reverse('machines:complete_overdue_rental', args=[overdue_rental.id]),
            {
                'completion_notes': 'Returned and verified by admin.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        overdue_rental.refresh_from_db()

        self.assertRedirects(
            response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(overdue_rental.status, 'completed')
        self.assertEqual(overdue_rental.workflow_state, 'completed')
        self.assertIn('Completed by', overdue_rental.system_note)
