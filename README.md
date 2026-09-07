# WellView - Health Report OCR Demo

This is a small Flask app that accepts an uploaded medical report image and displays extracted values.

Quick setup (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

After the app starts, open http://127.0.0.1:5001 in your browser.

Notes:
- If you don't have Tesseract installed, OCR won't run. You can still upload files — the app uses simulated sample data.
- The `uploads/` folder stores uploaded files.
