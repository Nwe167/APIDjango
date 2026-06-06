#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'APISharingfile.settings')
django.setup()

from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
import urllib.request
import urllib.error
import json

# Get admin token
try:
    admin = User.objects.get(username='admin')
    token = Token.objects.filter(user=admin).first()
    if not token:
        token = Token.objects.create(user=admin)
    print(f"Admin token: {token.key}")
except Exception as e:
    print(f"Error getting token: {e}")
    sys.exit(1)

# Test endpoints
headers = {'Authorization': f'Token {token.key}', 'Content-Type': 'application/json'}
base_url = 'http://127.0.0.1:8000/api/v1'

endpoints = [
    'users/profile/me/',
    'files/?limit=5',
    'activity/?limit=10',
    'users/notifications/'
]

for endpoint in endpoints:
    url = f'{base_url}/{endpoint}'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = response.read()
            print(f"✓ {endpoint}: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"✗ {endpoint}: {e.code}")
        error_body = e.read().decode()
        try:
            error_json = json.loads(error_body)
            print(f"  Error: {json.dumps(error_json, indent=2)[:300]}")
        except:
            print(f"  Error: {error_body[:200]}")
    except Exception as e:
        print(f"✗ {endpoint}: {e}")
