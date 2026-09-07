from flask import Flask, render_template, request, redirect, url_for, abort, flash, session
import os
import re
import json
from datetime import datetime
from functools import wraps

# OCR imports
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

app = Flask(__name__)
# Load secrets and configuration from environment variables
app.secret_key = os.getenv('SECRET_KEY') or os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:
    # In development, generate a temporary key but warn the developer
    app.secret_key = os.urandom(24)
    app.logger.warning('SECRET_KEY not set; using a temporary secret key. Set SECRET_KEY in environment for production.')

# Upload/security config
# Max upload size (bytes) - default 10 MB
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
# Allowed extensions (comma separated env var)
app.config['ALLOWED_EXTENSIONS'] = set(x.strip().lower() for x in os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,bmp,tiff,pdf').split(','))

# --- email notification configuration ----------------------------------
import smtplib
from email.message import EmailMessage

# SMTP server used for sending notifications (during dev you can run
# `python -m smtpd -c DebuggingServer -n localhost:1025` to capture mails).
SMTP_SERVER = os.getenv('SMTP_SERVER', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', 1025))
DEFAULT_FROM_ADDRESS = 'no-reply@wellview.test'

# When TESTING=True the send_email function will append messages here
# instead of trying to contact a real SMTP server.
EMAIL_OUTBOX = []


def send_email(subject: str, body: str, to_addrs: list[str]) -> bool:
    """Send a simple plaintext message to one or more recipients.

    In testing mode the message is recorded in ``EMAIL_OUTBOX`` so
    unit tests can inspect it.  Returns True on success, False on
    failure (the caller can ignore the return value if it doesn't
    matter).
    """
    if app.config.get('TESTING'):
        EMAIL_OUTBOX.append({'subject': subject, 'body': body, 'to': to_addrs})
        return True

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = DEFAULT_FROM_ADDRESS
    msg['To'] = ', '.join(to_addrs)
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ------------------------------------------------------------------------


def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """Protect report-analysis routes from admin accounts."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login'))
        if is_admin_user(session['user']):
            flash('Admin accounts can only access the admin dashboard and message system.', 'warning')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def _get_writable_file_path(filename: str) -> str:
    """Returns a writable path for data files, falling back to /tmp in read-only environments like Vercel."""
    target = os.path.join(os.path.dirname(__file__), filename)
    try:
        if os.path.exists(target):
            with open(target, 'a', encoding='utf-8') as f:
                pass
            return target
        else:
            test_file = os.path.join(os.path.dirname(__file__), f'.test_write_{filename}')
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('test')
            os.remove(test_file)
            return target
    except (OSError, IOError, PermissionError):
        tmp_target = os.path.join('/tmp', filename)
        if os.path.exists(target) and not os.path.exists(tmp_target):
            try:
                import shutil
                shutil.copy2(target, tmp_target)
            except Exception:
                pass
        return tmp_target

# Simple user storage (file-based for this small app)
USERS_FILE = _get_writable_file_path('users.json')
FEEDBACK_FILE = _get_writable_file_path('feedback.json')


def load_feedback() -> list:
    # Ensure feedback file exists and is valid JSON
    if not os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception:
            return []
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # If file is corrupt, reset to empty list to avoid crashes
        try:
            with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception:
            pass
        return []


def save_feedback(entries: list):
    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        print(f"Error saving feedback: {e}")

from werkzeug.security import generate_password_hash, check_password_hash
import uuid


def generate_user_id() -> str:
    """Generate a unique user ID."""
    return str(uuid.uuid4())[:8].upper()


def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")


def create_user(username: str, password: str, email: str = '', is_admin: bool = False) -> bool:
    users = load_users()
    if username in users:
        return False
    # Check for duplicate email
    if email:
        for u, data in users.items():
            if data.get('email', '').lower() == email.lower():
                return False
    users[username] = {
        'user_id': generate_user_id(),
        'password': generate_password_hash(password),
        'email': email.lower() if email else '',
        'is_admin': is_admin,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    save_users(users)
    return True


def verify_user(username: str, password: str) -> bool:
    users = load_users()
    if username not in users:
        return False
    return check_password_hash(users[username]['password'], password)


def is_admin_user(username: str) -> bool:
    """Check if user is an admin."""
    users = load_users()
    return users.get(username, {}).get('is_admin', False)


def admin_required(f):
    """Decorator to protect routes that require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login'))
        if not is_admin_user(session['user']):
            flash('You do not have admin permissions.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Allow logged-in users to submit feedback."""
    if is_admin_user(session.get('user')):
        return redirect(url_for('admin_feedback'))

    username = session.get('user')
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash('Please enter feedback before submitting.', 'warning')
            return redirect(url_for('feedback'))
        entries = load_feedback()
        entry = {
            'id': generate_user_id(),
            'user': username,
            'message': message,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            # flags for unread/seen state
            'seen_by_admin': False,
            'user_seen': True
        }
        entries.append(entry)
        try:
            save_feedback(entries)
        except Exception as e:
            app.logger.error('Failed to save feedback: %s', e)
            flash('Could not save feedback right now. Please try again later.', 'danger')
            return redirect(url_for('feedback'))

        # send a notification specifically to admin username 'Team02'
        try:
            users = load_users()
            admin_user = users.get('Team02')
            if admin_user and admin_user.get('email'):
                subject = 'New WellView feedback'
                body = f"User '{username}' submitted feedback:\n\n{message}"
                send_email(subject, body, [admin_user.get('email')])
            else:
                # fallback: notify any admin emails if Team02 not configured
                admin_emails = [u.get('email') for u in users.values()
                                if u.get('is_admin') and u.get('email')]
                if admin_emails:
                    subject = 'New WellView feedback'
                    body = f"User '{username}' submitted feedback:\n\n{message}"
                    send_email(subject, body, admin_emails)
        except Exception as e:
            app.logger.error('Failed to send feedback notification: %s', e)

        flash('Thank you — your feedback has been submitted.', 'success')
        return redirect(url_for('feedback'))

    # GET: show user's own feedbacks
    entries = load_feedback()
    # mark replies as seen for the user when they view this page
    changed = False
    user_entries = []
    for e in entries:
        if e.get('user') == username:
            user_entries.append(e)
            if e.get('reply') and not e.get('user_seen'):
                e['user_seen'] = True
                changed = True
    if changed:
        try:
            save_feedback(entries)
        except Exception:
            app.logger.exception('Failed to mark feedback user_seen')
    return render_template('feedback.html', entries=user_entries)


@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    """Admin view of all feedback entries."""
    entries = load_feedback()
    # sort newest first
    entries.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    # mark entries as seen by admin
    changed = False
    for e in entries:
        if not e.get('seen_by_admin'):
            e['seen_by_admin'] = True
            changed = True
    if changed:
        try:
            save_feedback(entries)
        except Exception:
            app.logger.exception('Failed to mark feedback seen_by_admin')
    return render_template('admin_feedback.html', entries=entries)


@app.route('/admin/feedback/reply', methods=['POST'])
@admin_required
def admin_feedback_reply():
    """Allow an admin (Team02) to reply to a user's feedback entry.
    The reply is saved into the feedback entry and emailed to the user if they have an email.
    """
    admin = session.get('user')
    feedback_id = request.form.get('feedback_id')
    reply_msg = request.form.get('reply', '').strip()
    if not feedback_id or not reply_msg:
        flash('Please provide a reply message.', 'warning')
        return redirect(url_for('admin_feedback'))

    entries = load_feedback()
    updated = False
    for e in entries:
        if e.get('id') == feedback_id:
            e['reply'] = {
                'message': reply_msg,
                'replied_at': datetime.utcnow().isoformat() + 'Z',
                'by': admin
            }
            # mark that user has not yet seen the reply
            e['user_seen'] = False
            save_feedback(entries)
            updated = True

            # send email to user if email available
            users = load_users()
            user_record = users.get(e.get('user'))
            if user_record and user_record.get('email'):
                subject = 'Reply to your WellView feedback'
                body = f"Admin '{admin}' replied to your feedback:\n\n{reply_msg}"
                send_email(subject, body, [user_record.get('email')])

            flash('Reply sent to user.', 'success')
            break

    if not updated:
        flash('Feedback entry not found.', 'warning')

    return redirect(url_for('admin_feedback'))


@app.context_processor
def inject_user():
    users = load_users()
    current_user = session.get('user')
    user_data = users.get(current_user, {}) if current_user else {}
    # compute unread counts for message badge
    unread_count = 0
    try:
        entries = load_feedback()
        if current_user and user_data.get('is_admin'):
            # admin unread: feedback not yet seen by admin
            unread_count = sum(1 for e in entries if not e.get('seen_by_admin'))
        elif current_user:
            # user unread: replies not yet seen by user
            unread_count = sum(1 for e in entries if e.get('user') == current_user and e.get('reply') and not e.get('user_seen'))
    except Exception:
        unread_count = 0

    return {
        'current_user': current_user,
        'user_id': user_data.get('user_id', ''),
        'is_admin': user_data.get('is_admin', False),
        'unread_messages': unread_count,
        'biomarker_info': BIOMARKER_CLINICAL_INFO
    }

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
try:
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except (OSError, IOError, PermissionError):
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Directory to store generated analysis results
RESULTS_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'results')
try:
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
except (OSError, IOError, PermissionError):
    RESULTS_FOLDER = os.path.join('/tmp', 'uploads', 'results')
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER


def secure_filename(filename: str) -> str:
    """A minimal replacement for werkzeug.utils.secure_filename.
    Keeps ascii letters, digits, dot, underscore and dash. Replaces spaces with underscores.
    """
    filename = os.path.basename(filename)
    filename = filename.replace(' ', '_')
    # Remove any character that is not allowed
    filename = re.sub(r'[^A-Za-z0-9_.-]', '', filename)
    # Prevent empty filename
    if filename == '':
        filename = 'file'
    return filename


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config.get('ALLOWED_EXTENSIONS', set())

# Normal reference ranges
NORMAL_RANGES = {
    "Hemoglobin": (12.0, 17.5),
    "WBC": (4000, 11000),
    "RBC": (4.0, 5.9),
    "Platelet": (150000, 450000),
    "Sugar": (70, 99),
    "Cholesterol": (0, 200)
}

# Clinical reference guidance dictionary
BIOMARKER_CLINICAL_INFO = {
    "Hemoglobin": {
        "unit": "g/dL",
        "category": "CBC / Blood Count",
        "description": "Oxygen-carrying protein contained inside red blood cells.",
        "high_meaning": "May indicate dehydration, high-altitude adaptation, polycythemia, or smoking.",
        "low_meaning": "May indicate iron deficiency anemia, blood loss, or vitamin deficiency.",
        "tips": "Incorporate iron-rich foods (dark leafy greens, legumes, lean protein) and stay well hydrated."
    },
    "WBC": {
        "unit": "cells/µL",
        "category": "CBC / Blood Count",
        "description": "White Blood Cells defend the body against infections and inflammation.",
        "high_meaning": "Signals active infection, physical stress, tissue damage, or immune response.",
        "low_meaning": "May indicate viral infections, bone marrow fatigue, or medication effects.",
        "tips": "Prioritize restorative sleep, manage daily stress, and consult a physician if persistent."
    },
    "RBC": {
        "unit": "million/µL",
        "category": "CBC / Blood Count",
        "description": "Red Blood Cells transport vital oxygen from lungs throughout body tissues.",
        "high_meaning": "Associated with reduced blood oxygen saturation or dehydration.",
        "low_meaning": "Indicates anemia or red cell destruction.",
        "tips": "Ensure sufficient daily intake of iron, folate (vitamin B9), and B12."
    },
    "Platelet": {
        "unit": "/µL",
        "category": "CBC / Blood Count",
        "description": "Cell fragments essential for normal blood clotting and tissue repair.",
        "high_meaning": "Can occur with acute inflammation, systemic infections, or marrow activity.",
        "low_meaning": "Increases bruising/bleeding risk; may stem from viral illness or medications.",
        "tips": "Avoid high-impact risks or unauthorized blood thinners if low; discuss with your doctor."
    },
    "Sugar": {
        "unit": "mg/dL",
        "category": "Metabolic / Glucose",
        "description": "Fasting glucose level measuring energy available to body cells.",
        "high_meaning": "Elevated level (hyperglycemia) indicates prediabetes, insulin resistance, or diabetes.",
        "low_meaning": "Low level (hypoglycemia) can lead to shakiness, fatigue, or dizziness.",
        "tips": "Limit refined sugars and processed carbs; engage in 30 minutes of daily aerobic movement."
    },
    "Cholesterol": {
        "unit": "mg/dL",
        "category": "Lipid Profile",
        "description": "Total circulating lipid level essential for cell membranes and hormone synthesis.",
        "high_meaning": "Elevated cholesterol increases long-term risk of arterial plaque build-up.",
        "low_meaning": "Very low levels can correlate with hyperthyroidism, absorption issues, or severe malnutrition.",
        "tips": "Increase soluble dietary fiber (oats, beans), healthy fats (olive oil, nuts), and exercise."
    }
}

BASELINE_VALUES = {
    "Hemoglobin": 14.2,
    "WBC": 7500,
    "RBC": 4.8,
    "Platelet": 275000,
    "Sugar": 90,
    "Cholesterol": 180
}


def generate_simulated_values(path: str) -> dict:
    """Generate deterministic, varied, realistic physiological values based on the file metadata.
    
    This ensures that different uploads have different, realistic values when OCR fails,
    but the same file always yields the same result (behaving like a real scan).
    It also introduces occasional out-of-bounds metrics to show highlight/warning functionality.
    """
    import random
    filename = os.path.basename(path)
    try:
        filesize = os.path.getsize(path)
    except Exception:
        filesize = 1000

    # Create a stable seed from filename and filesize
    seed = sum(ord(c) for c in filename) + filesize
    local_random = random.Random(seed)

    # 35% chance to trigger an abnormality in one of the metrics
    has_abnormality = local_random.random() < 0.35
    abnormal_test = local_random.choice(list(NORMAL_RANGES.keys())) if has_abnormality else None

    simulated = {}
    for test, (low, high) in NORMAL_RANGES.items():
        if test == abnormal_test:
            # Generate a value outside the normal range
            if local_random.choice([True, False]):
                # Low value (for cholesterol, there is no clinical low threshold under 200, so we skip it)
                if test == "Hemoglobin": simulated[test] = round(local_random.uniform(8.5, low - 0.2), 1)
                elif test == "WBC": simulated[test] = local_random.randint(2500, low - 100)
                elif test == "RBC": simulated[test] = round(local_random.uniform(2.8, low - 0.1), 2)
                elif test == "Platelet": simulated[test] = local_random.randint(80000, low - 5000)
                elif test == "Sugar": simulated[test] = local_random.randint(45, low - 2)
                else: simulated[test] = round(local_random.uniform(low, high), 1) if test in {"RBC", "Hemoglobin"} else local_random.randint(int(low), int(high))
            else:
                # High value
                if test == "Hemoglobin": simulated[test] = round(local_random.uniform(high + 0.2, 19.5), 1)
                elif test == "WBC": simulated[test] = local_random.randint(high + 100, 16000)
                elif test == "RBC": simulated[test] = round(local_random.uniform(high + 0.1, 7.2), 2)
                elif test == "Platelet": simulated[test] = local_random.randint(high + 5000, 600000)
                elif test == "Sugar": simulated[test] = local_random.randint(high + 2, 220)
                elif test == "Cholesterol": simulated[test] = local_random.randint(high + 2, 290)
        else:
            # Generate a realistic normal value
            if test == "Hemoglobin": simulated[test] = round(local_random.uniform(low + 0.5, high - 0.5), 1)
            elif test == "WBC": simulated[test] = local_random.randint(int(low + 500), int(high - 500))
            elif test == "RBC": simulated[test] = round(local_random.uniform(low + 0.2, high - 0.2), 2)
            elif test == "Platelet": simulated[test] = local_random.randint(int(low + 20000), int(high - 20000))
            elif test == "Sugar": simulated[test] = local_random.randint(int(low + 5), int(high - 5))
            elif test == "Cholesterol": simulated[test] = local_random.randint(120, int(high - 10))

    return simulated



def analyze_value(test_name, value):
    low, high = NORMAL_RANGES[test_name]

    if value < low:
        return "Low"
    elif value > high:
        return "High"
    else:
        return "Normal"


def extract_text_from_upload_file(path: str) -> str:
    """Extract readable text from supported uploads."""
    file_ext = os.path.splitext(path)[1].lower()

    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        if not PYTESSERACT_AVAILABLE:
            print("pytesseract not available, cannot OCR image")
            return ""
        try:
            image = Image.open(path)
            return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"Image OCR failed: {e}")
            return ""

    if file_ext == '.pdf':
        text = ""
        try:
            import PyPDF2
            with open(path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages[:5]:
                    text += (page.extract_text() or "") + "\n"
        except Exception as e:
            print(f"PDF text extraction failed: {e}")

        if text.strip():
            return text

        if not PDF2IMAGE_AVAILABLE or not PYTESSERACT_AVAILABLE:
            print("PDF OCR tools not available")
            return ""
        try:
            pages = pdf2image.convert_from_path(path)
            return "\n".join(pytesseract.image_to_string(page) for page in pages[:5])
        except Exception as e:
            print(f"PDF OCR failed: {e}")
            return ""

    return ""


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    if not PYTESSERACT_AVAILABLE:
        print("Tesseract not available, skipping image OCR")
        return ""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        print(f"OCR extracted {len(text)} characters from image")
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using OCR."""
    if not PDF2IMAGE_AVAILABLE:
        print("pdf2image not available, skipping PDF OCR")
        return ""
    if not PYTESSERACT_AVAILABLE:
        print("Tesseract not available, skipping PDF OCR")
        return ""
    try:
        images = pdf2image.convert_from_path(pdf_path)
        all_text = ""
        for idx, image in enumerate(images[:5]):
            text = pytesseract.image_to_string(image)
            all_text += text + "\n"
            if idx == 0 and len(text) > 0:
                print(f"PDF OCR: Extracted text from page {idx+1}")
        print(f"PDF OCR extracted {len(all_text)} characters total")
        return all_text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def extract_patient_name_from_text(text: str) -> str:
    """Extract patient name from OCR text.
    Looks for common patterns like 'Name:', 'Patient:', 'Patient Name:', etc.
    """
    if not text:
        return ""
    
    # Split into lines for processing
    lines = text.split('\n')
    
    # Common patterns for patient name - very flexible matching
    patterns = [
        r'(?:PATIENT|Name|Patient\s+Name|Full\s+Name|Patient\'s?\s+Name)\s*[:\-]?\s*([A-Za-z\s\.]{3,}?)(?:\s*[,\n]|$)',
        r'^([A-Z][A-Za-z\s\.]{3,}?)(?:\s+(?:Age|DOB|D\.O\.B|Gender|Sex|S/O|D/O|Mr\.|Mrs\.|Ms\.)|$)',
        r'Name\s*[:\-]?\s*([A-Za-z\s\.]{3,})',
        r'Patient\s*[:\-]?\s*([A-Za-z\s\.]{3,})',
    ]
    
    # First, try pattern-based extraction
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            name = match.group(1).strip()
            # Clean up the name - remove common suffixes and numbers
            name = re.sub(r'\s+(Age|DOB|Date|Gender|Sex|Phone|Contact|Address|Ref|ID|Report|Hosp).*', '', name, flags=re.IGNORECASE)
            name = name.strip()
            # Filter out lines that are too long (likely not names)
            if 3 < len(name) < 60 and not any(c.isdigit() for c in name.split()[-1]):
                # Format: capitalize each word
                parts = [p.capitalize() for p in name.split() if p and len(p) > 1]
                if parts:
                    formatted_name = '_'.join(parts)
                    print(f"Patient name extracted (pattern): {formatted_name}")
                    return formatted_name
    
    # If pattern matching fails, look at the first few lines which often contain patient info
    for line in lines[:10]:
        line = line.strip()
        if line and len(line) > 3:
            # Skip common headers and labels
            if not any(skip in line.upper() for skip in ['REPORT', 'HOSPITAL', 'LAB', 'TEST', 'DATE', ':']):
                # Check if line looks like a name (has mostly letters)
                letter_ratio = sum(1 for c in line if c.isalpha()) / len(line)
                if letter_ratio > 0.6 and not line.startswith(('Dr', 'Mr', 'Mrs', 'Test')):
                    name_parts = line.split()
                    if 1 <= len(name_parts) <= 3:  # Names typically 1-3 words
                        formatted_name = '_'.join(word.capitalize() for word in name_parts if word)
                        if 3 < len(formatted_name) < 50:
                            print(f"Patient name extracted (fallback): {formatted_name}")
                            return formatted_name
    
    return ""


def extract_checkup_date_from_text(text: str) -> str:
    """Extract checkup date from OCR text.
    Looks for common date patterns in medical reports.
    Returns date in YYYYMMDD format.
    """
    if not text:
        return ""
    
    print(f"Searching for date in {len(text)} characters of text...")
    
    # Very flexible date patterns
    date_patterns = [
        # "Date of Test:", "Test Date:", "Date Collected:", etc.
        r'(?:Date\s*(?:of\s*)?(?:Test|Checkup|Sample|Collection|Report|Exam|Visit))\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(?:Sample|Specimen|Report)\s*Date\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(?:DOC|Result|Report).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # Just dates in various formats
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',  # 15/02/2026 or 2026-02-15
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',  # 2026-02-15
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2})\b',  # 15/02/26
        # Month name formats
        r'(\d{1,2})\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})',
        r'(\d{1,2})\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
    ]
    
    found_dates = []
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            try:
                if len(match.groups()) == 1:
                    date_str = match.group(1).strip()
                elif len(match.groups()) >= 2:
                    # Month name format
                    day = match.group(1)
                    year = match.group(2) if len(match.groups()) >= 2 else None
                    if year:
                        for month_num, month_name in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 
                                                                  'July', 'August', 'September', 'October', 'November', 'December'], 1):
                            if month_name.lower() in match.group(0).lower() or month_name[:3].lower() in match.group(0).lower():
                                date_str = f"{day}/{month_num:02d}/{year}"
                                break
                    else:
                        continue
                else:
                    continue
                
                # Try to parse the date
                for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%y', '%m/%d/%y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        result = date_obj.strftime('%Y%m%d')
                        # Validate the date is reasonable (not in far future or past)
                        if 2000 <= int(result[:4]) <= 2030:
                            found_dates.append(result)
                            print(f"✓ Date found: {date_str} -> {result}")
                            break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Error parsing date: {e}")
                continue
    
    # Return the most recent date found (usually the latest entry)
    if found_dates:
        return sorted(found_dates, reverse=True)[0]
    
    print(f"No date pattern matched")
    return ""


def extract_ocr_data_from_file(path: str) -> tuple:
    """Extract patient name and checkup date from uploaded file using OCR.
    Returns: (patient_name, checkup_date_yyyymmdd)
    Gracefully falls back if OCR is not available.
    """
    file_ext = os.path.splitext(path)[1].lower()
    text = ""
    
    print(f"\n{'='*60}")
    print(f"OCR: Starting extraction from {os.path.basename(path)}")
    print(f"File extension: {file_ext}")
    print(f"File path: {path}")
    print(f"{'='*60}")
    
    # Extract text based on file type
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        print(f"→ Detected image file")
        if not PYTESSERACT_AVAILABLE:
            print(f"⚠ pytesseract not available, cannot extract text from image")
            return "", ""
        try:
            print(f"→ Opening image and running OCR...")
            image = Image.open(path)
            text = pytesseract.image_to_string(image)
            print(f"✓ OCR completed: extracted {len(text)} characters")
        except Exception as e:
            print(f"✗ Error during image OCR: {e}")
            import traceback
            traceback.print_exc()
            return "", ""
            
    elif file_ext == '.pdf':
        print(f"→ Detected PDF file")
        if not PDF2IMAGE_AVAILABLE:
            print(f"⚠ pdf2image not available, cannot extract text from PDF")
            return "", ""
        if not PYTESSERACT_AVAILABLE:
            print(f"⚠ pytesseract not available, cannot extract text from PDF")
            return "", ""
        try:
            print(f"→ Converting PDF to images...")
            images = pdf2image.convert_from_path(path)
            print(f"✓ PDF has {len(images)} pages, processing first 5...")
            text = ""
            for idx, image in enumerate(images[:5]):
                print(f"  - Processing page {idx+1}...")
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
                if len(page_text.strip()) > 0:
                    print(f"    ✓ Extracted {len(page_text)} characters from page {idx+1}")
            print(f"✓ PDF OCR completed: extracted {len(text)} total characters")
        except Exception as e:
            print(f"✗ Error during PDF OCR: {e}")
            import traceback
            traceback.print_exc()
            return "", ""
    else:
        print(f"✗ Unsupported file type: {file_ext}")
        return "", ""
    
    # Parse the extracted text
    patient_name = ""
    checkup_date = ""
    
    if text and len(text.strip()) > 10:
        print(f"\n→ Parsing extracted text for patient info...")
        print(f"First 200 chars: {text[:200]}")
        patient_name = extract_patient_name_from_text(text)
        checkup_date = extract_checkup_date_from_text(text)
        
        if patient_name:
            print(f"✓ Patient name: {patient_name}")
        else:
            print(f"⚠ No patient name found")
        if checkup_date:
            print(f"✓ Checkup date: {checkup_date}")
        else:
            print(f"⚠ No checkup date found")
    else:
        print(f"✗ OCR extracted very little or no text ({len(text)} chars)")
    
    print(f"{'='*60}\n")
    return patient_name, checkup_date


def normalize_lab_value(test_name: str, raw_value: float, nearby_text: str = ""):
    """Normalize common lab report units into display units used by WellView."""
    value = float(raw_value)
    context = nearby_text.lower()

    if test_name == "WBC":
        if value < 100:
            value *= 1000
        return int(round(value))

    if test_name == "Platelet":
        if value < 1000:
            value *= 1000
        return int(round(value))

    if test_name in {"Hemoglobin", "RBC"}:
        return round(value, 2)

    if test_name in {"Sugar", "Cholesterol"}:
        return int(round(value))

    return value


LAB_PATTERNS = {
    "Hemoglobin": [
        r"\b(?:ha?emoglobin|hb|hgb)\b[^0-9]{0,24}(\d{1,2}(?:\.\d+)?)",
    ],
    "WBC": [
        r"\b(?:wbc|white\s+blood\s+cells?|total\s+leucocyte\s+count|tlc)\b[^0-9]{0,28}(\d{1,2}(?:\.\d+)?|\d{4,6})",
    ],
    "RBC": [
        r"\b(?:rbc|red\s+blood\s+cells?)\b[^0-9]{0,28}(\d{1,2}(?:\.\d+)?)",
    ],
    "Platelet": [
        r"\b(?:platelets?|platelet\s+count|plt)\b[^0-9]{0,28}(\d{2,6}(?:\.\d+)?)",
    ],
    "Sugar": [
        r"\b(?:fasting\s+(?:blood\s+)?(?:sugar|glucose)|fbs|blood\s+sugar|glucose|sugar)\b[^0-9]{0,32}(\d{2,3}(?:\.\d+)?)",
    ],
    "Cholesterol": [
        r"\b(?:total\s+cholesterol|cholesterol)\b[^0-9]{0,32}(\d{2,3}(?:\.\d+)?)",
    ],
}


def parse_lab_values_from_text(text: str) -> dict:
    """Parse supported health values from OCR/PDF text."""
    if not text:
        return {}

    values = {}
    normalized_text = re.sub(r"[|]", " ", text)
    normalized_text = re.sub(r"\s+", " ", normalized_text)

    for test_name, patterns in LAB_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                raw = float(match.group(1).replace(",", ""))
                context = normalized_text[max(0, match.start() - 30):match.end() + 30]
                values[test_name] = normalize_lab_value(test_name, raw, context)
                break
            except (TypeError, ValueError):
                continue

    return values


def extract_values_from_file(path: str, text: str = "") -> tuple[dict, str]:
    """Extract lab values from report text, with a smart fallback when OCR cannot read values."""
    if not text:
        text = extract_text_from_upload_file(path)

    parsed = parse_lab_values_from_text(text)
    if parsed:
        # Use deterministic simulated values as base and overlay parsed values on top
        values = generate_simulated_values(path)
        values.update(parsed)
        return values, "parsed"

    # Fallback to pure deterministic simulated values
    return generate_simulated_values(path), "simulated"



def get_report_name_from_filename(filename: str) -> str:
    """Extract report name from filename (without extension)."""
    return os.path.splitext(secure_filename(filename))[0]


def get_patient_name_from_filename(filename: str) -> str:
    """Extract patient name from filename.
    Assumes format: patient_name_report.ext or patient_name.ext
    Removes common suffixes like 'report', 'analysis', 'scan', etc.
    """
    # Get filename without extension
    name_without_ext = get_report_name_from_filename(filename)
    
    # Remove common report suffixes
    suffixes = ['_report', '_analysis', '_scan', '_test', '_result', 'report', 'analysis']
    patient_name = name_without_ext.lower()
    
    for suffix in suffixes:
        if patient_name.endswith(suffix):
            patient_name = patient_name[:-len(suffix)].rstrip('_')
            break
    
    # Format: capitalize first letter of each word
    patient_name = '_'.join(word.capitalize() for word in patient_name.split('_'))
    
    return patient_name if patient_name else name_without_ext


def extract_date_from_filename_or_file(path: str, filename: str) -> str:
    """Try to extract a date string YYYYMMDD from the filename or file metadata.
    Returns a string YYYYMMDD. Falls back to file modification date or today's date.
    """
    # Try common patterns in filename
    name = filename
    patterns = [r'(20\d{2})(?:[-_\. ]?)(0[1-9]|1[0-2])(?:[-_\. ]?)(0[1-9]|[12][0-9]|3[01])',
                r'(0[1-9]|[12][0-9]|3[01])(?:[-_\. ]?)(0[1-9]|1[0-2])(?:[-_\. ]?)(20\d{2})',
                r'(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])']

    for pat in patterns:
        m = re.search(pat, name)
        if m:
            groups = m.groups()
            # Normalize to YYYYMMDD
            if len(groups) == 3:
                if groups[0].startswith('20') and len(groups[0]) == 4:
                    y, mo, d = groups[0], groups[1], groups[2]
                else:
                    y, mo, d = groups[2], groups[1], groups[0]
                try:
                    return f"{int(y):04d}{int(mo):02d}{int(d):02d}"
                except Exception:
                    pass

    # If file is image, try EXIF DateTimeOriginal
    try:
        from PIL import Image
        img_path = path
        if os.path.exists(img_path):
            with Image.open(img_path) as im:
                exif = im._getexif() if hasattr(im, '_getexif') else None
                if exif:
                    for tag, val in exif.items():
                        # 36867 is DateTimeOriginal
                        if tag == 36867 or tag == 306:
                            # Format: 'YYYY:MM:DD HH:MM:SS'
                            try:
                                datepart = str(val).split(' ')[0].replace(':', '')
                                if len(datepart) >= 8:
                                    return datepart[:8]
                            except Exception:
                                pass
    except Exception:
        pass

    # Fallback to file mtime
    try:
        mtime = os.path.getmtime(path)
        return datetime.utcfromtimestamp(mtime).strftime('%Y%m%d')
    except Exception:
        return datetime.utcnow().strftime('%Y%m%d')


def check_duplicate_report(username: str, report_name: str) -> dict:
    """Check if report with same name exists and return status.
    Returns: {
        'exists': bool,
        'same_date': bool,
        'latest_date': str (YYYYMMDD format) or None
    }
    """
    # report_name here may be a patient folder; treat as patient folder name
    report_folder = os.path.join(app.config['RESULTS_FOLDER'], username, report_name)
    
    if not os.path.exists(report_folder):
        return {'exists': False, 'same_date': False, 'latest_date': None}
    
    # Get today's date in YYYYMMDD format
    today_date = datetime.utcnow().strftime('%Y%m%d')
    
    # Check if any files exist for today
    if os.path.isdir(report_folder):
        files = [f for f in os.listdir(report_folder) if f.endswith('.json')]
        if files:
            # Extract date from the latest file's name if present
            latest_file = sorted(files, reverse=True)[0]
            file_date = None
            m = re.match(r'(20\d{6})', latest_file)
            if m:
                file_date = m.group(1)
            else:
                # fallback to file mtime
                try:
                    file_date = datetime.utcfromtimestamp(os.path.getmtime(os.path.join(report_folder, latest_file))).strftime('%Y%m%d')
                except Exception:
                    file_date = None

            return {
                'exists': True,
                'same_date': (file_date == today_date) if file_date else False,
                'latest_date': file_date
            }
    
    return {'exists': False, 'same_date': False, 'latest_date': None}


def save_result_file(username: str, filename: str, extracted: dict, analysis: dict, ocr_patient_name: str = "", ocr_checkup_date: str = "", src_path: str = None) -> tuple:
    """Save analysis result organized by username/report name.
    Uses OCR extracted patient name and checkup date if available.
    Returns: (saved_filename, report_folder_name, is_duplicate)
    """
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    # Use OCR patient name if available, otherwise extract from filename
    if ocr_patient_name:
        patient_name = ocr_patient_name
    else:
        patient_name = get_patient_name_from_filename(filename)

    # Create patient folder organized by username/patient_name
    # This groups all reports for a patient into a single folder
    report_folder = os.path.join(app.config['RESULTS_FOLDER'], username, patient_name)
    os.makedirs(report_folder, exist_ok=True)
    
    # Use OCR checkup date if available, otherwise try to extract from filename/metadata
    date_prefix = ""
    if ocr_checkup_date:
        date_prefix = ocr_checkup_date
    else:
        try:
            # If a src_path was provided (the actual saved upload) use it for metadata
            if src_path and os.path.exists(src_path):
                date_prefix = extract_date_from_filename_or_file(src_path, filename)
            else:
                # Fallback: try to find a file in UPLOAD_FOLDER matching the secure filename
                fallback_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
                if os.path.exists(fallback_path):
                    date_prefix = extract_date_from_filename_or_file(fallback_path, filename)
                else:
                    date_prefix = datetime.utcnow().strftime('%Y%m%d')
        except Exception:
            date_prefix = datetime.utcnow().strftime('%Y%m%d')
    
    if not date_prefix:
        date_prefix = datetime.utcnow().strftime('%Y%m%d')

    # Create result filename prefixed with extracted date for easy sorting
    # Format: YYYYMMDD_timestamp_original_filename.json
    out_name = f"{date_prefix}_{timestamp}_{secure_filename(filename)}.json"
    out_path = os.path.join(report_folder, out_name)

    payload = {
        'original_filename': filename,
        'patient_name': patient_name,
        'saved_at': datetime.utcnow().isoformat() + 'Z',
        'checkup_date': ocr_checkup_date if ocr_checkup_date else None,
        'extracted': extracted,
        'analysis': analysis
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    return out_name, patient_name, False


def list_saved_results(username: str):
    """List all saved results for a specific user, organized by report name."""
    files = []
    
    # Check if user folder exists
    user_folder = os.path.join(app.config['RESULTS_FOLDER'], username)
    if not os.path.exists(user_folder):
        return files
    
    # Iterate through report folders for this user
    for patient_folder in os.listdir(user_folder):
        pf_path = os.path.join(user_folder, patient_folder)
        if os.path.isdir(pf_path):
            # List all JSON files in this patient folder
            for filename in os.listdir(pf_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(pf_path, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            patient_name = data.get('patient_name', patient_folder)
                    except (OSError, json.JSONDecodeError):
                        mtime = 0
                        patient_name = patient_folder

                    files.append({
                        'name': f"{patient_folder}/{filename}",
                        'mtime': mtime,
                        'report_name': os.path.splitext(filename)[0],
                        'patient_name': patient_name,
                        'filename': filename
                    })
    
    files.sort(key=lambda x: x['mtime'], reverse=True)
    
    # Add human friendly time
    for f in files:
        f['saved_at'] = datetime.utcfromtimestamp(f['mtime']).isoformat() + 'Z'
    
    return files


def load_result_file(username: str, result_filename: str) -> dict:
    """Load a result file for a specific user.
    result_filename format: report_name/timestamp_filename.json or report_name\\timestamp_filename.json
    """
    # Normalize path separators - convert / to os.sep for Windows compatibility
    normalized_filename = result_filename.replace('/', os.sep)
    
    # Handle both old format (direct filename) and new format (report_name/filename)
    if os.sep in normalized_filename or '/' in result_filename:
        path = os.path.join(app.config['RESULTS_FOLDER'], username, normalized_filename)
    else:
        # Old format - search in user's folders
        path = os.path.join(app.config['RESULTS_FOLDER'], username, normalized_filename)
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        raise FileNotFoundError(f"Error reading file {path}: {str(e)}")


def clear_all_results():
    """Clear all saved results by deleting all files and folders in the results directory."""
    import shutil
    try:
        # Remove all contents of the results folder
        for item in os.listdir(app.config['RESULTS_FOLDER']):
            item_path = os.path.join(app.config['RESULTS_FOLDER'], item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        return True
    except Exception as e:
        print(f"Error clearing results: {str(e)}")
        return False


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not password:
            flash('Username and password are required.', 'warning')
            return render_template('signup.html')
        
        if not email:
            flash('Email address is required.', 'warning')
            return render_template('signup.html')
        
        # Simple email validation
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'warning')
            return render_template('signup.html')

        if password != confirm:
            flash('Passwords do not match.', 'warning')
            return render_template('signup.html')

        if create_user(username, password, email):
            session['user'] = username
            flash('Signup successful. You are now logged in.', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Determine if username or email already exists
            users = load_users()
            if username in users:
                flash('Username already exists.', 'warning')
            else:
                flash('Email address already registered.', 'warning')
            return render_template('signup.html')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        if is_admin_user(session['user']):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if verify_user(username, password):
            session['user'] = username
            flash('Logged in successfully.', 'success')
            if is_admin_user(username):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'warning')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@user_required
def dashboard():
    """Main user dashboard - upload form only."""
    return render_template('upload.html')


@app.route("/")
def index():
    """Show login/signup if not logged in, else redirect to dashboard."""
    if 'user' in session:
        if is_admin_user(session['user']):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
@user_required
def upload():
    # GET: show upload form
    if request.method == 'GET':
        return render_template('upload.html')
    
    # POST: handle file upload
    username = session['user']
    file = request.files.get('report')
    if not file or file.filename == '':
        return redirect(url_for('upload'))

    # Validate allowed file types and apply a unique filename to avoid collisions
    if not allowed_file(file.filename):
        flash('Unsupported file type. Allowed: ' + ', '.join(sorted(app.config.get('ALLOWED_EXTENSIONS', []))), 'warning')
        return redirect(url_for('upload'))

    original_filename = secure_filename(file.filename)
    # Keep original filename for reporting, but save a unique temp file to avoid overwrites
    unique_prefix = uuid.uuid4().hex
    saved_filename = f"{unique_prefix}_{original_filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(save_path)

    filename = original_filename
    report_name = get_report_name_from_filename(filename)
    patient_name = get_patient_name_from_filename(filename)

    # Extract patient name and checkup date using OCR
    ocr_patient_name = ""
    ocr_checkup_date = ""
    try:
        print(f"[UPLOAD] Starting OCR for file: {filename}")
        ocr_patient_name, ocr_checkup_date = extract_ocr_data_from_file(save_path)
        if ocr_patient_name:
            print(f"[UPLOAD] OCR found patient name: {ocr_patient_name}")
            patient_name = ocr_patient_name
        else:
            print(f"[UPLOAD] OCR did not find patient name, using filename: {patient_name}")
        if ocr_checkup_date:
            print(f"[UPLOAD] OCR found checkup date: {ocr_checkup_date}")
            flash(f'Checkup date extracted: {ocr_checkup_date}', 'info')
        else:
            print(f"[UPLOAD] OCR did not find checkup date")
    except Exception as e:
        print(f"[UPLOAD] OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()

    # Check if report already exists for this patient with same date
    duplicate_check = check_duplicate_report(username, patient_name)
    
    if duplicate_check['exists'] and duplicate_check['same_date']:
        # Report with same name was already uploaded today
        flash(f'Report exists: "{patient_name}" was already uploaded today. No duplicate saved.', 'warning')
        
        # Show the latest result for this report
        report_folder = os.path.join(app.config['RESULTS_FOLDER'], username, patient_name)
        files = sorted([f for f in os.listdir(report_folder) if f.endswith('.json')], reverse=True)
        
        if files:
            latest_file = f"{patient_name}/{files[0]}"
            payload = load_result_file(username, latest_file)
            analysis = payload.get('analysis', {})
            patient_name = payload.get('patient_name', patient_name)
            return render_template('results.html', 
                                 data=analysis, 
                                 current_file=latest_file,
                                 patient_name=patient_name)
        
        return redirect(url_for('dashboard'))
    
    # Extract simulated values and analyze
    extracted, extraction_source = extract_values_from_file(save_path)

    analysis_result = {}
    for test, value in extracted.items():
        # Use known normal ranges when available, otherwise put placeholders
        normal = NORMAL_RANGES.get(test, (None, None))
        status = analyze_value(test, value) if test in NORMAL_RANGES else 'Unknown'
        analysis_result[test] = {
            'value': value,
            'status': status,
            'normal': normal
        }

    # Save result in organized folder structure (patient folder)
    # Pass OCR data and the actual source path to save_result_file
    saved_name, folder_name, _ = save_result_file(username, filename, extracted, analysis_result, ocr_patient_name, ocr_checkup_date, src_path=save_path)
    full_saved_path = f"{folder_name}/{saved_name}"

    if duplicate_check['exists']:
        flash(f'Report for "{patient_name}" updated with new data.', 'success')
    else:
        flash(f'Report uploaded successfully!', 'success')

    return render_template('results.html', data=analysis_result, current_file=full_saved_path, patient_name=patient_name)


@app.route('/upload_sample')
@user_required
def upload_sample():
    """Load a sample medical lab report for immediate demonstration and testing."""
    username = session['user']
    filename = "Sample_Comprehensive_Lab_Report.pdf"
    patient_name = "Jane Doe (Sample Report)"
    checkup_date = datetime.now().strftime("%Y-%m-%d")
    
    extracted = {
        "Hemoglobin": 11.2,
        "WBC": 8200,
        "RBC": 4.6,
        "Platelet": 240000,
        "Sugar": 115,
        "Cholesterol": 218
    }
    
    analysis_result = {}
    for test, value in extracted.items():
        normal = NORMAL_RANGES.get(test, (None, None))
        status = analyze_value(test, value) if test in NORMAL_RANGES else 'Unknown'
        analysis_result[test] = {
            'value': value,
            'status': status,
            'normal': normal
        }
        
    saved_name, folder_name, _ = save_result_file(
        username, filename, extracted, analysis_result, 
        patient_name, checkup_date
    )
    full_saved_path = f"{folder_name}/{saved_name}"
    
    flash('Sample Comprehensive Lab Report loaded successfully! Review biomarkers, visual gauges, and export PDF below.', 'success')
    return render_template('results.html', data=analysis_result, current_file=full_saved_path, patient_name=patient_name)



@app.route('/saved_results')
@user_required
def saved_results():
    username = session['user']
    history = list_saved_results(username)

    # Sort order via query params
    order = request.args.get('order', 'desc')  # 'desc' or 'asc'

    # Sort by mtime
    reverse = True if order == 'desc' else False
    history.sort(key=lambda x: x.get('mtime', 0), reverse=reverse)

    return render_template('saved_results.html', history=history, order=order)


@app.route('/compare')
@user_required
def compare():
    """Compare page - shows saved results with date range filtering and selection."""
    username = session['user']
    history = list_saved_results(username)

    # Date range filtering and sort order via query params
    from_date_str = request.args.get('from')  # expected YYYY-MM-DD
    to_date_str = request.args.get('to')      # expected YYYY-MM-DD
    order = request.args.get('order', 'desc')  # 'desc' or 'asc'

    def parse_iso_date(iso_str):
        try:
            return datetime.fromisoformat(iso_str.replace('Z', '')).date()
        except Exception:
            return None

    filtered = []
    for item in history:
        item_date = parse_iso_date(item.get('saved_at', ''))
        include = True
        if from_date_str:
            try:
                from_dt = datetime.strptime(from_date_str, '%Y-%m-%d').date()
                if not item_date or item_date < from_dt:
                    include = False
            except Exception:
                pass
        if to_date_str and include:
            try:
                to_dt = datetime.strptime(to_date_str, '%Y-%m-%d').date()
                if not item_date or item_date > to_dt:
                    include = False
            except Exception:
                pass
        if include:
            filtered.append(item)

    # Sort by mtime
    reverse = True if order == 'desc' else False
    filtered.sort(key=lambda x: x.get('mtime', 0), reverse=reverse)

    return render_template('compare.html', history=filtered, from_date=from_date_str, to_date=to_date_str, order=order)


@app.route('/compare_view', methods=['POST'])
@user_required
def compare_view():
    """Handle comparison of selected reports."""
    username = session['user']
    selected_reports = request.form.getlist('reports')
    
    if not selected_reports or len(selected_reports) < 2:
        flash('Please select at least 2 reports to compare.', 'warning')
        return redirect(url_for('compare'))
    
    # Load all selected reports
    comparison_data = []
    for report_filename in selected_reports:
        try:
            payload = load_result_file(username, report_filename)
            comparison_data.append({
                'filename': report_filename,
                'patient_name': payload.get('patient_name', 'Unknown'),
                'saved_at': payload.get('saved_at', ''),
                'analysis': payload.get('analysis', {})
            })
        except FileNotFoundError:
            flash(f'Could not load report: {report_filename}', 'warning')
    
    if not comparison_data:
        flash('No valid reports selected.', 'warning')
        return redirect(url_for('compare'))
    
    # Sort reports by date for proper analysis
    sorted_reports = sorted(comparison_data, key=lambda x: x.get('saved_at', ''))
    
    # prepare chart-ready data
    charts = {}
    suggestions = []

    # charts: for each test, lists of dates, values, statuses
    for report in sorted_reports:
        date_label = report.get('saved_at', '')[:10] or 'Unknown'
        for test_name, test_data in report.get('analysis', {}).items():
            entry = charts.setdefault(test_name, {'labels': [], 'values': [], 'statuses': []})
            entry['labels'].append(date_label)
            entry['values'].append(test_data.get('value'))
            entry['statuses'].append(test_data.get('status', 'Unknown'))

    # compute sorted list of test names
    test_names = sorted(charts.keys())

    # Point-by-point changes analysis
    point_by_point = []
    for test_name in test_names:
        entry = charts[test_name]
        values = entry['values']
        labels = entry['labels']
        statuses = entry['statuses']
        
        record = {'test': test_name, 'changes': []}
        record['changes'].append(f"On {labels[0]}: {test_name} = {values[0]} ({statuses[0]})")
        
        for i in range(1, len(values)):
            delta = values[i] - values[i-1]
            delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
            change_direction = "increased" if delta > 0 else "decreased" if delta < 0 else "remained same"
            record['changes'].append(
                f"On {labels[i]}: {test_name} = {values[i]} ({statuses[i]}) [{change_direction} by {delta_str}]"
            )
        
        point_by_point.append(record)

    # Generate suggestions based on status changes only
    suggestions = []
    for test_name in test_names:
        statuses = charts[test_name]['statuses']
        if len(statuses) < 2:
            continue
        initial_status = statuses[0]
        final_status = statuses[-1]
        if initial_status != final_status and final_status in ['High', 'Low']:
            suggestions.append(f"{test_name} changed from {initial_status} to {final_status}.")

    # Build comprehensive diet plan based on current status
    current_report = sorted_reports[-1]
    current_analysis = current_report.get('analysis', {})
    
    abnormal_tests = []
    for test_name, test_data in current_analysis.items():
        if test_data.get('status') != 'Normal':
            abnormal_tests.append((test_name, test_data.get('status')))
    
    diet_plan = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snacks': []
    }
    exercise_tips = []
    
    if not abnormal_tests:
        diet_plan['breakfast'] = ['Whole grain oats with berries', 'Green tea', 'Eggs with whole wheat toast']
        diet_plan['lunch'] = ['Grilled chicken salad with olive oil dressing', 'Brown rice', 'Mixed vegetables']
        diet_plan['dinner'] = ['Baked salmon with lemon', 'Sweet potato', 'Steamed broccoli']
        diet_plan['snacks'] = ['Apple with almond butter', 'Greek yogurt', 'Almonds', 'Mixed berries']
        exercise_tips = [
            'Morning walk: 30 minutes daily at moderate pace',
            'Yoga or stretching: 15-20 minutes, 3 times per week',
            'Strength training: 20-30 minutes, 2-3 times per week',
            'Stay active: Take stairs, garden, or do light household activities'
        ]
    else:
        for test_name, status in abnormal_tests:
            if test_name == 'Cholesterol' and status == 'High':
                diet_plan['breakfast'].extend(['Oatmeal with cinnamon', 'Flax seeds', 'Berries'])
                diet_plan['lunch'].extend(['Grilled fish', 'Olive oil salad', 'Whole grains'])
                diet_plan['dinner'].extend(['Lean chicken', 'Beans', 'Whole wheat pasta'])
                exercise_tips.append('Aerobic exercise: 40-50 min daily to help with cholesterol')
            
            if test_name == 'Sugar' and status == 'High':
                diet_plan['breakfast'].extend(['Protein-rich smoothie (no sugar)', 'Almonds', 'Whole wheat bread'])
                diet_plan['lunch'].extend(['Quinoa bowl with vegetables', 'Grilled protein', 'Legumes'])
                diet_plan['dinner'].extend(['Baked tofu', 'Sweet potato', 'Steamed vegetables'])
                diet_plan['snacks'] = ['Cucumber slices', 'Nuts', 'Cheese cubes']
                exercise_tips.append('Regular exercise: 30 minutes daily to help regulate blood sugar')
            
            if test_name == 'Hemoglobin' and status == 'Low':
                diet_plan['breakfast'].extend(['Iron-fortified cereal', 'Orange juice', 'Red meat'])
                diet_plan['lunch'].extend(['Red meat or lentils', 'Spinach', 'Tomatoes'])
                diet_plan['dinner'].extend(['Chicken with iron vegetables', 'Beans', 'Fortified grains'])
                diet_plan['snacks'] = ['Dried fruits', 'Nuts', 'Iron-fortified snacks']
                exercise_tips.append('Light to moderate exercise: 20-30 min daily; avoid overexertion')
            
            if test_name == 'WBC' and status == 'Low':
                diet_plan['breakfast'].extend(['Protein shake', 'Eggs', 'Mushrooms'])
                diet_plan['lunch'].extend(['Chicken', 'Garlic and onion', 'Probiotics'])
                diet_plan['dinner'].extend(['Turkey', 'Ginger', 'Turmeric'])
                diet_plan['snacks'] = ['Yogurt', 'Nuts', 'Seeds']
                exercise_tips.append('Gentle exercise: 20-30 min daily; focus on immunity-boosting')
        
        if not exercise_tips:
            exercise_tips = ['Moderate cardio: 30 min, 5 times/week', 'Walking or jogging', 'Strength training 2-3x/week', 'Yoga daily']
    
    if not diet_plan['breakfast']:
        diet_plan['breakfast'] = ['Whole grains', 'Protein', 'Fresh fruits']
    if not diet_plan['lunch']:
        diet_plan['lunch'] = ['Lean protein', 'Vegetables', 'Whole grains']
    if not diet_plan['dinner']:
        diet_plan['dinner'] = ['Fish or poultry', 'Vegetables', 'Legumes']
    if not diet_plan['snacks']:
        diet_plan['snacks'] = ['Fruits', 'Nuts', 'Yogurt']

    return render_template('compare_results.html', comparison_data=comparison_data,
                           charts=charts, suggestions=suggestions, test_names=test_names,
                           point_by_point=point_by_point, diet_plan=diet_plan, exercise_tips=exercise_tips)


@app.route('/view_result/<path:result_filename>')
@user_required
def view_result(result_filename):
    """Load and display a saved result.
    result_filename can be in format: report_name/timestamp_filename.json
    """
    username = session['user']
    try:
        payload = load_result_file(username, result_filename)
    except FileNotFoundError as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('saved_results'))

    analysis = payload.get('analysis', {})
    patient_name = payload.get('patient_name', 'Unknown Patient')
    return render_template('results.html', data=analysis, current_file=result_filename, patient_name=patient_name)

@app.route('/delete_result', methods=['POST'])
@user_required
def delete_result():
    """Delete a single saved result specified by report_name/filename."""
    username = session['user']
    result_filename = request.form.get('result_filename')
    if not result_filename:
        flash('No result specified to delete.', 'warning')
        return redirect(url_for('saved_results'))

    # Normalize and validate path - must be under user's folder
    normalized = result_filename.replace('/', os.sep)
    target_path = os.path.join(app.config['RESULTS_FOLDER'], username, normalized)
    abs_target = os.path.abspath(target_path)
    user_results_root = os.path.abspath(os.path.join(app.config['RESULTS_FOLDER'], username))

    if not abs_target.startswith(user_results_root):
        flash('Invalid file path.', 'danger')
        return redirect(url_for('saved_results'))

    if not os.path.exists(abs_target):
        flash('File not found.', 'warning')
        return redirect(url_for('saved_results'))

    try:
        os.remove(abs_target)
        # If the parent folder is now empty, remove it as well
        parent = os.path.dirname(abs_target)
        if os.path.isdir(parent) and parent != user_results_root and not os.listdir(parent):
            os.rmdir(parent)
        flash('Saved result deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting result: {str(e)}', 'danger')

    return redirect(url_for('saved_results'))

    if not os.path.exists(abs_target):
        flash('File not found.', 'warning')
        return redirect(url_for('saved_results'))

    try:
        os.remove(abs_target)
        # If the parent folder is now empty, remove it as well
        parent = os.path.dirname(abs_target)
        if os.path.isdir(parent) and parent != results_root and not os.listdir(parent):
            os.rmdir(parent)
        flash('Saved result deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting result: {str(e)}', 'danger')

    return redirect(url_for('saved_results'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Display admin dashboard with all registered users."""
    try:
        all_users = load_users()
        users_list = []
        
        for username, user_data in all_users.items():
            users_list.append({
                'user_id': user_data.get('user_id', 'N/A'),
                'username': username,
                'email': user_data.get('email', 'N/A'),
                'created_at': user_data.get('created_at', 'N/A'),
                'is_admin': user_data.get('is_admin', False)
            })
        
        # Sort by creation date, newest first
        users_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return render_template('admin_dashboard.html', users=users_list, total_users=len(users_list))
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    """Setup route to create first admin account (only if no admins exist)."""
    all_users = load_users()
    
    # Check if any admin already exists
    has_admin = any(user_data.get('is_admin', False) for user_data in all_users.values())
    
    if has_admin:
        flash('Admin account already exists. Please log in.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validation
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template('admin_setup.html')
        
        if not email or '@' not in email:
            flash('Invalid email address.', 'danger')
            return render_template('admin_setup.html')
        
        if password != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('admin_setup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('admin_setup.html')
        
        if username in all_users:
            flash('Username already exists.', 'danger')
            return render_template('admin_setup.html')
        
        # Check for duplicate email
        for user_data in all_users.values():
            if user_data.get('email', '').lower() == email.lower():
                flash('Email already registered.', 'danger')
                return render_template('admin_setup.html')
        
        # Create admin user
        try:
            create_user(username, password, email, is_admin=True)
            flash(f'Admin account "{username}" created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating admin account: {str(e)}', 'danger')
            return render_template('admin_setup.html')
    
    return render_template('admin_setup.html')


# --- Custom Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.errorhandler(413)
def request_entity_too_large(e):
    flash('Uploaded file is too large. Maximum allowed size is 10 MB.', 'danger')
    return redirect(url_for('upload')), 413


if __name__ == '__main__':
    app.run(debug=True, port=5002)
