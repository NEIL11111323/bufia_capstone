from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine, Rental
from notifications.models import UserNotification


User = get_user_model()


class OverdueRentalActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='overdue-admin',
            email='admin@example.com',
            password='secret',
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='overdue-member',
            email='member@example.com',
            password='secret',
        )
        self.machine = Machine.objects.create(
            name='Overdue Test Tractor',
            machine_type='tractor',
            status='available',
        )
        self.client.login(username='overdue-admin', password='secret')

    def test_complete_overdue_rental_marks_completed_and_notifies_member(self):
        rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=timezone.localdate() - timedelta(days=4),
            end_date=timezone.localdate() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
            payment_status='paid',
        )

        response = self.client.post(
            reverse('machines:complete_overdue_rental', args=[rental.id]),
            {
                'completion_notes': 'Returned to BUFIA.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.status, 'completed')
        self.assertEqual(rental.workflow_state, 'completed')
        self.assertIsNotNone(rental.actual_return_at)
        self.assertIsNotNone(rental.actual_completion_time)
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_completed',
                related_object_id=rental.id,
            ).exists()
        )

    def test_extend_rental_updates_end_date_and_creates_notification(self):
        rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=timezone.localdate() - timedelta(days=3),
            end_date=timezone.localdate() - timedelta(days=1),
            status='approved',
            workflow_state='overdue',
            payment_type='cash',
            payment_status='paid',
        )

        response = self.client.post(
            reverse('machines:extend_rental', args=[rental.id]),
            {
                'extension_days': '2',
                'extension_reason': 'Farmer requested more time.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.end_date, timezone.localdate() + timedelta(days=1))
        self.assertEqual(rental.workflow_state, 'approved')
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_extended',
                related_object_id=rental.id,
            ).exists()
        )

    def test_reschedule_rental_updates_dates_and_creates_notification(self):
        start_date = timezone.localdate() + timedelta(days=2)
        end_date = timezone.localdate() + timedelta(days=4)
        rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=start_date,
            end_date=end_date,
            status='approved',
            workflow_state='conflict_review',
            payment_type='cash',
            payment_status='paid',
        )

        new_start = timezone.localdate() + timedelta(days=6)
        new_end = timezone.localdate() + timedelta(days=8)

        response = self.client.post(
            reverse('machines:reschedule_rental', args=[rental.id]),
            {
                'new_start_date': new_start.isoformat(),
                'new_end_date': new_end.isoformat(),
                'admin_notes': 'Moved after overdue machine release.',
                'return_url': reverse('machines:admin_overdue_rentals_report'),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('machines:admin_overdue_rentals_report'),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.start_date, new_start)
        self.assertEqual(rental.end_date, new_end)
        self.assertEqual(rental.workflow_state, 'approved')
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_rescheduled',
                related_object_id=rental.id,
            ).exists()
        )
