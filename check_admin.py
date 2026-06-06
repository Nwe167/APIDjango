import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 80)
print("CHECKING ADMIN ACCOUNT IN DJANGO")
print("=" * 80)

print("\n✓ ALL USERS IN DATABASE:\n")
users = User.objects.all()
for user in users:
    print(f"  ID: {user.id:2} | Username: {user.username:15} | Email: {user.email:25} |", end="")
    print(f" Staff: {str(user.is_staff):5} | Superuser: {str(user.is_superuser):5} | Active: {str(user.is_active):5}")

print("\n" + "=" * 80)
admin_user = User.objects.filter(username='admin').first()

if admin_user:
    print("\n✓ ADMIN ACCOUNT FOUND:\n")
    print(f"  Username:    {admin_user.username}")
    print(f"  Email:       {admin_user.email}")
    print(f"  First Name:  {admin_user.first_name if admin_user.first_name else '(empty)'}")
    print(f"  Last Name:   {admin_user.last_name if admin_user.last_name else '(empty)'}")
    print(f"  Is Staff:    {admin_user.is_staff}")
    print(f"  Is Superuser:{admin_user.is_superuser}")
    print(f"  Is Active:   {admin_user.is_active}")
    print(f"  Date Joined: {admin_user.date_joined}")
    print(f"  Last Login:  {admin_user.last_login}")
else:
    print("\n✗ ADMIN ACCOUNT NOT FOUND!")

print("\n" + "=" * 80)
print("ADMIN PANEL ACCESS INFO")
print("=" * 80)
print("\nURL:      http://127.0.0.1:8000/admin/")
print("Username: admin")
print("Password: CloudVault@2026")
print("\n" + "=" * 80)
