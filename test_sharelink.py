import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from AppAPI.models import ShareLink, File
from django.contrib.auth.models import User

# Get the first file
file = File.objects.first()
user = User.objects.first()

if file and user:
    # Try to create a ShareLink
    link = ShareLink(
        file=file,
        created_by=user,
        role='reader'
    )
    link.save()
    print(f"✓ ShareLink created successfully!")
    print(f"  Token: {link.token}")
    print(f"  File: {link.file.name}")
    print(f"  ID: {link.id}")
else:
    print("✗ No files or users found")
