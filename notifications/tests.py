from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import UserNotification

User = get_user_model()


class UserNotificationRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifmember',
            email='notifmember@example.com',
            password='testpassword123',
        )

    def test_membership_approved_redirects_to_membership_slip(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_approved',
            message='Approved',
        )

        self.assertEqual(notification.get_redirect_url(), reverse('membership_slip'))

    def test_membership_required_redirects_to_membership_submit_form(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_required',
            message='Please submit your membership form.',
        )

        self.assertEqual(notification.get_redirect_url(), reverse('submit_membership_form'))

    def test_membership_rejected_redirects_to_membership_info(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_rejected',
            message='Rejected',
        )

        self.assertEqual(notification.get_redirect_url(), reverse('view_membership_info_self'))
