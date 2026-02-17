from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a user account for BUFIA system'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the account')
        parser.add_argument('--email', type=str, help='Email address')
        parser.add_argument('--password', type=str, default='testpass123', help='Password (default: testpass123)')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--phone', type=str, default='09123456789', help='Phone number')

    def handle(self, *args, **options):
        # Get user details from options or use defaults
        username = options.get('username') or 'testuser2'
        email = options.get('email') or 'testuser2@bufia.com'
        password = options.get('password') or 'testpass123'
        first_name = options.get('first_name') or 'Maria'
        last_name = options.get('last_name') or 'Santos'
        phone_number = options.get('phone') or '09987654321'

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists!"))
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS("=" * 50))
            self.stdout.write(self.style.SUCCESS("Existing User Account Details:"))
            self.stdout.write(self.style.SUCCESS("=" * 50))
            self.stdout.write(f"Username: {user.username}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Password: {password}")
            self.stdout.write(f"Name: {user.first_name} {user.last_name}")
            self.stdout.write(f"Phone: {user.phone_number}")
            self.stdout.write(f"Role: {user.role}")
            self.stdout.write(f"Verified: {'Yes' if user.is_verified else 'No'}")
            self.stdout.write(self.style.SUCCESS("=" * 50))
        else:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                is_active=True,
                is_verified=False,
                role='member'
            )
            
            self.stdout.write(self.style.SUCCESS("=" * 50))
            self.stdout.write(self.style.SUCCESS("✅ User Account Created Successfully!"))
            self.stdout.write(self.style.SUCCESS("=" * 50))
            self.stdout.write(f"Username: {username}")
            self.stdout.write(f"Email: {email}")
            self.stdout.write(f"Password: {password}")
            self.stdout.write(f"Name: {first_name} {last_name}")
            self.stdout.write(f"Phone: {phone_number}")
            self.stdout.write(f"Role: member")
            self.stdout.write(f"Verified: No (submit membership application to get verified)")
            self.stdout.write(self.style.SUCCESS("=" * 50))
            self.stdout.write("\nYou can now login at: http://127.0.0.1:8000/accounts/login/")
            self.stdout.write(self.style.SUCCESS("=" * 50))
