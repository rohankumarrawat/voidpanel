#!/usr/bin/env python3
"""Fix migration: rename 0070 -> 0075, update dependency."""
import os, shutil

mig_dir = '/home/voidonyx/voidonyx/data/migrations'
old_path = os.path.join(mig_dir, '0070_whatsappconfig_api_fields.py')
new_path = os.path.join(mig_dir, '0075_whatsappconfig_api_fields.py')

if os.path.exists(old_path):
    with open(old_path, 'r') as f:
        content = f.read()
    
    content = content.replace(
        "('data', '0069_khatabookorder_owner_phone')",
        "('data', '0074_blogpost_edit_unlocked')"
    )
    
    with open(new_path, 'w') as f:
        f.write(content)
    
    os.remove(old_path)
    
    # Also remove any .pyc cache
    pyc_dir = os.path.join(mig_dir, '__pycache__')
    if os.path.exists(pyc_dir):
        for fn in os.listdir(pyc_dir):
            if '0070_whatsappconfig' in fn:
                os.remove(os.path.join(pyc_dir, fn))
                print(f'Removed cache: {fn}')
    
    print(f'Renamed to {new_path}')
    print(f'Updated dependency to 0074_blogpost_edit_unlocked')
elif os.path.exists(new_path):
    print('Already renamed to 0075')
else:
    print('ERROR: migration file not found')

print('FIX_MIGRATION_DONE')
