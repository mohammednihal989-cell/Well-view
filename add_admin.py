from app import create_user, load_users
import os
import getpass

username = 'Team02'
email = 'wellview02@gmail.com'

# Prefer providing the admin password via environment variable in CI/automated setups
password = os.getenv('ADMIN_PASSWORD')
if not password:
    try:
        password = getpass.getpass('Enter password for admin user Team02: ')
    except Exception:
        # Fallback to a prompt-less default is dangerous; fail instead
        raise SystemExit('No ADMIN_PASSWORD set and interactive input unavailable.')

created = create_user(username, password, email, is_admin=True)
if created:
    print('CREATED')
else:
    users = load_users()
    if username in users:
        print('EXISTS')
    else:
        print('FAILED')
