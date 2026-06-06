import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 80)
print("DETAILED ADMIN PASSWORD CHECK")
print("=" * 80)

admin_user = User.objects.filter(username='admin').first()

if not admin_user:
    print("\n✗ ERROR: Admin user not found!")
    exit(1)

print(f"\n✓ Admin user found: {admin_user.username}")
print(f"  Email: {admin_user.email}")
print(f"  Password Hash: {admin_user.password[:50]}...")
print(f"  Is Staff: {admin_user.is_staff}")
print(f"  Is Superuser: {admin_user.is_superuser}")
print(f"  Is Active: {admin_user.is_active}")

# Try multiple passwords
passwords_to_try = [
    "CloudVault@2026",
    "admin",
    "admin123",
    "password",
]

print(f"\n✓ Testing different passwords:\n")
for pwd in passwords_to_try:
    result = "✅ MATCH" if admin_user.check_password(pwd) else "❌ No match"
    print(f"  {pwd:20} {result}")

# Check if there are other superusers
print(f"\n✓ All superusers in database:\n")
superusers = User.objects.filter(is_superuser=True)
for user in superusers:
    print(f"  {user.username:15} | {user.email:25} | Staff: {user.is_staff}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("\nIf login still fails, try these alternative admin accounts:")
for user in superusers:
    print(f"  Username: {user.username}")

print("\n" + "=" * 80)
