from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum
from AppAPI.models import File, UserProfile


class Command(BaseCommand):
    help = 'Recalculate storage_quota_usage_bytes for all users'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        updated = 0
        for user in users:
            total = File.objects.filter(
                owner=user,
                trashed=False,
                size_bytes__isnull=False
            ).exclude(
                mime_type='folder'
            ).aggregate(total=Sum('size_bytes'))['total'] or 0

            rows = UserProfile.objects.filter(user=user).update(storage_quota_usage_bytes=total)
            if rows:
                updated += 1
                self.stdout.write(f"  {user.email}: {total} bytes")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Updated {updated} user(s)."))
