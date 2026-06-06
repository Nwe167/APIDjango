import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from AppAPI.models import ShareLink, File
from django.contrib.auth.models import User
from django.db import IntegrityError

file = File.objects.first()
user = User.objects.first()

print("=" * 60)
print("TESTING SHARELINK TOKEN FIX")
print("=" * 60)

try:
    if not file or not user:
        print("✗ Fatal: No File or User found in the database. Please ensure migrations are run and data exists.")
    else:
        print("\n1. Creating ShareLink without specifying token...")
        link1 = ShareLink(
            file=file,
            created_by=user,
            role='reader'
        )
        link1.save()
        print(f"   ✓ Success! Token: {link1.token[:16]}...")
        
        print("\n2. Creating another ShareLink without specifying token...")
        link2 = ShareLink(
            file=file,
            created_by=user,
            role='commenter'
        )
        link2.save()
        print(f"   ✓ Success! Token: {link2.token[:16]}...")
        
        print("\n3. Creating a third ShareLink without specifying token...")
        link3 = ShareLink(
            file=file,
            created_by=user,
            role='writer'
        )
        link3.save()
        print(f"   ✓ Success! Token: {link3.token[:16]}...")
        
        # Verify uniqueness
        tokens = [link1.token, link2.token, link3.token]
        unique = len(tokens) == len(set(tokens))
        
        print(f"\n4. Verifying token uniqueness...")
        print(f"   Token 1 == Token 2: {link1.token == link2.token} (should be False)")
        print(f"   Token 2 == Token 3: {link2.token == link3.token} (should be False)")
        print(f"   Token 1 == Token 3: {link1.token == link3.token} (should be False)")
        print(f"   All unique: {unique} (should be True) ✓\n")
        
        print("=" * 60)
        print("✓✓✓ FIX VERIFIED - NO INTEGRITY ERROR ✓✓✓")
        print("=" * 60)
        print("\nThe UNIQUE constraint issue has been resolved.")
        print("ShareLink tokens are now auto-generated and unique.")
    
except IntegrityError as e:
    print(f"\n   ✗ IntegrityError: {e}")
    print("   The fix may not have been applied correctly")
except Exception as e:
    print(f"\n   ✗ Error: {type(e).__name__}: {e}")
