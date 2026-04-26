from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from machines.models import Machine, Rental


User = get_user_model()


class AdminRentalApprovalPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='approval-admin',
            email='approval-admin@example.com',
            password='secret123',
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='approval-member',
            email='approval-member@example.com',
            password='secret123',
        )
        self.machine = Machine.objects.create(
            name='Approval Flow Tractor',
            machine_type='tractor_4wd',
            status='available',
            rental_fee_per_day=Decimal('2500.00'),
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=2),
            payment_method='face_to_face',
            payment_type='cash',
            payment_amount=Decimal('2500.00'),
            status='approved',
            workflow_state='approved',
        )

    def test_approval_page_keeps_payment_flow_without_schedule_tracking_panel(self):
        client = Client()
        client.login(username='approval-admin', password='secret123')

        response = client.get(reverse('machines:admin_approve_rental', args=[self.rental.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Over-the-Counter Payment')
        self.assertNotContains(response, 'Pickup and Return Tracking')
        self.assertNotContains(response, 'Scheduled Pickup')
        self.assertNotContains(response, 'Actual Pickup')
        self.assertNotContains(response, 'Save Schedule Tracking')

    def test_approval_page_shows_clear_decision_actions_and_hides_early_completion(self):
        client = Client()
        client.login(username='approval-admin', password='secret123')

        response = client.get(reverse('machines:admin_approve_rental', args=[self.rental.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Approve Rental')
        self.assertContains(response, 'Cancel Rental')
        self.assertNotContains(response, 'Mark Completed')
        self.assertContains(response, 'Back')
        self.assertContains(response, 'type="radio"', html=False)

    def test_operator_required_rental_cannot_be_completed_without_assignment(self):
        client = Client()
        client.login(username='approval-admin', password='secret123')

        self.rental.payment_verified = True
        self.rental.payment_status = 'paid'
        self.rental.workflow_state = 'in_progress'
        self.rental.save(update_fields=['payment_verified', 'payment_status', 'workflow_state', 'updated_at'])

        response = client.get(reverse('machines:admin_approve_rental', args=[self.rental.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assign Operator')
        self.assertNotContains(response, 'Mark Completed')
        self.assertNotContains(response, 'Mark Rental Completed')

        post_response = client.post(
            reverse('machines:admin_approve_rental', args=[self.rental.id]),
            {'status': 'completed'},
            follow=True,
        )

        self.rental.refresh_from_db()
        self.assertEqual(self.rental.status, 'approved')
        self.assertEqual(self.rental.workflow_state, 'in_progress')
        self.assertContains(post_response, 'Assign an operator before marking this rental as completed.')

    def test_paid_completion_action_requires_operator_assignment(self):
        client = Client()
        client.login(username='approval-admin', password='secret123')

        self.rental.payment_verified = True
        self.rental.payment_status = 'paid'
        self.rental.workflow_state = 'in_progress'
        self.rental.save(update_fields=['payment_verified', 'payment_status', 'workflow_state', 'updated_at'])

        response = client.post(
            reverse('machines:admin_complete_rental_early', args=[self.rental.id]),
            follow=True,
        )

        self.rental.refresh_from_db()
        self.assertEqual(self.rental.status, 'approved')
        self.assertEqual(self.rental.workflow_state, 'in_progress')
        self.assertContains(response, 'Assign an operator before marking this rental as completed.')
