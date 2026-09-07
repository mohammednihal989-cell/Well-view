import os, shutil
from app import app, save_result_file, create_user

# create user and results
create_user('tester','pass')
user_folder = os.path.join(app.config['RESULTS_FOLDER'], 'tester')
if os.path.exists(user_folder):
    shutil.rmtree(user_folder)

analysis1={'Hemoglobin':{'value':13,'status':'Normal','normal':[12,16]},'WBC':{'value':12000,'status':'High','normal':[4000,11000]}}
analysis2={'Hemoglobin':{'value':11,'status':'Low','normal':[12,16]},'WBC':{'value':9000,'status':'Normal','normal':[4000,11000]}}
for i,anal in enumerate([analysis1,analysis2], start=1):
    fname=f"report{i}.pdf"
    save_result_file('tester', fname, {}, anal)
print('Created test results at', user_folder)
print(os.listdir(user_folder))
