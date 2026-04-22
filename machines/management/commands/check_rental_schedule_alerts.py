from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from machines.models import Rental
from notifications.models import UserNotification
from notifications.notification_helpers import create_notification


User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin alerts for rentals that were not picked up on time or are overdue for return.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which alerts would be created without saving notifications.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        today = timezone.localdate()
        admin_users = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).distinct()

        pickup_candidates = Rental.objects.select_related('machine', 'user').filter(
            scheduled_pickup_at__isnull=False,
            actual_pickup_at__isnull=True,
            scheduled_pickup_at__lt=now,
        ).exclude(
            Q(status__in=['completed', 'rejected', 'cancelled']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        )

        overdue_candidates = Rental.objects.select_related('machine', 'user').filter(
            scheduled_return_at__isnull=False,
            actual_return_at__isnull=True,
            scheduled_return_at__lt=now,
        ).exclude(
            Q(status__in=['completed', 'rejected', 'cancelled']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        )

        due_today_candidates = Rental.objects.select_related('machine', 'user').filter(
            scheduled_return_at__isnull=False,
            actual_return_at__isnull=True,
            scheduled_return_at__date=today,
            scheduled_return_at__gte=now,
        ).exclude(
            Q(status__in=['completed', 'rejected', 'cancelled']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - notifications will not be saved'))

        created_pickup = self._notify_admins(
            admin_users=admin_users,
            rentals=pickup_candidates,
            notification_type='rental_pickup_overdue',
            title_builder=lambda rental: f'Pickup overdue - {rental.machine.name}',
            message_builder=lambda rental: (
                f'{rental.customer_display_name} has not picked up {rental.machine.name} yet. '
                f'Scheduled pickup was {timezone.localtime(rental.scheduled_pickup_at).strftime("%b %d, %Y %I:%M %p")}.'
            ),
            dry_run=dry_run,
        )

        created_overdue = self._notify_admins(
            admin_users=admin_users,
            rentals=overdue_candidates,
            notification_type='rental_overdue',
            title_builder=lambda rental: f'Return overdue - {rental.machine.name}',
            message_builder=lambda rental: (
                f'{rental.machine.name} is overdue for return. '
                f'{rental.customer_display_name} was due back on {timezone.localtime(rental.scheduled_return_at).strftime("%b %d, %Y %I:%M %p")}.'
            ),
            dry_run=dry_run,
        )

        created_due_today = self._notify_admins(
            admin_users=admin_users,
            rentals=due_today_candidates,
            notification_type='rental_due_today',
            title_builder=lambda rental: f'Return due today - {rental.machine.name}',
            message_builder=lambda rental: (
                f'{rental.machine.name} is due back today at '
                f'{timezone.localtime(rental.scheduled_return_at).strftime("%I:%M %p")}.'
            ),
            dry_run=dry_run,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed schedule alerts. '
                f'Pickup overdue: {created_pickup}, overdue returns: {created_overdue}, due today: {created_due_today}.'
            )
        )

    def _notify_admins(
        self,
        *,
        admin_users,
        rentals,
        notification_type,
        title_builder,
        message_builder,
        dry_run,
    ):
        created = 0

        for rental in rentals:
            for admin in admin_users:
                already_exists = UserNotification.objects.filter(
                    user=admin,
                    notification_type=notification_type,
                    related_object_id=rental.id,
                ).exists()
                if already_exists:
                    continue

                if dry_run:
                    self.stdout.write(
                        f'Would notify {admin.username}: {notification_type} for rental #{rental.id}'
                    )
                    created += 1
                    continue

                create_notification(
                    user=admin,
                    notification_type=notification_type,
                    title=title_builder(rental),
                    message=message_builder(rental),
                    category='rental',
                    priority='critical' if notification_type != 'rental_due_today' else 'important',
                    related_object_id=rental.id,
                )
                created += 1

        return created
