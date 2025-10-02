#!/usr/bin/env python3
"""Test if the code is actually loaded with debug fields"""

import sys
sys.path.insert(0, '/opt/blockshelf')

# Check if the file has the debug code
with open('/opt/blockshelf/inventory/views/api.py', 'r') as f:
    content = f.read()
    count = content.count('_debug_api_key')
    print(f"File contains '_debug_api_key': {count} times")
    if count >= 3:
        print("✓ File has the debug code")
    else:
        print("✗ File missing debug code")

# Try to import and check loaded module
try:
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockshelf_inventory.settings')
    django.setup()

    from inventory.views import api
    import inspect
    source = inspect.getsource(api.lookup_part)
    if '_debug_api_key' in source:
        print("✓ Loaded module has _debug_api_key")
    else:
        print("✗ Loaded module does NOT have _debug_api_key")

    # Clear cache
    from django.core.cache import cache
    deleted = 0
    try:
        pattern = 'lookup:*'
        keys = list(cache.keys(pattern))
        if keys:
            cache.delete_many(keys)
            deleted = len(keys)
    except:
        # If keys() not supported, try clearing all
        cache.clear()
        deleted = "all"
    print(f"✓ Cleared {deleted} cache entries")

except Exception as e:
    print(f"✗ Error loading module: {e}")
