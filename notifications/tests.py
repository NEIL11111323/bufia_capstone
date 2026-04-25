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

    def test_review_url_uses_notification_redirect_route(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_required',
            message='Please submit your membership form.',
        )

        self.assertEqual(
            notification.review_url,
            reverse('notifications:notification_redirect', args=[notification.id]),
        )

    def test_notification_redirect_marks_notification_as_read(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_required',
            message='Please submit your membership form.',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('notifications:notification_redirect', args=[notification.id]))

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertRedirects(
            response,
            reverse('submit_membership_form'),
            fetch_redirect_response=False,
        )


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

    def test_duplicate_notifications_with_same_payload_are_deduplicated(self):
        first = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_approved',
            message='Your membership is approved.',
            related_object_id=7,
        )
        second = UserNotification.objects.create(
            user=self.user,
            notification_type='membership_approved',
            message='Your membership is approved.',
            related_object_id=7,
        )

        notifications = UserNotification.objects.filter(
            user=self.user,
            notification_type='membership_approved',
        )

        self.assertEqual(notifications.count(), 1)
        self.assertEqual(first.pk, second.pk)

    def test_notifications_context_groups_duplicate_recent_notifications(self):
        UserNotification.objects.create(
            user=self.user,
            notification_type='rental_update',
            message='Rental status updated.',
        )
        UserNotification.objects.create(
            user=self.user,
            notification_type='rental_update',
            message='Rental schedule updated.',
        )

        request = self.factory.get('/dashboard/')
        request.user = self.user

        context = notifications_context(request)

        rental_groups = [
            item for item in context['recent_notification_groups']
            if item['primary'].notification_type == 'rental_update'
        ]
        self.assertEqual(len(rental_groups), 1)
        grouped_item = next(
            item for item in rental_groups
        )
        self.assertEqual(grouped_item['count'], 2)


class UserNotificationsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifviewer',
            email='notifviewer@example.com',
            password='testpassword123',
        )
        self.client.force_login(self.user)

    def test_user_notifications_groups_duplicate_history_entries(self):
        UserNotification.objects.bulk_create([
            UserNotification(
                user=self.user,
                notification_type='rental_approved',
                message='Your rental request has been approved.',
                related_object_id=12,
                is_read=True,
            ),
            UserNotification(
                user=self.user,
                notification_type='rental_approved',
                message='Your rental request has been approved.',
                related_object_id=12,
                is_read=True,
            ),
        ])

        response = self.client.get(reverse('notifications:user_notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rental Request Approved')
        self.assertContains(response, '2 similar')
