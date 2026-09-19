#!/usr/bin/env python3
"""
Submit x402-discovery-index listing issue for Vend API Merchant.
"""
import json
import urllib.request
import os

# Read the issue body from file
with open('/root/vend/bin/x402-discovery-issue.json') as f:
    payload = json.load(f)

# Get GitHub token from git credentials
with open('/root/.git-credentials') as f:
    line = f.readline().strip()
    # Format: https://user:token@github.com
    token = line.split('://', 1)[1].split('@')[0].split(':', 1)[1]

print(f"Token length: {len(token)}")

# Create the issue
req_data = {
    'title': payload['title'],
    'body': payload['body'],
}

req = urllib.request.Request(
    'https://api.github.com/repos/x402-index/x402-discovery-index/issues',
    data=json.dumps(req_data).encode(),
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'vend-agent'
    }
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        print(f"Status: {resp.status}")
        print(f"Issue URL: {result.get('html_url')}")
        print(f"Issue #: {result.get('number')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Response: {e.read().decode()}")
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason}")