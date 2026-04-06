import os
import json
import firebase_admin
from firebase_admin import credentials, db, storage
import utils

# Firebase Initialization
SERVICE_ACCOUNT_PATH = 'serviceAccountKey.json'
if not os.path.exists(SERVICE_ACCOUNT_PATH):
    print("Error: serviceAccountKey.json not found!")
    exit(1)

cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': f'https://{cred.project_id}-default-rtdb.firebaseio.com/',
        'storageBucket': f'{cred.project_id}.appspot.com'
    })

bucket = storage.bucket()

def upload_image(local_path, folder_name):
    """Uploads a local image to Firebase Storage and returns its public URL."""
    if not os.path.exists(local_path):
        return None
    
    # Create a unique blob name
    filename = os.path.basename(local_path)
    blob_name = f"static/images/{folder_name}/{filename}"
    blob = bucket.blob(blob_name)
    
    # Upload
    with open(local_path, 'rb') as f:
        blob.upload_from_file(f)
    
    # Make public
    blob.make_public()
    return blob.public_url

def migrate_json_file(filename, folder_name, image_fields):
    """
    Migrates a JSON file to Firebase RTDB, uploading images along the way.
    image_fields: list of paths to image fields in the object (e.g., ['image', 'hod.image', 'labs[].image'])
    """
    print(f"Migrating {filename}...")
    local_data_path = os.path.join('data', filename)
    if not os.path.exists(local_data_path):
        print(f"  Skipping {filename}: Local file not found.")
        return

    with open(local_data_path, 'r') as f:
        data = json.load(f)

    # Helper to recursively update image fields
    def process_item(item):
        if not isinstance(item, dict):
            return item
        
        # News/Faculty standard 'image' field
        for field in image_fields:
            if '[' in field: # Array of objects (like labs[].image)
                base, subfield = field.split('[].')
                if base in item and isinstance(item[base], list):
                    for subitem in item[base]:
                        if subfield in subitem:
                            img_val = subitem[subfield]
                            if img_val and not img_val.startswith('http'):
                                local_img = os.path.join('static/images', base if base != 'labs' else 'labs', img_val)
                                new_url = upload_image(local_img, base if base != 'labs' else 'labs')
                                if new_url:
                                    subitem[subfield] = new_url
            
            elif '.' in field: # Nested object (like hod.image)
                parts = field.split('.')
                curr = item
                for part in parts[:-1]:
                    if part in curr:
                        curr = curr[part]
                last = parts[-1]
                if last in curr:
                    img_val = curr[last]
                    if img_val and not img_val.startswith('http'):
                        # Determine folder name based on context
                        local_img = os.path.join('static/images', folder_name, img_val)
                        new_url = upload_image(local_img, folder_name)
                        if new_url:
                            curr[last] = new_url
            else: # Standard field (like 'image')
                if field in item:
                    img_val = item[field]
                    if img_val and not img_val.startswith('http'):
                        local_img = os.path.join('static/images', folder_name, img_val)
                        new_url = upload_image(local_img, folder_name)
                        if new_url:
                            item[field] = new_url
        return item

    if isinstance(data, list):
        for item in data:
            process_item(item)
    elif isinstance(data, dict):
        if 'stories' in data: # Special case for placements.json
            for story in data['stories']:
                process_item(story)
        else:
            process_item(data)

    # Save to Firebase
    key = filename.replace('.json', '')
    ref = db.reference(key)
    ref.set(data)
    print(f"  Successfully migrated {filename} to Firebase.")

if __name__ == '__main__':
    # Define migration map
    migrations = [
        ('news.json', 'news', ['image']),
        ('faculty.json', 'faculty', ['image']),
        ('departments.json', 'departments', ['hod.image', 'labs[].image']),
        ('gallery.json', 'gallery', ['image']),
        ('placements.json', 'placements', ['image']), # Stories handled specially in function
        ('facilities.json', 'facilities', ['image']),
        ('activities.json', 'activities', ['image']),
        ('leadership.json', 'leadership', ['image']),
        ('announcements.json', 'none', []), # No images
        ('academics.json', 'none', []), # No images
        ('library.json', 'none', []), # No images
        ('governance.json', 'none', []), # No images
    ]

    for filename, folder, img_fields in migrations:
        print(f"\n--- Starting Migration for {filename} ---")
        try:
            migrate_json_file(filename, folder, img_fields)
        except Exception as e:
            print(f"!!! Failed to migrate {filename}: {e}")
            import traceback
            traceback.print_exc()

    print("\nMigration complete! Your data is now live on Firebase.")
