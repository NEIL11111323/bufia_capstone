"""
Management command to delete notifications that reference deleted objects
"""
from django.core.management.base import BaseCommand
from notifications.models import UserNotification


class Command(BaseCommand):
    help = 'Delete all notifications that reference deleted objects (orphaned notifications)'

    def handle(self, *args, **options):
        deleted_count = 0
        
        # Get all notifications
        all_notifications = UserNotification.objects.all()
        total_count = all_notifications.count()
        
        self.stdout.write(f"Checking {total_count} notifications...")
        
        for notification in all_notifications:
            should_delete = False
            
            # Check if notification has a related object that no longer exists
            if notification.related_object_id:
                # Try to access the related object
                try:
                    # This will raise an exception if the related object doesn't exist
                    if notification.notification_type in ['rental_approved', 'rental_rejected', 'rental_cancelled']:
                        from machines.models import Rental
                        try:
                            Rental.objects.get(id=notification.related_object_id)
                        except Rental.DoesNotExist:
                            should_delete = True
                            
                    elif notification.notification_type in ['irrigation_approved', 'irrigation_rejected']:
                        from irrigation.models import WaterIrrigationRequest
                        try:
                            WaterIrrigationRequest.objects.get(id=notification.related_object_id)
                        except WaterIrrigationRequest.DoesNotExist:
                            should_delete = True
                            
                    elif notification.notification_type in ['appointment_confirmed', 'appointment_cancelled']:
                        from machines.models import RiceMillAppointment
                        try:
                            RiceMillAppointment.objects.get(id=notification.related_object_id)
                        except RiceMillAppointment.DoesNotExist:
                            should_delete = True
                            
                    elif notification.notification_type in ['maintenance_scheduled', 'maintenance_completed']:
                        from machines.models import Maintenance
                        try:
                            Maintenance.objects.get(id=notification.related_object_id)
                        except Maintenance.DoesNotExist:
                            should_delete = True
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Error checking notification {notification.id}: {str(e)}"
                        )
                    )
            
            if should_delete:
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleting orphaned notification: {notification.id} - {notification.message[:50]}..."
                    )
                )
                notification.delete()
                deleted_count += 1
        
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {deleted_count} orphaned notification(s)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nNo orphaned notifications found. Database is clean!"
                )
            )
