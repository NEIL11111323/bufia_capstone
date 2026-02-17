from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Update all users to ensure their permissions match their roles'

    def handle(self, *args, **options):
        self.stdout.write('Updating user permissions...')
        
        # Make sure groups exist
        admin_group, _ = Group.objects.get_or_create(name='Administrators')
        regular_group, _ = Group.objects.get_or_create(name='RegularUsers')
        
        # Update all users
        updated_count = 0
        for user in User.objects.all():
            updated = False
            
            # Update is_staff and is_superuser based on role
            if user.role == User.PRESIDENT:
                if not user.is_staff:
                    user.is_staff = True
                    updated = True
                # Presidents are not superusers by default
                
            elif user.role == User.SUPERUSER:
                if not user.is_staff or not user.is_superuser:
                    user.is_staff = True
                    user.is_superuser = True
                    updated = True
            
            # Update group membership
            current_groups = list(user.groups.all())
            
            if user.role in [User.PRESIDENT, User.SUPERUSER]:
                # Should be in admin group
                if admin_group not in current_groups:
                    user.groups.clear()
                    user.groups.add(admin_group)
                    updated = True
            else:
                # Should be in regular group
                if regular_group not in current_groups:
                    user.groups.clear()
                    user.groups.add(regular_group)
                    updated = True
            
            if updated:
                user.save()
                updated_count += 1
                self.stdout.write(f'Updated user: {user.username}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} users')) 