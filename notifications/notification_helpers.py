"""
Enhanced notification helper functions with categorization, priority, and better formatting
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import UserNotification

User = get_user_model()


def create_notification(user, notification_type, message, **kwargs):
    """
    Create a notification with automatic categorization and priority

    Args:
        user: User object
        notification_type: Type of notification (e.g., 'rental_new_request')
        message: Notification message
        **kwargs: Additional fields (title, priority, category, related_object_id, action_url)
    """
    # Auto-detect category from notification_type if not provided
    if 'category' not in kwargs:
        if 'rental' in notification_type:
            kwargs['category'] = 'rental'
        elif 'operator' in notification_type:
            kwargs['category'] = 'operator'
        elif 'payment' in notification_type or 'settlement' in notification_type:
            kwargs['category'] = 'payment'
        elif 'maintenance' in notification_type or 'machine' in notification_type:
            kwargs['category'] = 'maintenance'
        elif 'irrigation' in notification_type:
            kwargs['category'] = 'irrigation'
        elif 'appointment' in notification_type or 'rice' in notification_type:
            kwargs['category'] = 'appointment'
        elif 'membership' in notification_type:
            kwargs['category'] = 'membership'
        else:
            kwargs['category'] = 'system'

    # Auto-detect priority if not provided
    if 'priority' not in kwargs:
        if 'urgent' in notification_type or 'critical' in notification_type or 'breakdown' in notification_type:
            kwargs['priority'] = 'critical'
        elif 'new_request' in notification_type or 'approved' in notification_type:
            kwargs['priority'] = 'important'
        elif 'update' in notification_type or 'completed' in notification_type:
            kwargs['priority'] = 'normal'
        else:
            kwargs['priority'] = 'low'

    # Generate title if not provided
    if 'title' not in kwargs:
        kwargs['title'] = generate_notification_title(notification_type, message)

    return UserNotification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        **kwargs
    )


def generate_notification_title(notification_type, message):
    """Generate a short title from notification type"""
    titles = {
        'rental_new_request': 'New Rental Request',
        'rental_approved': 'Rental Approved',
        'rental_rejected': 'Rental Rejected',
        'rental_completed': 'Rental Completed',
        'rental_update': 'Rental Update',
        'rental_pickup_overdue': 'Pickup Overdue',
        'rental_overdue': 'Rental Overdue',
        'rental_due_today': 'Return Due Today',
        'operator_job_assigned': 'New Job Assigned',
        'operator_job_updated': 'Job Status Updated',
        'operator_harvest_approved': 'Harvest Approved',
        'operator_harvest_rejected': 'Harvest Needs Revision',
        'operator_job_completed': 'Job Completed',
        'operator_urgent_job': 'Urgent Job',
        'operator_schedule_change': 'Schedule Changed',
        'payment_verified': 'Payment Verified',
        'payment_pending': 'Payment Pending',
        'settlement_completed': 'Settlement Completed',
        'settlement_waiting': 'Waiting for Delivery',
        'maintenance_scheduled': 'Maintenance Scheduled',
        'machine_breakdown': 'Machine Breakdown',
        'machine_available': 'Machine Available',
        'irrigation_approved': 'Irrigation Approved',
        'irrigation_completed': 'Irrigation Completed',
        'appointment_approved': 'Appointment Approved',
        'appointment_completed': 'Appointment Completed',
        'membership_approved': 'Membership Approved',
        'membership_required': 'Membership Required',
    }

    return titles.get(notification_type, 'Notification')


def notify_rental_request(rental, admin_users=None):
    """Notify admins about new rental request"""
    if admin_users is None:
        admin_users = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True, role='admin')

    title = f"New Rental Request from {rental.user.get_full_name()}"
    message = (
        f"{rental.user.get_full_name()} requested {rental.machine.name}. "
        f"Period: {rental.start_date.strftime('%b %d')} - {rental.end_date.strftime('%b %d, %Y')}. "
        f"Payment: {rental.get_payment_method_display()}."
    )

    for admin in admin_users:
        create_notification(
            user=admin,
            notification_type='rental_new_request',
            title=title,
            message=message,
            category='rental',
            priority='important',
            related_object_id=rental.id,
            action_url=f'/machines/admin/rental/{rental.id}/approve/'
        )


def notify_rental_approved(rental):
    """Notify user that rental was approved"""
    title = f"Rental Approved - {rental.machine.name}"
    message = (
        f"Your rental request for {rental.machine.name} has been approved! "
        f"Period: {rental.start_date.strftime('%b %d')} - {rental.end_date.strftime('%b %d, %Y')}. "
        f"Please proceed with payment if not yet completed."
    )

    create_notification(
        user=rental.user,
        notification_type='rental_approved',
        title=title,
        message=message,
        category='rental',
        priority='important',
        related_object_id=rental.id,
        action_url=f'/machines/rental/{rental.id}/'
    )


def notify_harvest_completed(rental, admin_users=None):
    """Notify admins about harvest completion"""
    if admin_users is None:
        admin_users = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True, role='admin')

    title = f"Harvest Completed - {rental.machine.name}"
    message = (
        f"Harvest completed for {rental.machine.name}. "
        f"Total: {rental.total_harvest_sacks} sacks. "
        f"BUFIA Share: {rental.organization_share_required} sacks. "
        f"Operator: {rental.assigned_operator.get_full_name() if rental.assigned_operator else 'N/A'}."
    )

    for admin in admin_users:
        create_notification(
            user=admin,
            notification_type='rental_update',
            title=title,
            message=message,
            category='payment',
            priority='important',
            related_object_id=rental.id,
            action_url=f'/machines/admin/rental/{rental.id}/approve/'
        )


def notify_settlement_completed(rental):
    """Notify relevant parties about settlement completion"""
    title = f"Settlement Completed - {rental.machine.name}"
    message = (
        f"Settlement completed for {rental.machine.name}. "
        f"Rice received: {rental.organization_share_received} sacks. "
        f"Member: {rental.user.get_full_name()}."
    )

    # Notify user
    create_notification(
        user=rental.user,
        notification_type='settlement_completed',
        title=title,
        message=message,
        category='payment',
        priority='normal',
        related_object_id=rental.id,
        action_url=f'/machines/rental/{rental.id}/'
    )

    # Notify operator if assigned
    if rental.assigned_operator:
        create_notification(
            user=rental.assigned_operator,
            notification_type='operator_payment_processed',
            title=title,
            message=message,
            category='payment',
            priority='normal',
            related_object_id=rental.id,
            action_url=f'/machines/operator/payments/in-kind/'
        )


def group_similar_notifications(notifications, time_window_minutes=60):
    """
    Group similar notifications that occurred within a time window

    Args:
        notifications: QuerySet of notifications
        time_window_minutes: Time window in minutes to group notifications

    Returns:
        List of grouped notifications with count
    """
    from datetime import timedelta
    from django.utils import timezone

    grouped = []
    processed_ids = set()

    for notif in notifications:
        if notif.id in processed_ids:
            continue

        # Find similar notifications within time window
        time_threshold = notif.timestamp - timedelta(minutes=time_window_minutes)
        similar = notifications.filter(
            notification_type=notif.notification_type,
            category=notif.category,
            timestamp__gte=time_threshold,
            timestamp__lte=notif.timestamp
        ).exclude(id__in=processed_ids)

        if similar.count() > 1:
            # Group them
            grouped.append({
                'notification': notif,
                'count': similar.count(),
                'is_grouped': True,
                'similar_ids': list(similar.values_list('id', flat=True))
            })
            processed_ids.update(similar.values_list('id', flat=True))
        else:
            # Single notification
            grouped.append({
                'notification': notif,
                'count': 1,
                'is_grouped': False,
                'similar_ids': [notif.id]
            })
            processed_ids.add(notif.id)

    return grouped


def mark_all_as_read(user):
    """Mark all notifications as read for a user"""
    return UserNotification.objects.filter(user=user, is_read=False).update(is_read=True)


def _rental_reminder_admin_users():
    return User.objects.filter(
        Q(is_superuser=True) | (Q(is_staff=True) & ~Q(role='operator'))
    ).distinct()


def _create_daily_rental_reminder(
    *,
    user,
    rental,
    notification_type,
    title,
    message,
    action_url,
    current_date,
):
    if UserNotification.objects.filter(
        user=user,
        notification_type=notification_type,
        related_object_id=rental.id,
        timestamp__date=current_date,
    ).exists():
        return False

    create_notification(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        category='rental',
        priority='important',
        related_object_id=rental.id,
        action_url=action_url,
    )
    return True


def _send_machine_rental_schedule_reminders(*, current_date, admin_users):
    from machines.models import Rental

    tomorrow = current_date + timedelta(days=1)
    rentals = Rental.objects.select_related('user', 'machine').filter(
        status='approved',
        start_date__in=[current_date, tomorrow],
    ).exclude(
        Q(status__in=['completed', 'cancelled', 'rejected']) |
        Q(workflow_state__in=['completed', 'cancelled'])
    )

    results = {
        'checked': rentals.count(),
        'user_notifications_created': 0,
        'admin_notifications_created': 0,
    }

    for rental in rentals:
        if rental.start_date == tomorrow:
            user_type = 'rental_starts_tomorrow'
            admin_type = 'rental_starts_tomorrow_admin'
            user_title = f'Rental Starts Tomorrow - {rental.machine.name}'
            admin_title = f'Rental Starts Tomorrow - {rental.customer_display_name}'
            user_message = (
                f'Your booking for {rental.machine.name} starts tomorrow, '
                f'{rental.start_date.strftime("%B %d, %Y")}. '
                f'Please be ready for your scheduled rental period.'
            )
            admin_message = (
                f'{rental.customer_display_name} has a booking for {rental.machine.name} '
                f'starting tomorrow, {rental.start_date.strftime("%B %d, %Y")}.'
            )
        else:
            user_type = 'rental_starts_today'
            admin_type = 'rental_starts_today_admin'
            user_title = f'Rental Starts Today - {rental.machine.name}'
            admin_title = f'Rental Starts Today - {rental.customer_display_name}'
            user_message = (
                f'Your booking for {rental.machine.name} is scheduled for today, '
                f'{rental.start_date.strftime("%B %d, %Y")}, and is now active in your rental schedule.'
            )
            admin_message = (
                f'{rental.customer_display_name} has a booking for {rental.machine.name} '
                f'starting today, {rental.start_date.strftime("%B %d, %Y")}. '
                f'Please monitor the active rental schedule.'
            )

        if _create_daily_rental_reminder(
            user=rental.user,
            rental=rental,
            notification_type=user_type,
            title=user_title,
            message=user_message,
            action_url=reverse('machines:rental_detail', kwargs={'pk': rental.pk}),
            current_date=current_date,
        ):
            results['user_notifications_created'] += 1

        for admin_user in admin_users:
            if _create_daily_rental_reminder(
                user=admin_user,
                rental=rental,
                notification_type=admin_type,
                title=admin_title,
                message=admin_message,
                action_url=reverse('machines:admin_approve_rental', kwargs={'rental_id': rental.pk}),
                current_date=current_date,
            ):
                results['admin_notifications_created'] += 1

    return results


def _send_rice_mill_schedule_reminders(*, current_date, admin_users):
    from machines.models import RiceMillAppointment

    tomorrow = current_date + timedelta(days=1)
    appointments = RiceMillAppointment.objects.select_related('user', 'machine').filter(
        appointment_date__in=[current_date, tomorrow],
        status__in=['approved', 'paid', 'confirmed', 'ongoing'],
    ).exclude(status__in=['rejected', 'cancelled', 'completed'])

    results = {
        'checked': appointments.count(),
        'user_notifications_created': 0,
        'admin_notifications_created': 0,
    }

    for appointment in appointments:
        if appointment.appointment_date == tomorrow:
            user_type = 'appointment_starts_tomorrow'
            admin_type = 'appointment_starts_tomorrow_admin'
            user_title = f'Rice Mill Booking Tomorrow - {appointment.machine.name}'
            admin_title = f'Rice Mill Booking Tomorrow - {appointment.customer_display_name}'
            user_message = (
                f'Your rice mill booking for {appointment.machine.name} is scheduled for tomorrow, '
                f'{appointment.appointment_date.strftime("%B %d, %Y")}. '
                f'Please be ready during daytime operating hours.'
            )
            admin_message = (
                f'{appointment.customer_display_name} has a rice mill booking for {appointment.machine.name} '
                f'tomorrow, {appointment.appointment_date.strftime("%B %d, %Y")}.'
            )
        else:
            user_type = 'appointment_starts_today'
            admin_type = 'appointment_starts_today_admin'
            user_title = f'Rice Mill Booking Today - {appointment.machine.name}'
            admin_title = f'Rice Mill Booking Today - {appointment.customer_display_name}'
            user_message = (
                f'Your rice mill booking for {appointment.machine.name} is scheduled for today, '
                f'{appointment.appointment_date.strftime("%B %d, %Y")}. '
                f'Please proceed during daytime operating hours.'
            )
            admin_message = (
                f'{appointment.customer_display_name} has a rice mill booking for {appointment.machine.name} '
                f'starting today, {appointment.appointment_date.strftime("%B %d, %Y")}.'
            )

        if _create_daily_rental_reminder(
            user=appointment.user,
            rental=appointment,
            notification_type=user_type,
            title=user_title,
            message=user_message,
            action_url=reverse('machines:ricemill_appointment_detail', kwargs={'pk': appointment.pk}),
            current_date=current_date,
        ):
            results['user_notifications_created'] += 1

        for admin_user in admin_users:
            if _create_daily_rental_reminder(
                user=admin_user,
                rental=appointment,
                notification_type=admin_type,
                title=admin_title,
                message=admin_message,
                action_url=reverse('machines:ricemill_appointment_approve', kwargs={'pk': appointment.pk}),
                current_date=current_date,
            ):
                results['admin_notifications_created'] += 1

    return results


def _send_dryer_schedule_reminders(*, current_date, admin_users):
    from machines.models import DryerRental

    tomorrow = current_date + timedelta(days=1)
    dryer_rentals = DryerRental.objects.select_related('user', 'machine').filter(
        rental_date__in=[current_date, tomorrow],
        status__in=['approved', 'paid', 'confirmed', 'in_progress', 'ongoing'],
    ).exclude(status__in=['rejected', 'cancelled', 'completed'])

    results = {
        'checked': dryer_rentals.count(),
        'user_notifications_created': 0,
        'admin_notifications_created': 0,
    }

    for dryer_rental in dryer_rentals:
        if dryer_rental.rental_date == tomorrow:
            user_type = 'dryer_starts_tomorrow'
            admin_type = 'dryer_starts_tomorrow_admin'
            user_title = f'Dryer Booking Tomorrow - {dryer_rental.machine.name}'
            admin_title = f'Dryer Booking Tomorrow - {dryer_rental.customer_display_name}'
            user_message = (
                f'Your dryer booking for {dryer_rental.machine.name} is scheduled for tomorrow, '
                f'{dryer_rental.rental_date.strftime("%B %d, %Y")}.'
            )
            admin_message = (
                f'{dryer_rental.customer_display_name} has a dryer booking for {dryer_rental.machine.name} '
                f'tomorrow, {dryer_rental.rental_date.strftime("%B %d, %Y")}.'
            )
        else:
            user_type = 'dryer_starts_today'
            admin_type = 'dryer_starts_today_admin'
            user_title = f'Dryer Booking Today - {dryer_rental.machine.name}'
            admin_title = f'Dryer Booking Today - {dryer_rental.customer_display_name}'
            user_message = (
                f'Your dryer booking for {dryer_rental.machine.name} is scheduled for today, '
                f'{dryer_rental.rental_date.strftime("%B %d, %Y")}.'
            )
            admin_message = (
                f'{dryer_rental.customer_display_name} has a dryer booking for {dryer_rental.machine.name} '
                f'starting today, {dryer_rental.rental_date.strftime("%B %d, %Y")}.'
            )

        if _create_daily_rental_reminder(
            user=dryer_rental.user,
            rental=dryer_rental,
            notification_type=user_type,
            title=user_title,
            message=user_message,
            action_url=reverse('machines:dryer_rental_detail', kwargs={'pk': dryer_rental.pk}),
            current_date=current_date,
        ):
            results['user_notifications_created'] += 1

        for admin_user in admin_users:
            if _create_daily_rental_reminder(
                user=admin_user,
                rental=dryer_rental,
                notification_type=admin_type,
                title=admin_title,
                message=admin_message,
                action_url=reverse('machines:dryer_rental_approve', kwargs={'pk': dryer_rental.pk}),
                current_date=current_date,
            ):
                results['admin_notifications_created'] += 1

    return results


def send_rental_schedule_reminders(*, current_date=None):
    """
    Send rental reminder notifications to both the renter and admins.

    Rules:
    - Notify one day before the rental start date.
    - Notify again on the rental start date.
    - Only active approved rentals are included.
    - Re-running on the same day will not create duplicates.
    """
    current_date = current_date or timezone.localdate()

    admin_users = list(_rental_reminder_admin_users())
    results = {
        'current_date': current_date,
        'rentals_checked': 0,
        'user_notifications_created': 0,
        'admin_notifications_created': 0,
    }

    for sender in (
        _send_machine_rental_schedule_reminders,
        _send_rice_mill_schedule_reminders,
        _send_dryer_schedule_reminders,
    ):
        sender_result = sender(current_date=current_date, admin_users=admin_users)
        results['rentals_checked'] += sender_result['checked']
        results['user_notifications_created'] += sender_result['user_notifications_created']
        results['admin_notifications_created'] += sender_result['admin_notifications_created']

    return results


def get_notification_summary(user):
    """Get notification summary for a user"""
    notifications = UserNotification.objects.filter(user=user)

    return {
        'total': notifications.count(),
        'unread': notifications.filter(is_read=False).count(),
        'by_category': {
            'rental': notifications.filter(category='rental').count(),
            'operator': notifications.filter(category='operator').count(),
            'payment': notifications.filter(category='payment').count(),
            'maintenance': notifications.filter(category='maintenance').count(),
            'system': notifications.filter(category='system').count(),
        },
        'by_priority': {
            'critical': notifications.filter(priority='critical', is_read=False).count(),
            'important': notifications.filter(priority='important', is_read=False).count(),
            'normal': notifications.filter(priority='normal', is_read=False).count(),
            'low': notifications.filter(priority='low', is_read=False).count(),
        }
    }
