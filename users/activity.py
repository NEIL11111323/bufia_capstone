from django.db.models import Q

from .models import ActivityLog, CustomUser


PROFILE_ICON_MAP = {
    ActivityLog.TYPE_REGISTER: 'fas fa-user-plus',
    ActivityLog.TYPE_SUBMIT: 'fas fa-file-circle-plus',
    ActivityLog.TYPE_APPROVE: 'fas fa-circle-check',
    ActivityLog.TYPE_REJECT: 'fas fa-circle-xmark',
    ActivityLog.TYPE_PAYMENT: 'fas fa-wallet',
    ActivityLog.TYPE_SCHEDULE: 'fas fa-calendar-check',
    ActivityLog.TYPE_MACHINE: 'fas fa-tractor',
    ActivityLog.TYPE_BILLING: 'fas fa-file-invoice-dollar',
    ActivityLog.TYPE_UPDATE: 'fas fa-pen-to-square',
    ActivityLog.TYPE_OTHER: 'fas fa-bolt',
}


def is_activity_admin(user):
    return bool(
        user
        and (
            user.is_superuser
            or user.is_staff
            or getattr(user, 'role', '') == CustomUser.SUPERUSER
        )
    )


def log_activity(
    *,
    activity_type,
    title,
    description='',
    actor=None,
    subject_user=None,
    visibility=ActivityLog.VISIBILITY_BOTH,
    related_object=None,
    related_model='',
    related_object_id='',
    metadata=None,
    created_at=None,
):
    if related_object is not None:
        related_model = f'{related_object._meta.app_label}.{related_object.__class__.__name__}'
        related_object_id = str(related_object.pk or '')

    create_kwargs = dict(
        actor=actor,
        subject_user=subject_user,
        activity_type=activity_type,
        visibility=visibility,
        title=title,
        description=description,
        related_model=related_model or '',
        related_object_id=str(related_object_id or ''),
        metadata=metadata or None,
    )
    if created_at is not None:
        create_kwargs['created_at'] = created_at

    return ActivityLog.objects.create(**create_kwargs)


def get_recent_activities_for_user(user, limit=10):
    queryset = ActivityLog.objects.select_related('actor', 'subject_user').order_by('-created_at', '-id')
    if is_activity_admin(user):
        return list(queryset[:limit])

    return list(
        queryset.filter(
            visibility__in=[ActivityLog.VISIBILITY_USER, ActivityLog.VISIBILITY_BOTH]
        ).filter(
            Q(subject_user=user) | Q(actor=user)
        )[:limit]
    )


def serialize_activity_for_profile(activity):
    return {
        'type': activity.activity_type,
        'icon': PROFILE_ICON_MAP.get(activity.activity_type, PROFILE_ICON_MAP[ActivityLog.TYPE_OTHER]),
        'title': activity.title,
        'description': activity.description,
        'timestamp': activity.created_at,
    }


def build_profile_activity_feed(user, limit=10):
    return [serialize_activity_for_profile(item) for item in get_recent_activities_for_user(user, limit=limit)]
