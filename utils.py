import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On Vercel, the filesystem is read-only except for /tmp
if os.environ.get('VERCEL'):
    DATA_DIR = '/tmp/data'
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            # Copy initial data files from source to /tmp if they don't exist
            # This allows the app to read initial data and then "override" it in /tmp
            SOURCE_DATA_DIR = os.path.join(BASE_DIR, 'data')
            if os.path.exists(SOURCE_DATA_DIR):
                import shutil
                for item in os.listdir(SOURCE_DATA_DIR):
                    s = os.path.join(SOURCE_DATA_DIR, item)
                    d = os.path.join(DATA_DIR, item)
                    if os.path.isfile(s) and not os.path.exists(d):
                        shutil.copy2(s, d)
        except OSError:
            DATA_DIR = os.path.join(BASE_DIR, 'data') # Fallback to original
else:
    DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_json(filename):
    """Loads data from a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    
    # If file doesn't exist in /tmp, try reading from original data dir
    if not os.path.exists(filepath):
        alt_path = os.path.join(BASE_DIR, 'data', filename)
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            return []
            
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def save_json(filename, data):
    """Saves data to a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except OSError as e:
        if e.errno == 30:
            print(f"Warning: Cannot save {filename}. Read-only filesystem.")
        else:
            raise

def get_faculty_by_dept(faculty_list):
    """Groups faculty by department for display."""
    grouped = {}
    for fac in faculty_list:
        dept = fac.get('department', 'Other')
        if dept not in grouped:
            grouped[dept] = []
        grouped[dept].append(fac)
    return grouped
