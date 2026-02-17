from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Assign users to appropriate groups in BUFIA Management System'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to assign')
        parser.add_argument('--group', type=str, help='Group to assign the user to (Administrators, Staff, RegularUsers, RiceFarmers)')
        parser.add_argument('--all-regular', action='store_true', help='Assign all users to RegularUsers group')
        
    def handle(self, *args, **kwargs):
        username = kwargs.get('username')
        group_name = kwargs.get('group')
        all_regular = kwargs.get('all_regular')
        
        # Validate groups
        valid_groups = ['Administrators', 'Staff', 'RegularUsers', 'RiceFarmers']
        
        if all_regular:
            # Get regular users group
            try:
                regular_group = Group.objects.get(name='RegularUsers')
                
                # Get all users that are not in any group
                users_without_group = User.objects.filter(groups__isnull=True)
                
                if not users_without_group.exists():
                    self.stdout.write(self.style.WARNING('No users found without a group assignment'))
                    return
                
                count = 0
                for user in users_without_group:
                    # Skip superuser
                    if user.is_superuser:
                        continue
                        
                    user.groups.add(regular_group)
                    count += 1
                
                self.stdout.write(self.style.SUCCESS(f'Successfully assigned {count} users to the RegularUsers group'))
                return
                
            except Group.DoesNotExist:
                self.stdout.write(self.style.ERROR('RegularUsers group does not exist'))
                return
        
        if not username or not group_name:
            self.stdout.write(self.style.ERROR('Both --username and --group arguments are required'))
            return
            
        if group_name not in valid_groups:
            self.stdout.write(self.style.ERROR(f'Invalid group: {group_name}. Valid groups are: {", ".join(valid_groups)}'))
            return
            
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} does not exist'))
            return
            
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Group {group_name} does not exist'))
            return
            
        # Remove from all other groups first
        user.groups.clear()
        
        # Add to the specified group
        user.groups.add(group)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned user {username} to group {group_name}')) 