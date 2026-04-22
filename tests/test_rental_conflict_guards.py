from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from machines.models import Machine, Rental


User = get_user_model()


class RentalConflictGuardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='conflict_admin',
            email='conflict_admin@example.com',
            password='secret',
            is_staff=True,
            is_superuser=True,
        )
        self.member_a = User.objects.create_user(
            username='conflict_member_a',
            email='conflict_member_a@example.com',
            password='secret',
        )
        self.member_b = User.objects.create_user(
            username='conflict_member_b',
            email='conflict_member_b@example.com',
            password='secret',
        )
        self.member_c = User.objects.create_user(
            username='conflict_member_c',
            email='conflict_member_c@example.com',
            password='secret',
        )
        self.machine = Machine.objects.create(
            name='Conflict Test Tractor',
            machine_type='tractor',
            status='available',
            rental_fee_per_day=100,
            current_price='100/day',
        )

    def _create_rental(self, *, user, start_date, end_date, status, workflow_state):
        return Rental.objects.create(
            machine=self.machine,
            user=user,
            start_date=start_date,
            end_date=end_date,
            status=status,
            workflow_state=workflow_state,
            payment_type='cash',
            payment_verified=True,
        )

    def test_legacy_approve_view_handles_conflict_without_500(self):
        conflict_day = date.today() + timedelta(days=3)
        safe_day = date.today() + timedelta(days=6)

        self._create_rental(
            user=self.member_a,
            start_date=conflict_day,
            end_date=conflict_day,
            status='approved',
            workflow_state='approved',
        )
        pending = self._create_rental(
            user=self.member_b,
            start_date=safe_day,
            end_date=safe_day,
            status='pending',
            workflow_state='pending_approval',
        )

        # Simulate stale/conflicting data without triggering model clean.
        Rental.objects.filter(pk=pending.pk).update(start_date=conflict_day, end_date=conflict_day)

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:rental_approve', args=[pending.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, 'pending')
        message_text = ' '.join(str(msg) for msg in response.context['messages'])
        self.assertIn('Cannot approve rental', message_text)

    def test_conflicts_report_flags_same_day_approved_overlaps(self):
        overlap_day = date.today() + timedelta(days=4)
        future_day = date.today() + timedelta(days=8)

        approved_a = self._create_rental(
            user=self.member_a,
            start_date=overlap_day,
            end_date=overlap_day,
            status='approved',
            workflow_state='approved',
        )
        approved_b = self._create_rental(
            user=self.member_b,
            start_date=future_day,
            end_date=future_day,
            status='approved',
            workflow_state='approved',
        )

        # Force same-day overlap so report logic must detect inclusive boundaries.
        Rental.objects.filter(pk=approved_b.pk).update(start_date=overlap_day, end_date=overlap_day)

        captured = {}

        def _fake_render(request, template_name, context):
            captured['context'] = context
            return HttpResponse('ok')

        self.client.force_login(self.admin)
        with patch('machines.admin_views.render', side_effect=_fake_render):
            response = self.client.get(reverse('machines:admin_conflicts_report'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('context', captured)
        self.assertGreater(captured['context']['total_conflicts'], 0)

        seen_ids = set()
        for row in captured['context']['conflicts']:
            seen_ids.add(row['rental'].id)
            seen_ids.update(conflict.id for conflict in row['conflicts_with'])

        self.assertIn(approved_a.id, seen_ids)
        self.assertIn(approved_b.id, seen_ids)

    def test_conflicts_report_template_renders(self):
        overlap_day = date.today() + timedelta(days=4)
        future_day = date.today() + timedelta(days=8)

        self._create_rental(
            user=self.member_a,
            start_date=overlap_day,
            end_date=overlap_day,
            status='approved',
            workflow_state='approved',
        )
        approved_b = self._create_rental(
            user=self.member_b,
            start_date=future_day,
            end_date=future_day,
            status='approved',
            workflow_state='approved',
        )
        Rental.objects.filter(pk=approved_b.pk).update(start_date=overlap_day, end_date=overlap_day)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:admin_conflicts_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rental Conflicts Report')
        self.assertContains(response, 'Approved Rental Conflicts')
        self.assertContains(response, 'Pending Requests With Conflict Risk')
        self.assertNotContains(response, 'Most Requested Machines')

    def test_django_admin_bulk_approve_skips_conflicts_and_continues(self):
        conflict_day = date.today() + timedelta(days=5)
        safe_day = date.today() + timedelta(days=9)

        self._create_rental(
            user=self.member_a,
            start_date=conflict_day,
            end_date=conflict_day,
            status='approved',
            workflow_state='approved',
        )
        conflict_pending = self._create_rental(
            user=self.member_b,
            start_date=safe_day,
            end_date=safe_day,
            status='pending',
            workflow_state='pending_approval',
        )
        valid_pending = self._create_rental(
            user=self.member_c,
            start_date=safe_day + timedelta(days=3),
            end_date=safe_day + timedelta(days=3),
            status='pending',
            workflow_state='pending_approval',
        )

        # Force conflict into one pending row.
        Rental.objects.filter(pk=conflict_pending.pk).update(
            start_date=conflict_day,
            end_date=conflict_day,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin:machines_rental_changelist'),
            {
                'action': 'approve_rentals',
                '_selected_action': [str(conflict_pending.pk), str(valid_pending.pk)],
                'select_across': '0',
                'index': '0',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        conflict_pending.refresh_from_db()
        valid_pending.refresh_from_db()
        self.assertEqual(conflict_pending.status, 'pending')
        self.assertEqual(valid_pending.status, 'approved')
        self.assertEqual(valid_pending.workflow_state, 'approved')
