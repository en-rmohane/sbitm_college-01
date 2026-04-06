import json
import os
import firebase_admin
from firebase_admin import credentials, db, storage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Firebase Initialization
# Use service account file if it exists, otherwise assume environment variables (for Vercel)
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, 'serviceAccountKey.json')

if not firebase_admin._apps:
    if os.path.exists(SERVICE_ACCOUNT_PATH):
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    else:
        # Fallback for Vercel Environment Variables
        import json as py_json
        cred_dict = {
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        # Only try if at least one crucial var is set
        if cred_dict["project_id"]:
            cred = credentials.Certificate(cred_dict)
        else:
            cred = None

    if cred:
        firebase_admin.initialize_app(cred, {
            'databaseURL': f'https://{cred.project_id}-default-rtdb.firebaseio.com/',
            'storageBucket': f'{cred.project_id}.appspot.com'
        })
    else:
        print("Warning: Firebase not initialized. Using local filesystem fallback.")

def load_json(filename):
    """Loads data from Firebase RTDB if available, otherwise from local JSON."""
    # Use filename without .json as key
    key = filename.replace('.json', '')
    
    if firebase_admin._apps:
        try:
            ref = db.reference(key)
            data = ref.get()
            if data is not None:
                return data
        except Exception as e:
            print(f"Firebase read error for {key}: {e}")

    # Fallback to local
    filepath = os.path.join(BASE_DIR, 'data', filename)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def save_json(filename, data):
    """Saves data to Firebase RTDB if available, otherwise to local JSON."""
    key = filename.replace('.json', '')
    
    if firebase_admin._apps:
        try:
            ref = db.reference(key)
            ref.set(data)
            return True
        except Exception as e:
            print(f"Firebase save error for {key}: {e}")

    # Fallback to local
    filepath = os.path.join(BASE_DIR, 'data', filename)
    try:
        # Ensure data dir exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except OSError as e:
        print(f"Local save error for {filename}: {e}")
        return False

def get_faculty_by_dept(faculty_list):
    """Groups faculty by department for display."""
    grouped = {}
    for fac in faculty_list:
        dept = fac.get('department', 'Other')
        if dept not in grouped:
            grouped[dept] = []
        grouped[dept].append(fac)
    return grouped
