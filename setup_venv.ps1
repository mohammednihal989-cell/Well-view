# PowerShell helper to create virtual environment and install requirements
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "Setup complete. Run: .venv\Scripts\Activate.ps1; python app.py"