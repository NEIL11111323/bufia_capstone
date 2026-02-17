from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from machines.models import Machine, Rental


class Command(BaseCommand):
    help = 'Set up user groups and permissions for BUFIA Management System'

    def handle(self, *args, **kwargs):
        # Create groups if they don't exist
        admin_group, created = Group.objects.get_or_create(name='Administrators')
        staff_group, created = Group.objects.get_or_create(name='Staff')
        user_group, created = Group.objects.get_or_create(name='RegularUsers')
        farmer_group, created = Group.objects.get_or_create(name='RiceFarmers')
        
        # Get content types
        machine_ct = ContentType.objects.get_for_model(Machine)
        rental_ct = ContentType.objects.get_for_model(Rental)
        
        # Get or create custom permissions
        can_rent_machine, created = Permission.objects.get_or_create(
            codename='can_rent_machine',
            name='Can rent a machine',
            content_type=machine_ct,
        )
        
        can_schedule_rent, created = Permission.objects.get_or_create(
            codename='can_schedule_rent',
            name='Can schedule a machine rental',
            content_type=machine_ct,
        )
        
        can_view_all_rentals, created = Permission.objects.get_or_create(
            codename='can_view_all_rentals',
            name='Can view all rental records',
            content_type=rental_ct,
        )
        
        can_approve_rentals, created = Permission.objects.get_or_create(
            codename='can_approve_rentals',
            name='Can approve rental requests',
            content_type=rental_ct,
        )
        
        # Standard permissions for Machine
        change_machine = Permission.objects.get(codename='change_machine', content_type=machine_ct)
        add_machine = Permission.objects.get(codename='add_machine', content_type=machine_ct)
        delete_machine = Permission.objects.get(codename='delete_machine', content_type=machine_ct)
        view_machine = Permission.objects.get(codename='view_machine', content_type=machine_ct)
        
        # Standard permissions for Rental
        change_rental = Permission.objects.get(codename='change_rental', content_type=rental_ct)
        add_rental = Permission.objects.get(codename='add_rental', content_type=rental_ct)
        delete_rental = Permission.objects.get(codename='delete_rental', content_type=rental_ct)
        view_rental = Permission.objects.get(codename='view_rental', content_type=rental_ct)
        
        # Clear existing permissions
        admin_group.permissions.clear()
        staff_group.permissions.clear()
        user_group.permissions.clear()
        farmer_group.permissions.clear()
        
        # Assign permissions to Administrators group (all permissions)
        admin_permissions = [
            add_machine, change_machine, delete_machine, view_machine,
            add_rental, change_rental, delete_rental, view_rental,
            can_rent_machine, can_schedule_rent, can_view_all_rentals, can_approve_rentals
        ]
        admin_group.permissions.add(*admin_permissions)
        
        # Assign permissions to Staff group
        staff_permissions = [
            add_machine, change_machine, view_machine,
            add_rental, change_rental, view_rental,
            can_rent_machine, can_schedule_rent, can_view_all_rentals, can_approve_rentals
        ]
        staff_group.permissions.add(*staff_permissions)
        
        # Assign permissions to Regular Users group
        user_permissions = [
            view_machine, view_rental, can_rent_machine
        ]
        user_group.permissions.add(*user_permissions)
        
        # Assign permissions to Rice Farmers group
        farmer_permissions = [
            view_machine, view_rental, can_rent_machine, can_schedule_rent
        ]
        farmer_group.permissions.add(*farmer_permissions)
        
        self.stdout.write(self.style.SUCCESS('Successfully set up user groups and permissions!')) 