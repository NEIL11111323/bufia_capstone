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
        self.assertContains(response, 'Conflict Found')
        self.assertContains(response, 'Conflicts Report')

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
