import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from AppAPI.models import ShareLink, File
from django.contrib.auth.models import User

file = File.objects.first()
user = User.objects.first()

if file and user:
    print("Creating 3 ShareLinks for the same file...\n")
    for i in range(1, 4):
        link = ShareLink(
            file=file,
            created_by=user,
            role='reader'
        )
        link.save()
        print(f"✓ ShareLink {i} created")
        print(f"  Token: {link.token[:16]}...")
        print(f"  ID: {link.id}\n")
    
    print(f"\n✓ All 3 ShareLinks created successfully with unique tokens!")
    
    # Verify tokens are actually unique
    tokens = ShareLink.objects.values_list('token', flat=True)
    unique_tokens = set(tokens)
    print(f"\nTotal ShareLinks: {len(tokens)}")
    print(f"Unique tokens: {len(unique_tokens)}")
    print(f"All unique: {len(tokens) == len(unique_tokens)}")
else:
    print("✗ No files or users found")
