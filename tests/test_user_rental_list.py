from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from machines.models import Machine, Rental


User = get_user_model()


class UserRentalListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='member-rentals',
            email='member-rentals@example.com',
            password='secret123',
        )
        self.machine = Machine.objects.create(
            name='History Tractor',
            machine_type='tractor_4wd',
            status='available',
        )
        self.cancelled_rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() - timedelta(days=1),
            status='cancelled',
            workflow_state='cancelled',
            payment_type='cash',
        )

    def test_cancelled_filter_shows_cancelled_rentals(self):
        client = Client()
        client.login(username='member-rentals', password='secret123')

        response = client.get(reverse('machines:rental_list'), {'status': 'cancelled'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cancelled')
        self.assertContains(response, self.machine.name)

    def test_conflict_review_and_overdue_rentals_appear_in_active_sections(self):
        conflict_rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            status='approved',
            workflow_state='conflict_review',
            payment_type='cash',
        )
        overdue_rental = Rental.objects.create(
            user=self.user,
            machine=self.machine,
            start_date=date.today() - timedelta(days=4),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
        )

        client = Client()
        client.login(username='member-rentals', password='secret123')

        response = client.get(reverse('machines:rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(conflict_rental, response.context['approved_rentals'])
        self.assertIn(overdue_rental, response.context['in_progress_rentals'])
        self.assertNotIn(overdue_rental, response.context['history_rentals'].object_list)
        self.assertContains(response, 'Conflict Review')
        self.assertContains(response, 'Overdue')
