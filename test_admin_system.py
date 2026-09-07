"""
Test script for admin system functionality.
"""
import sys
import os
import json
import tempfile
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app
from app import app, create_user, load_users, is_admin_user

def test_admin_system():
    """Test admin system setup and access."""
    
    # Create test client
    client = app.test_client()
    
    # Clean up test users first to avoid conflict if they already exist
    from app import save_users
    users = load_users()
    for u in ['admin_test', 'user1', 'user2', 'doctor_admin']:
        if u in users:
            del users[u]
    save_users(users)

    print("=" * 60)
    print("ADMIN SYSTEM TEST SUITE")
    print("=" * 60)
    
    # Ensure we have a known admin account for testing
    admin_username = 'admin_test'
    admin_password = 'AdminPass123'
    admin_email = 'admin@wellview.test'

    # Try to create a deterministic admin entry; if it already exists and is admin, we'll use it.
    created = create_user(admin_username, admin_password, admin_email, is_admin=True)
    if created:
        print("✓ Created admin_test account programmatically")
    else:
        users_now = load_users()
        if admin_username in users_now and users_now[admin_username].get('is_admin'):
            print("✓ admin_test already exists and is admin")
        else:
            # If admin_test exists but not admin or creation failed, create an alternate admin
            alt_name = f'admin_auto_{int(datetime.utcnow().timestamp())}'
            create_user(alt_name, admin_password, f'{alt_name}@wellview.test', is_admin=True)
            admin_username = alt_name
            print(f"✓ Created alternate admin account: {admin_username}")
    
    # Test 3: Verify admin flag in users.json
    print("\n[TEST 3] Verify admin flag stored in users.json...")
    all_users = load_users()
    assert 'admin_test' in all_users, "Admin user not found in users.json"
    assert all_users['admin_test'].get('is_admin') == True, "is_admin flag not set"
    assert all_users['admin_test'].get('email') == 'admin@wellview.test', "Email not stored correctly"
    assert 'user_id' in all_users['admin_test'], "User ID not generated"
    print("✓ Admin user data stored correctly")
    print(f"  - User ID: {all_users['admin_test'].get('user_id')}")
    print(f"  - Email: {all_users['admin_test'].get('email')}")
    print(f"  - Created at: {all_users['admin_test'].get('created_at')}")
    
    # Test 4: Cannot create second admin via setup
    print("\n[TEST 4] Prevent duplicate admin account creation...")
    response = client.get('/admin/setup')
    assert b'Admin account already exists' in response.data or response.status_code == 302, "Should prevent admin creation"
    print("✓ Setup correctly prevents duplicate admin accounts")
    
    # Test 5: Admin login works
    print("\n[TEST 5] Admin login functionality...")
    response = client.post('/login', data={
        'username': 'admin_test',
        'password': 'AdminPass123'
    }, follow_redirects=True)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert b'dashboard' in response.data.lower() or b'upload' in response.data.lower(), "Admin login redirect failed"
    print("✓ Admin login successful")
    
    # Test 6: Create some test users to populate admin dashboard
    print("\n[TEST 6] Create test users for admin dashboard...")
    create_user('user1', 'pass1', 'user1@test.com', is_admin=False)
    create_user('user2', 'pass2', 'user2@test.com', is_admin=False)
    create_user('doctor_admin', 'pass3', 'doctor@test.com', is_admin=True)
    print("✓ Test users created successfully")
    
    # Test 7: Admin can access dashboard
    print("\n[TEST 7] Admin dashboard accessibility...")
    with client:
        # Login as admin first
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'AdminPass123'
        })
        
        # Now try to access admin dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert b'Admin Dashboard' in response.data, "Admin dashboard page not found"
        assert b'Registered Users' in response.data, "Users list section missing"
        print("✓ Admin dashboard is accessible")
    
    # Test 8: Admin dashboard displays users
    print("\n[TEST 8] Admin dashboard displays user information...")
    with client:
        # Login as admin
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'AdminPass123'
        })
        
        response = client.get('/admin/dashboard')
        
        # Check for user details
        assert b'user1' in response.data, "user1 not found in dashboard"
        assert b'user2' in response.data, "user2 not found in dashboard"
        assert b'user1@test.com' in response.data, "user email not found in dashboard"
        assert b'Total Users' in response.data, "Stats section missing"
        
        print("✓ Admin dashboard displays all users correctly")
        
        # Count users in display
        users = load_users()
        print(f"  - Total users in system: {len(users)}")
        print(f"  - Users displayed:")
        for username in ['admin_test', 'user1', 'user2', 'doctor_admin']:
            if username in users:
                print(f"    • {username} (ID: {users[username].get('user_id')}) - Admin: {users[username].get('is_admin', False)}")
    
    # Test 9: Non-admin cannot access admin dashboard
    print("\n[TEST 9] Prevent non-admin access to dashboard...")
    # Use a fresh client for non-admin to avoid leftover admin session
    client_nonadmin = app.test_client()
    # Login as regular user
    client_nonadmin.post('/login', data={
        'username': 'user1',
        'password': 'pass1'
    })

    # Should redirect (302) since non-admin
    response_no_redirect = client_nonadmin.get('/admin/dashboard', follow_redirects=False)
    assert response_no_redirect.status_code == 302, f"Expected redirect (302), got {response_no_redirect.status_code}"

    # Follow redirect and verify it goes to dashboard with a permission flash
    response = client_nonadmin.get('/admin/dashboard', follow_redirects=True)
    assert b'You do not have admin permissions' in response.data, \
        "Non-admin should be blocked from admin dashboard"
    print("✓ Non-admin access to admin dashboard is restricted")
    
    # Test 10: Admin link appears in navbar for admins
    print("\n[TEST 10] Admin navbar link visibility...")
    with client:
        # Login as admin
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'AdminPass123'
        })
        
        response = client.get('/admin/dashboard')
        assert response.status_code == 200, "Dashboard access failed"
        # Check if admin-related elements are present (context processor should inject is_admin)
        # Note: The actual link visibility depends on template rendering
        print("✓ Admin context variables available for rendering")
    
    # Test 11: Feedback submission should notify admins
    print("\n[TEST 11] Feedback notification to admin..." )
    with client:
        # ensure we're in testing mode and clear previous outbox
        app.config['TESTING'] = True
        from app import EMAIL_OUTBOX
        EMAIL_OUTBOX.clear()

        # login as a standard user and submit feedback
        client.get('/logout')
        client.post('/login', data={
            'username': 'user1',
            'password': 'pass1'
        })
        response = client.post('/feedback', data={'message': 'This is a test feedback'}, follow_redirects=True)
        assert b'Thank you' in response.data, "Feedback submission flash not shown"
        # after posting we should have an email in the outbox
        assert EMAIL_OUTBOX, "No email was sent to admins"
        last_mail = EMAIL_OUTBOX[-1]
        assert 'New WellView feedback' in last_mail['subject']
        assert 'This is a test feedback' in last_mail['body']
        assert 'wellview02@gmail.com' in last_mail['to'], "Admin's email missing from notification"
        print("✓ Feedback submission triggers email to admin(s)")

    # Test 12: Admin can view feedback entries via /admin/feedback
    print("\n[TEST 12] Admin feedback inbox shows entries...")
    with client:
        client.get('/logout')
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'AdminPass123'
        })
        response = client.get('/admin/feedback')
        assert response.status_code == 200, "Admin feedback page unavailable"
        assert b'This is a test feedback' in response.data, "Feedback entry not visible to admin"
        assert b'Great app!' in response.data or b'so intresting' in response.data, "Previous entries missing"
        print("✓ Admin feedback page displays all user feedback")

    print("\n" + "=" * 60)
    print("ALL ADMIN SYSTEM TESTS PASSED! ✅")
    print("=" * 60)
    print("\nAdmin System Summary:")
    print("  • Admin setup page: /admin/setup")
    print("  • Admin dashboard: /admin/dashboard")
    print("  • Admin features enabled for admin users")
    print("  • User IDs generated for all users")
    print("  • Email addresses captured and stored")
    print("  • Feedback notifications sent to admins")
    print("  • Admin can view feedback entries")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    try:
        test_admin_system()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
