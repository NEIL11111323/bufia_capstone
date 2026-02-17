from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from machines.models import Machine, Rental

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up permissions for BUFIA users'

    def handle(self, *args, **options):
        # Ensure machine permissions exist
        machine_content_type = ContentType.objects.get_for_model(Machine)
        rental_content_type = ContentType.objects.get_for_model(Rental)
        
        # Create can_rent_machine permission if it doesn't exist
        rent_perm, created = Permission.objects.get_or_create(
            codename='can_rent_machine',
            name='Can rent a machine',
            content_type=machine_content_type,
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created permission: {rent_perm}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Permission already exists: {rent_perm}'))
        
        # Add can_rent_machine permission to all users
        users = User.objects.all()
        for user in users:
            if not user.has_perm('machines.can_rent_machine'):
                user.user_permissions.add(rent_perm)
                self.stdout.write(self.style.SUCCESS(f'Added permission to {user.username}'))
        
        # Update is_verified field for all users
        for user in users:
            if user.is_president() or user.is_superuser:
                user.is_verified = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Set {user.username} as verified (admin/president)'))
            
        self.stdout.write(self.style.SUCCESS('Permission setup complete!')) 