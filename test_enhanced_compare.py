from app import app
import os

client = app.test_client()
client.post('/login', data={'username':'tester','password':'pass'}, follow_redirects=True)
folder = os.path.join(app.config['RESULTS_FOLDER'], 'tester')
names=[]
for root, dirs, files in os.walk(folder):
    for f in files:
        if f.endswith('.json'):
            rel=os.path.relpath(os.path.join(root,f), folder)
            names.append(rel.replace('\\','/'))
resp = client.post('/compare_view', data={'reports':names})
html = resp.data.decode('utf-8')

# Check for new sections
print('✓ Point-by-Point Changes present:', 'Point-by-Point Changes Across Reports' in html)
print('✓ Diet Plan present:', 'Best Health Diet Plan' in html)
print('✓ Exercise Tips present:', 'Exercise & Lifestyle Tips' in html)
print('✓ Breakfast section:', '🌅 Breakfast' in html)
print('✓ Lunch section:', '🍲 Lunch' in html)
print('✓ Dinner section:', '🍽️ Dinner' in html)
print('✓ Snacks section:', '🥗 Healthy Snacks' in html)
print('✓ Canvas count (charts):', html.count('canvas id'))
print()
# Extract and show segments
if 'Point-by-Point Changes' in html:
    start = html.find('Point-by-Point Changes')
    end = html.find('</div>', start) + len('</div>')
    print('Point-by-Point section snippet:')
    print(html[start:start+400])
