import os, shutil, time
from app import app, save_result_file, create_user

# create user and clean up results
create_user('tester','pass')
user_folder = os.path.join(app.config['RESULTS_FOLDER'], 'tester')
if os.path.exists(user_folder):
    try:
        shutil.rmtree(user_folder)
    except PermissionError:
        print('Folder locked, trying to delete individual files...')
        for root, dirs, files in os.walk(user_folder, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except:
                    pass

# Create test data with clear abnormalities to trigger suggestions
analysis1 = {
    'Hemoglobin': {'value': 10.5, 'status': 'Low', 'normal': [12, 16]},
    'WBC': {'value': 14000, 'status': 'High', 'normal': [4000, 11000]},
    'Platelet': {'value': 250000, 'status': 'Normal', 'normal': [150000, 450000]},
    'Sugar': {'value': 95, 'status': 'Normal', 'normal': [70, 140]}
}

analysis2 = {
    'Hemoglobin': {'value': 12.5, 'status': 'Normal', 'normal': [12, 16]},
    'WBC': {'value': 12500, 'status': 'High', 'normal': [4000, 11000]},
    'Platelet': {'value': 240000, 'status': 'Normal', 'normal': [150000, 450000]},
    'Sugar': {'value': 125, 'status': 'Normal', 'normal': [70, 140]}
}

for i, anal in enumerate([analysis1, analysis2], start=1):
    fname = f"report{i}.pdf"
    save_result_file('tester', fname, {}, anal)

print('✓ Test data created with abnormalities')
print('  Report 1: Low Hemoglobin (10.5) and High WBC (14000)')
print('  Report 2: Normal Hemoglobin (12.5) and High WBC (12500)')

