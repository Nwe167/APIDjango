#!/usr/bin/env python
"""
Test file sharing functionality with Gmail/external emails
This script demonstrates how to share files with external users
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from AppAPI.models import File, Permission
import json

print("=" * 70)
print("FILE SHARING WITH GMAIL/EXTERNAL EMAILS - TEST SUITE")
print("=" * 70)

# Get or create test user
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@filedocs.com',
        'first_name': 'Admin',
        'last_name': 'User'
    }
)

# Get or create token
token, _ = Token.objects.get_or_create(user=admin)

print(f"\n✓ Test User: {admin.username} ({admin.email})")
print(f"✓ API Token: {token.key[:20]}...")

# Get or create a test file
file_obj, created = File.objects.get_or_create(
    name='test_document.pdf',
    owner=admin,
    defaults={
        'mime_type': 'application/pdf',
        'size_bytes': 1024000,
    }
)
print(f"✓ Test File: {file_obj.name} (ID: {file_obj.id})")

print("\n" + "=" * 70)
print("SCENARIO 1: Share with existing user (internal)")
print("=" * 70)

# Create another test user
user2, _ = User.objects.get_or_create(
    username='testuser',
    defaults={
        'email': 'testuser@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    }
)

# Create permission for existing user
try:
    perm1 = Permission.objects.create(
        file=file_obj,
        grantee_user=user2,
        permission_type='user',
        role='reader'
    )
    print(f"✓ Permission created for: {user2.email}")
    print(f"  - Permission ID: {perm1.id}")
    print(f"  - Role: {perm1.role}")
    print(f"  - Type: {perm1.permission_type}")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 70)
print("SCENARIO 2: Share with external Gmail address (no account yet)")
print("=" * 70)

external_email = 'someone@gmail.com'

# Create permission for external email
try:
    perm2 = Permission.objects.create(
        file=file_obj,
        grantee_email=external_email,
        permission_type='user',
        role='commenter'
    )
    print(f"✓ Permission created for external email: {external_email}")
    print(f"  - Permission ID: {perm2.id}")
    print(f"  - Role: {perm2.role}")
    print(f"  - Type: {perm2.permission_type}")
    print(f"  - Grantee Email: {perm2.grantee_email}")
    print(f"  - Grantee User: {perm2.grantee_user}")
    print("\n  📧 Email notification would be sent to: {external_email}")
    print("     Subject: Admin User shared 'test_document.pdf' with you")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 70)
print("SCENARIO 3: Share with domain/group (if needed)")
print("=" * 70)

try:
    perm3 = Permission.objects.create(
        file=file_obj,
        grantee_domain='example.com',
        permission_type='domain',
        role='reader'
    )
    print(f"✓ Permission created for domain: example.com")
    print(f"  - Role: {perm3.role}")
    print(f"  - Type: {perm3.permission_type}")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 70)
print("SCENARIO 4: Share with 'anyone' (public link)")
print("=" * 70)

try:
    perm4 = Permission.objects.create(
        file=file_obj,
        permission_type='anyone',
        role='reader'
    )
    print(f"✓ Permission created for anyone")
    print(f"  - Role: {perm4.role}")
    print(f"  - Type: {perm4.permission_type}")
    print(f"  - Allow file discovery: {perm4.allow_file_discovery}")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 70)
print("LIST ALL PERMISSIONS FOR THE FILE")
print("=" * 70)

permissions_list = Permission.objects.filter(file=file_obj, deleted=False)
print(f"\n✓ Total permissions: {permissions_list.count()}")

for i, perm in enumerate(permissions_list, 1):
    print(f"\n{i}. Permission ID: {perm.id}")
    print(f"   Type: {perm.permission_type}")
    print(f"   Role: {perm.role}")
    
    if perm.grantee_user:
        print(f"   Grantee: {perm.grantee_user.email} (user)")
    elif perm.grantee_email:
        print(f"   Grantee: {perm.grantee_email} (external)")
    elif perm.grantee_domain:
        print(f"   Grantee: {perm.grantee_domain} (domain)")
    else:
        print(f"   Grantee: Public (anyone)")
    
    print(f"   Created: {perm.created_at}")

print("\n" + "=" * 70)
print("REVOKE PERMISSION TEST")
print("=" * 70)

if permissions_list.exists():
    perm_to_revoke = permissions_list.first()
    revoked_email = perm_to_revoke.grantee_email or (perm_to_revoke.grantee_user.email if perm_to_revoke.grantee_user else 'unknown')
    
    perm_to_revoke.deleted = True
    perm_to_revoke.revoked_by = admin
    perm_to_revoke.save()
    
    print(f"✓ Permission revoked for: {revoked_email}")
    print(f"  📧 Unshare notification would be sent")
    print(f"     Subject: Access to '{file_obj.name}' has been revoked")

print("\n" + "=" * 70)
print("✓ FILE SHARING TEST COMPLETE")
print("=" * 70)
print("\nAPI Endpoints for file sharing:")
print("  POST   /api/permissions/")
print("         - Create permission for user/group/domain/anyone")
print("  GET    /api/permissions/?file_id=<id>")
print("         - List permissions for a file")
print("  DELETE /api/permissions/<id>/")
print("         - Revoke permission")
print("\n  POST   /api/share-links/")
print("         - Create public share link")
print("  GET    /api/share-links/?file_id=<id>")
print("         - List share links for a file")
print("  POST   /api/share-links/<id>/revoke/")
print("         - Revoke public link")
