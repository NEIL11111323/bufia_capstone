"""
Tests for early rental completion functionality.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from machines.models import Machine, Rental, RentalStateChange

User = get_user_model()


class EarlyCompletionTestCase(TestCase):
    """Test early completion of in-kind rentals."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True
        )

        # Create farmer user
        self.farmer = User.objects.create_user(
            username='farmer',
            password='testpass123'
        )

        # Create machine
        self.machine = Machine.objects.create(
            name='Test Harvester',
            machine_type='harvester',
            rental_price_type='in_kind',
            in_kind_farmer_share=9,
            in_kind_organization_share=1,
            current_price='1 sack per 9 harvested'
        )

        # Create in-kind rental in progress
        today = timezone.now().date()
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.farmer,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=2),
            payment_type='in_kind',
            workflow_state='in_progress',
            actual_handover_date=timezone.now() - timedelta(days=2)
        )

        self.client = Client()

    def test_early_completion_view_requires_login(self):
        """Test that early completion view requires authentication."""
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_early_completion_view_get_request(self):
        """Test GET request to early completion view."""
        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            'machines/admin/complete_rental_early.html'
        )
        self.assertEqual(response.context['rental'], self.rental)

    def test_early_completion_post_request(self):
        """Test POST request to complete rental early."""
        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        response = self.client.post(
            url,
            {'reason': 'Harvest completed ahead of schedule'}
        )

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)

        # Refresh rental from database
        self.rental.refresh_from_db()

        # Check rental state changed
        self.assertEqual(self.rental.workflow_state, 'completed')
        self.assertIsNotNone(self.rental.actual_completion_time)
        self.assertEqual(self.rental.state_changed_by, self.admin)

    def test_early_completion_creates_state_change_record(self):
        """Test that early completion creates a state change record."""
        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        self.client.post(
            url,
            {'reason': 'Early completion test'}
        )

        # Check state change record
        state_change = RentalStateChange.objects.filter(
            rental=self.rental,
            from_state='in_progress',
            to_state='completed'
        ).first()

        self.assertIsNotNone(state_change)
        self.assertEqual(state_change.changed_by, self.admin)
        self.assertEqual(state_change.reason, 'Early completion test')

    def test_early_completion_only_for_in_progress(self):
        """Test that early completion only works for in_progress rentals."""
        # Change rental to completed state
        self.rental.workflow_state = 'completed'
        self.rental.save()

        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        response = self.client.post(
            url,
            {'reason': 'Should fail'}
        )

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

    def test_early_completion_sets_actual_completion_time(self):
        """Test that actual_completion_time is set correctly."""
        before_completion = timezone.now()

        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        self.client.post(url, {'reason': 'Test'})

        self.rental.refresh_from_db()
        after_completion = timezone.now()

        # Check that actual_completion_time is set
        self.assertIsNotNone(self.rental.actual_completion_time)

        # Check that it's within reasonable time range
        self.assertGreaterEqual(
            self.rental.actual_completion_time,
            before_completion
        )
        self.assertLessEqual(
            self.rental.actual_completion_time,
            after_completion
        )

    def test_early_completion_preserves_rental_record(self):
        """Test that rental record is preserved after early completion."""
        rental_id = self.rental.id

        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        self.client.post(url, {'reason': 'Test'})

        # Rental should still exist in database
        rental = Rental.objects.get(id=rental_id)
        self.assertIsNotNone(rental)
        self.assertEqual(rental.workflow_state, 'completed')

    def test_early_completion_audit_trail(self):
        """Test that early completion creates proper audit trail."""
        self.client.login(username='admin', password='testpass123')
        url = reverse(
            'machines:admin_complete_rental_early',
            kwargs={'rental_id': self.rental.id}
        )

        self.client.post(
            url,
            {'reason': 'Harvest completed early'}
        )

        # Check state changes
        state_changes = RentalStateChange.objects.filter(
            rental=self.rental
        ).order_by('-changed_at')

        self.assertGreater(state_changes.count(), 0)

        latest_change = state_changes.first()
        self.assertEqual(latest_change.from_state, 'in_progress')
        self.assertEqual(latest_change.to_state, 'completed')
        self.assertEqual(latest_change.changed_by, self.admin)
