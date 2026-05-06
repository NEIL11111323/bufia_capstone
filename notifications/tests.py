from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.core.management import call_command
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from machines.models import DryerRental, Machine, Rental, RiceMillAppointment, RentalPackage
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
        self.package = RentalPackage.objects.create(
            user=self.user,
            package_name='Whole Farming Service Package',
            farmer_name='Notif Member',
            location='Test Farm',
            preferred_start_date=timezone.now().date() + timedelta(days=2),
            status='pending',
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

    def test_package_notification_redirects_to_package_detail(self):
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='rental_package_submitted',
            message='Your package request was submitted.',
            related_object_id=self.package.pk,
        )

        self.assertEqual(
            notification.get_redirect_url(),
            reverse('machines:rental_package_detail', args=[self.package.pk]),
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
        self.assertEqual(context['package_notification_count'], 0)

    def test_notifications_context_counts_member_package_updates(self):
        package = RentalPackage.objects.create(
            user=self.user,
            package_name='Whole Farming Service Package',
            farmer_name='Context Member',
            location='Test Farm',
            preferred_start_date=timezone.now().date() + timedelta(days=3),
            member_last_viewed_at=timezone.now() - timedelta(days=1),
            status='approved',
        )

        request = self.factory.get('/machines/rentals/')
        request.user = self.user

        context = notifications_context(request)

        self.assertEqual(context['package_notification_count'], 1)
        self.assertEqual(package.user, self.user)

    def test_notifications_context_counts_admin_package_alerts_by_package(self):
        admin = User.objects.create_user(
            username='notifcontextadmin',
            email='notifcontextadmin@example.com',
            password='testpassword123',
            is_staff=True,
        )
        first_package = RentalPackage.objects.create(
            user=self.user,
            package_name='Package One',
            farmer_name='Context Member',
            location='First Farm',
            preferred_start_date=timezone.now().date() + timedelta(days=3),
            status='pending',
        )
        second_package = RentalPackage.objects.create(
            user=self.user,
            package_name='Package Two',
            farmer_name='Context Member',
            location='Second Farm',
            preferred_start_date=timezone.now().date() + timedelta(days=4),
            status='pending',
        )
        UserNotification.objects.create(
            user=admin,
            notification_type='rental_package_new_request',
            message='Package one submitted.',
            related_object_id=first_package.pk,
        )
        UserNotification.objects.create(
            user=admin,
            notification_type='rental_package_new_request',
            message='Package two submitted.',
            related_object_id=second_package.pk,
        )

        request = self.factory.get('/machines/admin/rentals/')
        request.user = admin

        context = notifications_context(request)

        self.assertEqual(context['package_notification_count'], 2)

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


class RentalScheduleReminderCommandTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='rentalreminderadmin',
            email='rentalreminderadmin@example.com',
            password='testpassword123',
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='rentalremindermember',
            email='rentalremindermember@example.com',
            password='testpassword123',
            first_name='Rental',
            last_name='Member',
        )
        self.machine = Machine.objects.create(
            name='Reminder Tractor',
            machine_type='tractor_4wd',
            description='Reminder test machine',
            current_price='2500',
            rental_fee_per_day=2500,
            status='available',
        )
        self.rice_mill_machine = Machine.objects.create(
            name='Reminder Rice Mill',
            machine_type='rice_mill',
            description='Reminder rice mill machine',
            current_price='5',
            status='available',
        )
        self.dryer_machine = Machine.objects.create(
            name='Reminder Dryer',
            machine_type='flatbed_dryer',
            description='Reminder dryer machine',
            current_price='150',
            status='available',
        )

    def test_command_sends_day_before_rental_reminders_to_user_and_admin(self):
        start_date = timezone.localdate() + timedelta(days=1)
        rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=start_date,
            end_date=start_date + timedelta(days=1),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
        )

        call_command('send_rental_schedule_reminders', date=timezone.localdate().isoformat())

        self.assertTrue(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_starts_tomorrow',
                related_object_id=rental.pk,
            ).exists()
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.admin,
                notification_type='rental_starts_tomorrow_admin',
                related_object_id=rental.pk,
            ).exists()
        )

    def test_command_sends_day_before_reminders_for_all_booking_rent_types(self):
        target_date = timezone.localdate()
        next_day = target_date + timedelta(days=1)

        rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=next_day,
            end_date=next_day + timedelta(days=1),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
        )
        appointment = RiceMillAppointment.objects.create(
            user=self.member,
            machine=self.rice_mill_machine,
            appointment_date=next_day,
            sacks=2,
            rice_quantity=Decimal('100.00'),
            total_amount=Decimal('500.00'),
            status='approved',
            payment_method='face_to_face',
        )
        dryer_rental = DryerRental.objects.create(
            user=self.member,
            machine=self.dryer_machine,
            rental_date=next_day,
            rental_type='hourly',
            start_time=timezone.datetime.strptime('08:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            total_amount=Decimal('300.00'),
            status='approved',
            payment_method='face_to_face',
        )

        call_command('send_rental_schedule_reminders', date=target_date.isoformat())

        self.assertTrue(UserNotification.objects.filter(
            user=self.member,
            notification_type='rental_starts_tomorrow',
            related_object_id=rental.pk,
        ).exists())
        self.assertTrue(UserNotification.objects.filter(
            user=self.admin,
            notification_type='rental_starts_tomorrow_admin',
            related_object_id=rental.pk,
        ).exists())
        self.assertTrue(UserNotification.objects.filter(
            user=self.member,
            notification_type='appointment_starts_tomorrow',
            related_object_id=appointment.pk,
        ).exists())
        self.assertTrue(UserNotification.objects.filter(
            user=self.admin,
            notification_type='appointment_starts_tomorrow_admin',
            related_object_id=appointment.pk,
        ).exists())
        self.assertTrue(UserNotification.objects.filter(
            user=self.member,
            notification_type='dryer_starts_tomorrow',
            related_object_id=dryer_rental.pk,
        ).exists())
        self.assertTrue(UserNotification.objects.filter(
            user=self.admin,
            notification_type='dryer_starts_tomorrow_admin',
            related_object_id=dryer_rental.pk,
        ).exists())

    def test_command_sends_start_day_rental_reminders_to_user_and_admin(self):
        start_date = timezone.localdate()
        rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=start_date,
            end_date=start_date + timedelta(days=1),
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
        )

        call_command('send_rental_schedule_reminders', date=start_date.isoformat())

        user_notification = UserNotification.objects.get(
            user=self.member,
            notification_type='rental_starts_today',
            related_object_id=rental.pk,
        )
        admin_notification = UserNotification.objects.get(
            user=self.admin,
            notification_type='rental_starts_today_admin',
            related_object_id=rental.pk,
        )

        self.assertIn('active in your rental schedule', user_notification.message)
        self.assertEqual(
            user_notification.action_url,
            reverse('machines:rental_detail', kwargs={'pk': rental.pk}),
        )
        self.assertEqual(
            admin_notification.action_url,
            reverse('machines:admin_approve_rental', kwargs={'rental_id': rental.pk}),
        )

    def test_admin_booking_reminder_redirects_to_admin_review_pages(self):
        appointment_admin = UserNotification.objects.create(
            user=self.admin,
            notification_type='appointment_starts_tomorrow_admin',
            message='Rice mill booking tomorrow.',
            related_object_id=45,
        )
        dryer_admin = UserNotification.objects.create(
            user=self.admin,
            notification_type='dryer_starts_tomorrow_admin',
            message='Dryer booking tomorrow.',
            related_object_id=46,
        )

        self.assertEqual(
            appointment_admin.get_redirect_url(),
            reverse('machines:ricemill_appointment_approve', kwargs={'pk': 45}),
        )
        self.assertEqual(
            dryer_admin.get_redirect_url(),
            reverse('machines:dryer_rental_approve', kwargs={'pk': 46}),
        )

    def test_command_does_not_duplicate_same_day_rental_reminders(self):
        start_date = timezone.localdate()
        rental = Rental.objects.create(
            user=self.member,
            machine=self.machine,
            start_date=start_date,
            end_date=start_date,
            status='approved',
            workflow_state='approved',
            payment_type='cash',
            payment_status='pending',
        )

        call_command('send_rental_schedule_reminders', date=start_date.isoformat())
        call_command('send_rental_schedule_reminders', date=start_date.isoformat())

        self.assertEqual(
            UserNotification.objects.filter(
                user=self.member,
                notification_type='rental_starts_today',
                related_object_id=rental.pk,
            ).count(),
            1,
        )
        self.assertEqual(
            UserNotification.objects.filter(
                user=self.admin,
                notification_type='rental_starts_today_admin',
                related_object_id=rental.pk,
            ).count(),
            1,
        )
