from app import app
import os

client = app.test_client()
# log in
resp = client.post('/login', data={'username':'tester','password':'pass'}, follow_redirects=True)
print('login status', resp.status_code)
# inspect saved results page data length
res = client.get('/saved_results')
print('saved_results length', len(res.data))
# list names from results folder
folder = os.path.join(app.config['RESULTS_FOLDER'], 'tester')
names = []
for root, dirs, files in os.walk(folder):
    for f in files:
        if f.endswith('.json'):
            rel = os.path.relpath(os.path.join(root,f), folder)
            names.append(rel.replace('\\','/'))
print('names', names)
# now perform compare_view post
post_data = {'reports': names}
resp = client.post('/compare_view', data=post_data)
html = resp.data.decode('utf-8')
print('compare_view status', resp.status_code)
print('canvas count', html.count('canvas id'))
print('suggestions present', 'Suggestions' in html)
# optionally write full html to file for manual inspection
with open('debug_compare.html','w',encoding='utf8') as f:
    f.write(html)
print('wrote debug_compare.html')
print(html[:2000])
