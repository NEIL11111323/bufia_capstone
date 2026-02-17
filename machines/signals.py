from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Rental, RiceMillAppointment
from notifications.models import UserNotification

User = get_user_model()


@receiver(pre_save, sender=Rental)
def track_rental_status_change(sender, instance, **kwargs):
    """Track status changes for rentals before saving"""
    if instance.pk:
        try:
            old_instance = Rental.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Rental.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Rental)
def notify_rental_status_change(sender, instance, created, **kwargs):
    """Send notification when rental status changes"""
    if created:
        # Notify user that rental request was submitted
        UserNotification.objects.create(
            user=instance.user,
            notification_type='rental_submitted',
            message=f'Your rental request for {instance.machine.name} from {instance.start_date.strftime("%B %d, %Y")} to {instance.end_date.strftime("%B %d, %Y")} has been submitted and is pending approval.',
            related_object_id=instance.id
        )
        
        # Notify all admins about new rental request
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            UserNotification.objects.create(
                user=admin,
                notification_type='rental_new_request',
                message=f'New rental request from {instance.user.get_full_name()} for {instance.machine.name} from {instance.start_date.strftime("%B %d, %Y")} to {instance.end_date.strftime("%B %d, %Y")}.',
                related_object_id=instance.id
            )
    else:
        # Check if status changed
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            # Notify user about status change
            if instance.status == 'approved':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='rental_approved',
                    message=f'Your rental request for {instance.machine.name} from {instance.start_date.strftime("%B %d, %Y")} to {instance.end_date.strftime("%B %d, %Y")} has been approved!',
                    related_object_id=instance.id
                )
            elif instance.status == 'rejected':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='rental_rejected',
                    message=f'Your rental request for {instance.machine.name} from {instance.start_date.strftime("%B %d, %Y")} to {instance.end_date.strftime("%B %d, %Y")} has been rejected.',
                    related_object_id=instance.id
                )
            elif instance.status == 'completed':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='rental_completed',
                    message=f'Your rental of {instance.machine.name} has been marked as completed. Thank you for using our services!',
                    related_object_id=instance.id
                )
            elif instance.status == 'cancelled':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='rental_cancelled',
                    message=f'Your rental request for {instance.machine.name} from {instance.start_date.strftime("%B %d, %Y")} to {instance.end_date.strftime("%B %d, %Y")} has been cancelled.',
                    related_object_id=instance.id
                )


@receiver(pre_save, sender=RiceMillAppointment)
def track_appointment_status_change(sender, instance, **kwargs):
    """Track status changes for rice mill appointments before saving"""
    if instance.pk:
        try:
            old_instance = RiceMillAppointment.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except RiceMillAppointment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=RiceMillAppointment)
def notify_appointment_status_change(sender, instance, created, **kwargs):
    """Send notification when rice mill appointment status changes"""
    if created:
        # Notify user that appointment was submitted
        UserNotification.objects.create(
            user=instance.user,
            notification_type='appointment_submitted',
            message=f'Your rice mill appointment for {instance.machine.name} on {instance.appointment_date.strftime("%B %d, %Y")} ({instance.get_time_slot_display()}) has been submitted and is pending approval. Reference: {instance.reference_number}',
            related_object_id=instance.id
        )
        
        # Notify all admins about new appointment
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            UserNotification.objects.create(
                user=admin,
                notification_type='appointment_new_request',
                message=f'New rice mill appointment from {instance.user.get_full_name()} for {instance.machine.name} on {instance.appointment_date.strftime("%B %d, %Y")} ({instance.get_time_slot_display()}). Quantity: {instance.rice_quantity} kg. Reference: {instance.reference_number}',
                related_object_id=instance.id
            )
    else:
        # Check if status changed
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            # Notify user about status change
            if instance.status == 'approved':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='appointment_approved',
                    message=f'Your rice mill appointment for {instance.machine.name} on {instance.appointment_date.strftime("%B %d, %Y")} ({instance.get_time_slot_display()}) has been approved! Reference: {instance.reference_number}',
                    related_object_id=instance.id
                )
            elif instance.status == 'rejected':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='appointment_rejected',
                    message=f'Your rice mill appointment for {instance.machine.name} on {instance.appointment_date.strftime("%B %d, %Y")} ({instance.get_time_slot_display()}) has been rejected. Reference: {instance.reference_number}',
                    related_object_id=instance.id
                )
            elif instance.status == 'completed':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='appointment_completed',
                    message=f'Your rice mill appointment for {instance.machine.name} has been marked as completed. Thank you for using our services! Reference: {instance.reference_number}',
                    related_object_id=instance.id
                )
            elif instance.status == 'cancelled':
                UserNotification.objects.create(
                    user=instance.user,
                    notification_type='appointment_cancelled',
                    message=f'Your rice mill appointment for {instance.machine.name} on {instance.appointment_date.strftime("%B %d, %Y")} ({instance.get_time_slot_display()}) has been cancelled. Reference: {instance.reference_number}',
                    related_object_id=instance.id
                )
