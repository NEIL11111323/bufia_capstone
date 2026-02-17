from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model
from notifications.models import UserNotification
import datetime

User = get_user_model()


@receiver(user_signed_up)
def create_membership_notification(sender, request, user, **kwargs):
    """
    Create a notification for new users to complete their membership application.
    This is triggered when a user signs up via django-allauth.
    """
    # Check if user has already submitted membership form
    if not user.membership_form_submitted:
        UserNotification.objects.create(
            user=user,
            notification_type='membership_required',
            message=(
                'Welcome to BUFIA! Please complete your membership application '
                'to access all features. Click here to submit your application.'
            ),
            is_read=False
        )


@receiver(pre_save, sender=User)
def track_verification_change(sender, instance, **kwargs):
    """
    Track when a user's verification status changes from False to True.
    Store the previous state so we can detect changes in post_save.
    """
    if instance.pk:  # Only for existing users
        try:
            old_instance = User.objects.get(pk=instance.pk)
            instance._old_is_verified = old_instance.is_verified
        except User.DoesNotExist:
            instance._old_is_verified = False
    else:
        instance._old_is_verified = False


@receiver(post_save, sender=User)
def check_membership_status(sender, instance, created, **kwargs):
    """
    Check if existing users need to complete their membership application.
    Also send notification when membership is approved.
    This runs whenever a user is saved.
    """
    if created:
        # For newly created users (not through allauth signup)
        if not instance.membership_form_submitted and not instance.is_superuser:
            # Check if notification already exists
            existing_notification = UserNotification.objects.filter(
                user=instance,
                notification_type='membership_required',
                is_read=False
            ).exists()
            
            if not existing_notification:
                UserNotification.objects.create(
                    user=instance,
                    notification_type='membership_required',
                    message=(
                        'Welcome to BUFIA! Please complete your membership application '
                        'to access all features. Click here to submit your application.'
                    ),
                    is_read=False
                )
    else:
        # For existing users - check if verification status changed
        old_is_verified = getattr(instance, '_old_is_verified', False)
        
        # If user was just verified (changed from False to True)
        if not old_is_verified and instance.is_verified:
            # Mark any pending membership notifications as read
            UserNotification.objects.filter(
                user=instance,
                notification_type='membership_required',
                is_read=False
            ).update(is_read=True)
            
            # Check if approval notification already exists
            existing_approval = UserNotification.objects.filter(
                user=instance,
                notification_type='membership_approved'
            ).exists()
            
            if not existing_approval:
                # Create approval notification
                approval_date = instance.membership_approved_date or datetime.date.today()
                UserNotification.objects.create(
                    user=instance,
                    notification_type='membership_approved',
                    message=(
                        f'Congratulations! Your membership application has been approved on '
                        f'{approval_date.strftime("%B %d, %Y")}. You now have full access to all BUFIA services.'
                    ),
                    is_read=False
                )
