from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from machines.models import Machine

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix rental permissions for all users'

    def handle(self, *args, **options):
        # Get can_rent_machine permission
        machine_content_type = ContentType.objects.get_for_model(Machine)
        rent_perm, created = Permission.objects.get_or_create(
            codename='can_rent_machine',
            name='Can rent a machine',
            content_type=machine_content_type,
        )
        
        # Add permission to all users who don't have it
        users = User.objects.all()
        updated_count = 0
        
        for user in users:
            if not user.has_perm('machines.can_rent_machine'):
                user.user_permissions.add(rent_perm)
                updated_count += 1
                self.stdout.write(f'Added rent permission to {user.username}')
        
        # Ensure verified users can rent machines
        for user in User.objects.filter(is_verified=True):
            if not user.has_perm('machines.can_rent_machine'):
                user.user_permissions.add(rent_perm)
                updated_count += 1
                self.stdout.write(f'Added rent permission to verified user {user.username}')
        
        # Add group permissions too
        try:
            regular_users_group = Group.objects.get(name='RegularUsers')
            if rent_perm not in regular_users_group.permissions.all():
                regular_users_group.permissions.add(rent_perm)
                self.stdout.write('Added rent permission to RegularUsers group')
        except Group.DoesNotExist:
            self.stdout.write('RegularUsers group not found')
            
        self.stdout.write(self.style.SUCCESS(f'Updated permissions for {updated_count} users!')) 