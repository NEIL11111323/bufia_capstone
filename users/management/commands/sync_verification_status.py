from django.core.management.base import BaseCommand
from users.models import CustomUser, MembershipApplication
from django.utils import timezone

class Command(BaseCommand):
    help = 'Synchronizes verification status between CustomUser and MembershipApplication'

    def handle(self, *args, **options):
        # 1. Get statistics before synchronization
        verified_users_count = CustomUser.objects.filter(is_verified=True).count()
        approved_applications_count = MembershipApplication.objects.filter(is_approved=True).count()
        verified_with_approved_count = MembershipApplication.objects.filter(
            user__is_verified=True, is_approved=True
        ).count()
        
        self.stdout.write(self.style.SUCCESS(f"Before synchronization:"))
        self.stdout.write(f"- Verified users: {verified_users_count}")
        self.stdout.write(f"- Approved applications: {approved_applications_count}")
        self.stdout.write(f"- Verified users with approved applications: {verified_with_approved_count}")
        
        # 2. Fix verified users with unapproved applications
        verified_users_with_unapproved_apps = MembershipApplication.objects.filter(
            user__is_verified=True, is_approved=False
        )
        
        for app in verified_users_with_unapproved_apps:
            app.is_approved = True
            app.is_rejected = False
            app.review_date = timezone.now().date()
            app.save()
            
            self.stdout.write(f"- Updated application for user: {app.user.username}")
        
        # 3. Fix verified users without membership applications
        verified_users_without_apps = CustomUser.objects.filter(
            is_verified=True
        ).exclude(
            membership_application__isnull=False
        )
        
        for user in verified_users_without_apps:
            # Create a new application record for the user
            MembershipApplication.objects.create(
                user=user,
                is_approved=True,
                submission_date=user.membership_approved_date or timezone.now().date(),
                review_date=user.membership_approved_date or timezone.now().date(),
            )
            self.stdout.write(f"- Created new application for user: {user.username}")
        
        # 4. Fix approved applications with unverified users
        approved_apps_with_unverified_users = MembershipApplication.objects.filter(
            is_approved=True, user__is_verified=False
        )
        
        for app in approved_apps_with_unverified_users:
            user = app.user
            user.is_verified = True
            user.membership_approved_date = app.review_date or timezone.now().date()
            user.save()
            
            self.stdout.write(f"- Updated verification status for user: {user.username}")
        
        # 5. Get statistics after synchronization
        verified_users_count = CustomUser.objects.filter(is_verified=True).count()
        approved_applications_count = MembershipApplication.objects.filter(is_approved=True).count()
        verified_with_approved_count = MembershipApplication.objects.filter(
            user__is_verified=True, is_approved=True
        ).count()
        
        self.stdout.write(self.style.SUCCESS(f"\nAfter synchronization:"))
        self.stdout.write(f"- Verified users: {verified_users_count}")
        self.stdout.write(f"- Approved applications: {approved_applications_count}")
        self.stdout.write(f"- Verified users with approved applications: {verified_with_approved_count}")
        
        self.stdout.write(self.style.SUCCESS("\nSynchronization completed successfully!")) 