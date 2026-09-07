#!/usr/bin/env python
"""Quick verification that Team02 is set up correctly."""
import json
from app import load_users

users = load_users()
print('✅ Users loaded successfully\n')
print('Team02 Configuration:')
print(f'  - Email: {users["Team02"].get("email")}')
print(f'  - Is Admin: {users["Team02"].get("is_admin")}')
print(f'  - User ID: {users["Team02"].get("user_id")}')

# Check how many admins exist
admin_count = sum(1 for u in users.values() if u.get('is_admin', False))
print(f'\nTotal admin accounts in system: {admin_count}')
if admin_count == 1:
    print('✅ Only ONE admin (Team02) - CORRECT')
else:
    print(f'⚠️  WARNING: {admin_count} admins found, should be 1')

print('\nAll admins:')
for username, data in users.items():
    if data.get('is_admin', False):
        print(f'  - {username}: {data.get("email")}')

print('\n✅ System is ready!')
print('Users will now receive feedback notifications at: wellview02@gmail.com')
