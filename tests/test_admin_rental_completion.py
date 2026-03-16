from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from machines.models import Machine, Rental
from machines.forms_enhanced import AdminRentalApprovalForm
from notifications.models import UserNotification
from datetime import date, timedelta

User = get_user_model()


class AdminRentalCompletionTests(TestCase):
    """Ensure admins can mark rentals completed using the approval form."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@example.com',
            password='secret',
            is_staff=True
        )
        self.member = User.objects.create_user(
            username='member1',
            email='member@example.com',
            password='secret'
        )
        self.machine = Machine.objects.create(
            name='Test Machine',
            machine_type='tractor',
            status='available'
        )
        self.rental = Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1),
            status='approved',
            payment_type='cash',
            payment_verified=True
        )

    def test_admin_form_includes_completed_choice(self):
        form = AdminRentalApprovalForm(instance=self.rental)
        choices = [choice[0] for choice in form.fields['status'].choices]
        self.assertIn('completed', choices, "'completed' should be offered when the rental is already approved")

    def test_view_post_can_complete(self):
        client = Client()
        client.login(username='admin1', password='secret')

        url = reverse('machines:admin_approve_rental', args=[self.rental.id])
        data = {
            'status': 'completed',
            'verify_payment': 'on',
            'admin_notes': 'finished',
        }
        resp = client.post(url, data)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.status, 'completed')

        # notification should have been created by the signal
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_completed',
                related_object_id=self.rental.id
            ).exists()
        )
        # view redirects to rental list (previous behaviour)
        self.assertRedirects(resp, reverse('machines:rental_list'))
