import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 80)
print("ADMIN LOGIN TROUBLESHOOTING")
print("=" * 80)

admin_user = User.objects.filter(username='admin').first()

if not admin_user:
    print("\n✗ ERROR: Admin user not found!")
    exit(1)

print(f"\n✓ Admin user found: {admin_user.username}")
print(f"  Email: {admin_user.email}")
print(f"  Is Staff: {admin_user.is_staff}")
print(f"  Is Superuser: {admin_user.is_superuser}")
print(f"  Is Active: {admin_user.is_active}")

# Test password
test_password = "CloudVault@2026"
print(f"\n✓ Testing password: {test_password}")

if admin_user.check_password(test_password):
    print("  ✅ PASSWORD IS CORRECT")
else:
    print("  ❌ PASSWORD IS INCORRECT - Need to reset it")
    print("\n  Resetting admin password to: CloudVault@2026")
    admin_user.set_password("CloudVault@2026")
    admin_user.save()
    print("  ✅ Password has been reset!")

print("\n" + "=" * 80)
print("LOGIN INFORMATION")
print("=" * 80)
print(f"\nURL:      http://127.0.0.1:8000/admin/")
print(f"Username: admin")
print(f"Password: CloudVault@2026")
print(f"\nTry logging in now!")
print("\n" + "=" * 80)
