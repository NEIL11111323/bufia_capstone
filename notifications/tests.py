from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .context_processors import notifications_context
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


class NotificationContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='notifcontextuser',
            email='notifcontext@example.com',
            password='testpassword123',
        )

    def test_notifications_context_returns_defaults_when_queries_fail(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user

        with patch(
            'notifications.context_processors.UserNotification.objects.filter',
            side_effect=OperationalError('no such column: notifications_usernotification.priority'),
        ):
            context = notifications_context(request)

        self.assertEqual(context['unread_notifications_count'], 0)
        self.assertEqual(context['recent_notifications'], [])
        self.assertEqual(context['recent_notification_groups'], [])
