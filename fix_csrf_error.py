"""
Quick script to fix CSRF errors by clearing sessions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia_project.settings')
django.setup()

from django.contrib.sessions.models import Session
from django.utils import timezone

print("=" * 70)
print("CSRF ERROR FIX - CLEARING SESSIONS")
print("=" * 70)

# Get all sessions
all_sessions = Session.objects.all()
print(f"\nTotal sessions in database: {all_sessions.count()}")

# Get expired sessions
expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
print(f"Expired sessions: {expired_sessions.count()}")

# Clear all sessions
if all_sessions.count() > 0:
    confirm = input("\nClear all sessions? This will log out all users. (yes/no): ")
    if confirm.lower() == 'yes':
        deleted_count = all_sessions.count()
        all_sessions.delete()
        print(f"\n✅ Cleared {deleted_count} session(s)")
        print("\nAll users have been logged out.")
        print("They will need to log in again with fresh CSRF tokens.")
    else:
        print("\n❌ Session clearing cancelled")
else:
    print("\n✅ No sessions to clear")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("""
1. Restart your Django server:
   - Stop the server (Ctrl+C)
   - Run: python manage.py runserver

2. Clear your browser cache:
   - Open DevTools (F12)
   - Go to Application/Storage tab
   - Clear all cookies and site data
   - Hard refresh (Ctrl+Shift+R)

3. Log in again with fresh credentials

4. Try submitting the form again
""")
print("=" * 70)
