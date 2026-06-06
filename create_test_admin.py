import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 80)
print("CREATING NEW ADMIN ACCOUNT FOR TESTING")
print("=" * 80)

# Delete old testadmin if exists
User.objects.filter(username='testadmin').delete()

# Create new admin account
testadmin = User.objects.create_superuser(
    username='testadmin',
    email='testadmin@localhost',
    password='Test@1234'
)

print(f"\n✅ New admin account created:")
print(f"   Username: testadmin")
print(f"   Email: testadmin@localhost")
print(f"   Password: Test@1234")
print(f"   Is Staff: {testadmin.is_staff}")
print(f"   Is Superuser: {testadmin.is_superuser}")

# Verify
print(f"\n✓ Verifying password:")
print(f"   Password Check: {testadmin.check_password('Test@1234')}")

print("\n" + "=" * 80)
print("TRY LOGGING IN WITH:")
print("=" * 80)
print(f"URL: http://127.0.0.1:8000/admin/")
print(f"Username: testadmin")
print(f"Password: Test@1234")
print("\n" + "=" * 80)
