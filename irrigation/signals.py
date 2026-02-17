from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import WaterIrrigationRequest
from notifications.models import UserNotification

User = get_user_model()


@receiver(pre_save, sender=WaterIrrigationRequest)
def track_irrigation_status_change(sender, instance, **kwargs):
    """Track status changes for irrigation requests before saving"""
    if instance.pk:
        try:
            old_instance = WaterIrrigationRequest.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except WaterIrrigationRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=WaterIrrigationRequest)
def notify_irrigation_status_change(sender, instance, created, **kwargs):
    """Send notification when irrigation request status changes"""
    if created:
        # Notify user that irrigation request was submitted
        UserNotification.objects.create(
            user=instance.farmer,
            notification_type='irrigation_submitted',
            message=f'Your irrigation request for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")} has been submitted and is pending approval. Sector: {instance.sector.name if instance.sector else "N/A"}',
            related_object_id=instance.id
        )
        
        # Notify admins and water tenders in the same sector
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            UserNotification.objects.create(
                user=admin,
                notification_type='irrigation_new_request',
                message=f'New irrigation request from {instance.farmer.get_full_name()} for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")}. Sector: {instance.sector.name if instance.sector else "N/A"}, Crop: {instance.crop_type}',
                related_object_id=instance.id
            )
        
        # Notify water tenders in the same sector
        if instance.sector:
            water_tenders = instance.sector.water_tenders.filter(is_active=True)
            for water_tender in water_tenders:
                UserNotification.objects.create(
                    user=water_tender,
                    notification_type='irrigation_new_request',
                    message=f'New irrigation request in your sector ({instance.sector.name}) from {instance.farmer.get_full_name()} for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")}. Crop: {instance.crop_type}',
                    related_object_id=instance.id
                )
    else:
        # Check if status changed
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            # Notify user about status change
            if instance.status == 'approved':
                UserNotification.objects.create(
                    user=instance.farmer,
                    notification_type='irrigation_approved',
                    message=f'Your irrigation request for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")} has been approved! Sector: {instance.sector.name if instance.sector else "N/A"}',
                    related_object_id=instance.id
                )
            elif instance.status == 'rejected':
                rejection_reason = f' Reason: {instance.status_notes}' if instance.status_notes else ''
                UserNotification.objects.create(
                    user=instance.farmer,
                    notification_type='irrigation_rejected',
                    message=f'Your irrigation request for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")} has been rejected.{rejection_reason}',
                    related_object_id=instance.id
                )
            elif instance.status == 'completed':
                UserNotification.objects.create(
                    user=instance.farmer,
                    notification_type='irrigation_completed',
                    message=f'Your irrigation request for {instance.area_size} hectares has been marked as completed. Thank you for using our irrigation services!',
                    related_object_id=instance.id
                )
            elif instance.status == 'cancelled':
                UserNotification.objects.create(
                    user=instance.farmer,
                    notification_type='irrigation_cancelled',
                    message=f'Your irrigation request for {instance.area_size} hectares on {instance.requested_date.strftime("%B %d, %Y")} has been cancelled.',
                    related_object_id=instance.id
                )
