from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test users and assigns them to appropriate groups'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating test users...')
        
        with transaction.atomic():
            # Create groups if they don't exist (in case setup_groups wasn't run)
            admin_group, _ = Group.objects.get_or_create(name='Administrators')
            regular_group, _ = Group.objects.get_or_create(name='RegularUsers')
            rice_farmers_group, _ = Group.objects.get_or_create(name='RiceFarmers')
            
            # Create regular user
            regular_user, created = User.objects.get_or_create(
                username='regular_user',
                defaults={
                    'email': 'regular@bufia.example',
                    'is_active': True,
                }
            )
            
            if created:
                regular_user.set_password('regular123')
                regular_user.save()
                self.stdout.write(f'Created regular user: {regular_user.username}')
            else:
                self.stdout.write(f'Regular user already exists: {regular_user.username}')
            
            # Add to regular group
            regular_user.groups.add(regular_group)
            self.stdout.write(f'Added {regular_user.username} to RegularUsers group')
            
            # Create rice farmer user
            rice_user, created = User.objects.get_or_create(
                username='rice_farmer',
                defaults={
                    'email': 'rice@bufia.example',
                    'is_active': True,
                }
            )
            
            if created:
                rice_user.set_password('rice123')
                rice_user.save()
                self.stdout.write(f'Created rice farmer user: {rice_user.username}')
            else:
                self.stdout.write(f'Rice farmer user already exists: {rice_user.username}')
            
            # Add to rice farmers group
            rice_user.groups.add(rice_farmers_group)
            self.stdout.write(f'Added {rice_user.username} to RiceFarmers group')
            
            # Create admin user
            admin_user, created = User.objects.get_or_create(
                username='admin_user',
                defaults={
                    'email': 'admin@bufia.example',
                    'is_active': True,
                    'is_staff': True,
                }
            )
            
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(f'Created admin user: {admin_user.username}')
            else:
                self.stdout.write(f'Admin user already exists: {admin_user.username}')
            
            # Add to admin group
            admin_user.groups.add(admin_group)
            self.stdout.write(f'Added {admin_user.username} to Administrators group')
            
            self.stdout.write(self.style.SUCCESS('Successfully created test users')) 