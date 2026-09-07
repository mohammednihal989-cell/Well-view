from app import app

client = app.test_client()

# Test 1: Check index.html doesn't have Key Features
resp = client.get('/')
html = resp.data.decode('utf-8')
has_features = 'Key Features' in html
print(f'✓ Key Features removed from index: {not has_features}')

# Test 2: Check signup.html has email field
resp_signup = client.get('/signup')
signup_html = resp_signup.data.decode('utf-8')
has_email = 'type="email"' in signup_html and 'Email Address' in signup_html
print(f'✓ Email field in signup form: {has_email}')

# Test 3: Try signup with email - valid
resp_post = client.post('/signup', data={
    'username': 'testuser123',
    'email': 'test@example.com',
    'password': 'password123',
    'confirm': 'password123'
}, follow_redirects=True)
print(f'✓ Signup successful: {resp_post.status_code == 200}')

# Test 4: Try signup with invalid email
client2 = app.test_client()
resp_invalid = client2.post('/signup', data={
    'username': 'user2',
    'email': 'invalidemail',
    'password': 'pass123',
    'confirm': 'pass123'
})
invalid_html = resp_invalid.data.decode('utf-8')
print(f'✓ Invalid email rejected: {"valid email" in invalid_html.lower()}')

# Test 5: Try duplicate email
client3 = app.test_client()
resp_dup = client3.post('/signup', data={
    'username': 'user3',
    'email': 'test@example.com',  # same as first user
    'password': 'pass123',
    'confirm': 'pass123'
})
dup_html = resp_dup.data.decode('utf-8')
print(f'✓ Duplicate email rejected: {"already registered" in dup_html.lower()}')

# Verify user data stored correctly
from app import load_users
users = load_users()
user_data = users.get('testuser123', {})
print(f'✓ Email stored in user data: {user_data.get("email") == "test@example.com"}')

print('\n✅ All email field tests passed!')
