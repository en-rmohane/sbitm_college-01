import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_json(filename):
    """Loads data from a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_json(filename, data):
    """Saves data to a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def get_faculty_by_dept(faculty_list):
    """Groups faculty by department for display."""
    grouped = {}
    for fac in faculty_list:
        dept = fac.get('department', 'Other')
        if dept not in grouped:
            grouped[dept] = []
        grouped[dept].append(fac)
    return grouped
