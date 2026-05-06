from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from machines.models import Machine, Rental


User = get_user_model()


class OperatorOverviewPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='operator-overview-admin',
            email='admin@example.com',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.operator = User.objects.create_user(
            username='fieldoperator',
            email='operator@example.com',
            password='secret123',
            role=User.OPERATOR,
            first_name='Field',
            last_name='Operator',
            phone_number='09123456789',
            is_active=True,
        )
        self.member = User.objects.create_user(
            username='member-one',
            email='member@example.com',
            password='secret123',
        )
        self.machine = Machine.objects.create(
            name='Overview Tractor',
            machine_type='tractor_4wd',
            status='available',
            rental_fee_per_day=Decimal('3000.00'),
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            assigned_operator=self.operator,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('3000.00'),
            payment_status='paid',
            payment_verified=True,
        )
        self.client.login(username='operator-overview-admin', password='secret123')

    def test_overview_page_shows_needed_actions_including_delete(self):
        response = self.client.get(reverse('machines:operator_overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("machines:operator_overview")}" class="nav-link active"',
            html=False,
        )
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'View')
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Delete')
        self.assertContains(response, reverse('machines:operator_delete', args=[self.operator.id]))
        self.assertContains(response, 'operator@example.com')
        self.assertContains(response, '09123456789')

    def test_operator_detail_page_is_functional_for_admin(self):
        response = self.client.get(reverse('machines:operator_detail', args=[self.operator.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operator Details')
        self.assertContains(response, 'Open Rental Review')
        self.assertContains(response, self.machine.name)
        self.assertContains(response, 'operator@example.com')

    def test_admin_dashboard_view_for_operator_uses_safe_review_links(self):
        response = self.client.get(
            reverse('machines:operator_dashboard'),
            {'operator_id': self.operator.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned machine rentals for this operator.")
        self.assertContains(response, 'Open Rental Review')
        self.assertContains(response, self.machine.name)
        self.assertContains(response, 'PHP 3,000.00')
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Print')
        self.assertContains(response, 'Filter Range')
        self.assertContains(response, 'Amount Total')
        self.assertContains(response, 'id="operatorRentalPreview" aria-hidden="true" hidden', html=False)
        self.assertNotContains(response, 'Accept Task')

    def test_admin_dashboard_view_filters_assigned_rentals_by_date_range(self):
        Rental.objects.create(
            machine=self.machine,
            user=self.member,
            assigned_operator=self.operator,
            start_date=date.today() + timedelta(days=15),
            end_date=date.today() + timedelta(days=16),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_amount=Decimal('3000.00'),
            payment_status='paid',
            payment_verified=True,
        )

        response = self.client.get(
            reverse('machines:operator_dashboard'),
            {
                'operator_id': self.operator.id,
                'date_from': str(date.today() + timedelta(days=1)),
                'date_to': str(date.today() + timedelta(days=3)),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Overview Tractor')
        self.assertContains(response, '1 rental found.')
        self.assertContains(response, 'Operator ID')
        self.assertContains(response, '<th class="col-idx">#</th>', html=False)
