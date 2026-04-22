from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine, Rental
from notifications.models import UserNotification
from users.models import CustomUser


class RentalScheduleAlertTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='schedule-admin',
            password='secret123',
            is_staff=True,
        )
        self.member = CustomUser.objects.create_user(
            username='schedule-member',
            password='secret123',
        )
        self.machine = Machine.objects.create(
            name='Tracked Tractor',
            machine_type='tractor_4wd',
            status='available',
        )
        self.machine_two = Machine.objects.create(
            name='Tracked Harvester',
            machine_type='harvester',
            status='available',
        )

    def _create_rental(self, **overrides):
        defaults = {
            'machine': self.machine,
            'user': self.member,
            'start_date': timezone.localdate(),
            'end_date': timezone.localdate() + timedelta(days=1),
            'status': 'approved',
            'workflow_state': 'approved',
            'payment_type': 'cash',
        }
        defaults.update(overrides)
        return Rental.objects.create(**defaults)

    def test_schedule_alert_command_creates_pickup_overdue_once(self):
        rental = self._create_rental(
            scheduled_pickup_at=timezone.now() - timedelta(hours=2),
        )

        call_command('check_rental_schedule_alerts')
        call_command('check_rental_schedule_alerts')

        self.assertEqual(
            UserNotification.objects.filter(
                user=self.admin,
                notification_type='rental_pickup_overdue',
                related_object_id=rental.id,
            ).count(),
            1,
        )

    def test_admin_dashboard_includes_schedule_alert_stats(self):
        now = timezone.now()
        self._create_rental(
            scheduled_pickup_at=now - timedelta(hours=3),
            scheduled_return_at=now + timedelta(hours=5),
        )
        self._create_rental(
            machine=self.machine_two,
            scheduled_return_at=now - timedelta(hours=1),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(response.status_code, 200)
        stats = response.context['stats']
        self.assertEqual(stats['pickup_overdue'], 1)
        self.assertEqual(stats['overdue_returns'], 1)
        self.assertGreaterEqual(stats['due_today'], 1)

    def test_admin_can_update_schedule_tracking_and_mark_pickup_return(self):
        rental = self._create_rental()
        self.client.force_login(self.admin)

        pickup = timezone.localtime(timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        returning = timezone.localtime(timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')

        response = self.client.post(
            reverse('machines:update_rental_schedule_tracking', args=[rental.id]),
            {
                'scheduled_pickup_at': pickup,
                'scheduled_return_at': returning,
                'actual_pickup_at': '',
                'actual_return_at': '',
            },
        )
        self.assertRedirects(response, reverse('machines:admin_approve_rental', args=[rental.id]), fetch_redirect_response=False)

        rental.refresh_from_db()
        self.assertIsNotNone(rental.scheduled_pickup_at)
        self.assertIsNotNone(rental.scheduled_return_at)

        response = self.client.post(reverse('machines:mark_rental_picked_up', args=[rental.id]))
        self.assertRedirects(response, reverse('machines:admin_approve_rental', args=[rental.id]), fetch_redirect_response=False)
        rental.refresh_from_db()
        self.assertIsNotNone(rental.actual_pickup_at)

        response = self.client.post(reverse('machines:mark_rental_returned', args=[rental.id]))
        self.assertRedirects(response, reverse('machines:admin_approve_rental', args=[rental.id]), fetch_redirect_response=False)
        rental.refresh_from_db()
        self.assertIsNotNone(rental.actual_return_at)
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_status_update',
                related_object_id=rental.id,
            ).exists()
        )
