import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
import utils
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey' # Needed for flash messages
app.config['UPLOAD_FOLDER'] = 'static/images/faculty'
app.config['GALLERY_FOLDER'] = 'static/images/gallery'
app.config['NEWS_FOLDER'] = 'static/images/news'
app.config['PLACEMENTS_FOLDER'] = 'static/images/placements'
app.config['FACILITIES_FOLDER'] = 'static/images/facilities'
app.config['ACTIVITIES_FOLDER'] = 'static/images/activities'
app.config['LABS_FOLDER'] = 'static/images/labs'

# Admin Credentials (Hardcoded for simplicity)
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = 'password123'

# Helper for directory creation (handles read-only systems like Vercel)
def safe_makedirs(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        if e.errno == 30: # Read-only file system
            print(f"Warning: Could not create directory {path} (Read-only filesystem)")
        else:
            raise

# Helper to save uploaded files safely (handles Firebase Cloud Storage)
def save_file_safely(file, folder):
    filename = secure_filename(file.filename)
    if not filename:
        return ""
        
    # Standard path for local development fallback or if Firebase is not available
    target_path = os.path.join(folder, filename)
    
    # Firebase Storage Upload
    from firebase_admin import storage
    try:
        bucket = storage.bucket()
        if bucket:
            # Create a unique blob name using UUID to avoid collisions
            ext = os.path.splitext(filename)[1]
            blob_name = f"{folder}/{uuid.uuid4()}{ext}"
            blob = bucket.blob(blob_name)
            
            # Reset file pointer and upload
            file.seek(0)
            blob.upload_from_file(file, content_type=file.content_type)
            
            # Make the blob publicly viewable
            blob.make_public()
            print(f"Uploaded to Firebase: {blob.public_url}")
            return blob.public_url
    except Exception as e:
        print(f"Firebase Storage upload error: {e}")

    # Fallback to local /tmp on Vercel or local static folder
    try:
        base_folder = '/tmp' if os.environ.get('VERCEL') else '.'
        full_folder = os.path.join(base_folder, folder)
        os.makedirs(full_folder, exist_ok=True)
        
        final_path = os.path.join(full_folder, filename)
        file.seek(0)
        file.save(final_path)
        return filename
    except Exception as e:
        print(f"Fallback save error: {e}")
        return ""

# Custom route to serve static files from /tmp on Vercel
@app.route('/static/images/<path:filename>')
def serve_tmp_images(filename):
    from flask import send_from_directory
    # Try standard static first
    static_folder = os.path.join(app.root_path, 'static', 'images')
    if os.path.exists(os.path.join(static_folder, filename)):
        return send_from_directory(static_folder, filename)
    
    # Fallback to /tmp
    tmp_folder = os.path.join('/tmp', 'static', 'images')
    return send_from_directory(tmp_folder, filename)

@app.route('/favicon.ico')
def favicon_ico():
    return app.send_static_file('favicon.ico')

@app.route('/favicon.png')
def favicon_png():
    return app.send_static_file('favicon.png')

# Ensure upload directory exists locally (won't affect Vercel root but good for local)
if not os.environ.get('VERCEL'):
    safe_makedirs(app.config['UPLOAD_FOLDER'])
    safe_makedirs(app.config['GALLERY_FOLDER'])
    safe_makedirs(app.config['NEWS_FOLDER'])
    safe_makedirs(app.config['PLACEMENTS_FOLDER'])
    safe_makedirs(app.config['FACILITIES_FOLDER'])
    safe_makedirs(app.config['ACTIVITIES_FOLDER'])
    safe_makedirs(app.config['LABS_FOLDER'])

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    news_items = utils.load_json('news.json')
    placement_data = utils.load_json('placements.json')
    stories = placement_data.get('stories', []) if placement_data else []
    announcements = utils.load_json('announcements.json')
    return render_template('index.html', news=news_items, stories=stories, announcements=announcements)

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    stats = {
        'faculty': len(utils.load_json('faculty.json')),
        'news': len(utils.load_json('news.json')),
        'activities': len(utils.load_json('activities.json'))
    }
    return render_template('admin/dashboard.html', stats=stats)

# --- Faculty Management ---
@app.route('/admin/faculty', methods=['GET', 'POST'])
@login_required
def manage_faculty():
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        role = request.form.get('role')
        designation = request.form.get('designation')
        bio = request.form.get('bio')
        experience = request.form.get('experience')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        specialization = request.form.get('specialization')
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        new_faculty = {
            "id": str(uuid.uuid4()),
            "name": name,
            "department": department,
            "role": role,
            "designation": designation,
            "image": image_filename,
            "bio": bio,
            "experience": experience,
            "email": email,
            "qualification": qualification,
            "specialization": specialization
        }
        
        faculty_list = utils.load_json('faculty.json')
        faculty_list.append(new_faculty)
        utils.save_json('faculty.json', faculty_list)
        flash('Faculty member added successfully!', 'success')
        return redirect(url_for('manage_faculty'))
        
    faculty_list = utils.load_json('faculty.json')
    departments_list = utils.load_json('departments.json')
    return render_template('admin/manage_faculty.html', faculty=faculty_list, departments=departments_list)

@app.route('/admin/faculty/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_faculty(id):
    faculty_list = utils.load_json('faculty.json')
    faculty_member = next((f for f in faculty_list if f['id'] == id), None)
    
    if not faculty_member:
        flash('Faculty member not found.', 'danger')
        return redirect(url_for('manage_faculty'))

    if request.method == 'POST':
        faculty_member['name'] = request.form.get('name')
        faculty_member['department'] = request.form.get('department')
        faculty_member['role'] = request.form.get('role')
        faculty_member['designation'] = request.form.get('designation')
        faculty_member['bio'] = request.form.get('bio')
        faculty_member['experience'] = request.form.get('experience')
        faculty_member['email'] = request.form.get('email')
        faculty_member['qualification'] = request.form.get('qualification')
        faculty_member['specialization'] = request.form.get('specialization')
        
        # Handle Image Upload - Only update if a new file is provided
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                faculty_member['image'] = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        utils.save_json('faculty.json', faculty_list)
        flash('Faculty details updated!', 'success')
        return redirect(url_for('manage_faculty'))
        
    departments_list = utils.load_json('departments.json')
    return render_template('admin/edit_faculty.html', faculty=faculty_member, departments=departments_list)

@app.route('/admin/faculty/delete/<id>')
@login_required
def delete_faculty(id):
    faculty_list = utils.load_json('faculty.json')
    faculty_list = [f for f in faculty_list if f['id'] != id]
    utils.save_json('faculty.json', faculty_list)
    flash('Faculty member deleted.', 'info')
    return redirect(url_for('manage_faculty'))

# --- News Management ---
@app.route('/admin/news', methods=['GET', 'POST'])
@login_required
def manage_news():
    if request.method == 'POST':
        title = request.form.get('title')
        date = request.form.get('date')
        description = request.form.get('description')
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = save_file_safely(file, app.config['NEWS_FOLDER'])
        
        new_item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "date": date,
            "description": description,
            "image": image_filename if image_filename else "https://via.placeholder.com/400x250"
        }
        
        news_list = utils.load_json('news.json')
        news_list.append(new_item)
        utils.save_json('news.json', news_list)
        flash('News item added!', 'success')
        return redirect(url_for('manage_news'))
        
    news_list = utils.load_json('news.json')
    return render_template('admin/manage_news.html', news=news_list)

@app.route('/admin/news/delete/<id>')
@login_required
def delete_news(id):
    news_list = utils.load_json('news.json')
    news_list = [n for n in news_list if n['id'] != id]
    utils.save_json('news.json', news_list)
    flash('News item deleted.', 'info')
    return redirect(url_for('manage_news'))

@app.route('/admin/news/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    news_list = utils.load_json('news.json')
    item = next((n for n in news_list if n['id'] == id), None)
    
    if not item:
        flash('News item not found.', 'danger')
        return redirect(url_for('manage_news'))

    if request.method == 'POST':
        item['title'] = request.form.get('title')
        item['date'] = request.form.get('date')
        item['description'] = request.form.get('description')
        
        # Handle Image Upload - Only update if a new file is provided
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                item['image'] = save_file_safely(file, app.config['NEWS_FOLDER'])

        utils.save_json('news.json', news_list)
        flash('News item updated successfully!', 'success')
        return redirect(url_for('manage_news'))
        
    return render_template('admin/edit_news.html', item=item)

# --- Announcement Management ---
@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required
def manage_announcements():
    if request.method == 'POST':
        text = request.form.get('text')
        if text:
            announcements = utils.load_json('announcements.json')
            new_announcement = {
                "id": str(uuid.uuid4()),
                "text": text
            }
            announcements.append(new_announcement)
            utils.save_json('announcements.json', announcements)
            flash('Announcement added successfully!', 'success')
        return redirect(url_for('manage_announcements'))
        
    announcements = utils.load_json('announcements.json')
    return render_template('admin/manage_announcements.html', announcements=announcements)

@app.route('/admin/announcements/delete/<id>')
@login_required
def delete_announcement(id):
    announcements = utils.load_json('announcements.json')
    announcements = [a for a in announcements if a['id'] != id]
    utils.save_json('announcements.json', announcements)
    flash('Announcement deleted.', 'info')
    return redirect(url_for('manage_announcements'))

# --- Gallery Management ---
@app.route('/admin/gallery', methods=['GET', 'POST'])
@login_required
def manage_gallery():
    if request.method == 'POST':
        caption = request.form.get('caption')
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = save_file_safely(file, app.config['GALLERY_FOLDER'])
        
        if image_filename:
            new_item = {
                "id": str(uuid.uuid4()),
                "caption": caption,
                "image": image_filename
            }
            
            gallery_list = utils.load_json('gallery.json')
            gallery_list.append(new_item)
            utils.save_json('gallery.json', gallery_list)
            flash('Image added to gallery!', 'success')
        else:
             flash('Please upload an image.', 'danger')
             
        return redirect(url_for('manage_gallery'))
        
    gallery_list = utils.load_json('gallery.json')
    return render_template('admin/manage_gallery.html', gallery=gallery_list)

@app.route('/admin/gallery/delete/<id>')
@login_required
def delete_gallery(id):
    gallery_list = utils.load_json('gallery.json')
    gallery_list = [g for g in gallery_list if g['id'] != id]
    utils.save_json('gallery.json', gallery_list)
    flash('Image deleted.', 'info')
    return redirect(url_for('manage_gallery'))

# --- Placement Management ---
@app.route('/admin/placements', methods=['GET', 'POST'])
@login_required
def manage_placements():
    data = utils.load_json('placements.json')
    if not data:
         data = {"stats": {}, "recruiters": [], "stories": []}

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_stats':
            data['stats']['percentage'] = request.form.get('percentage')
            data['stats']['highest_package'] = request.form.get('highest_package')
            data['stats']['recruiters_count'] = request.form.get('recruiters_count')
            flash('Stats updated!', 'success')
            
        elif action == 'update_recruiters':
            recruiters_str = request.form.get('recruiters')
            data['recruiters'] = [r.strip() for r in recruiters_str.split(',')]
            flash('Recruiters list updated!', 'success')
            
        elif action == 'add_story':
            # Handle Image Upload
            image_filename = ""
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    image_filename = save_file_safely(file, app.config['PLACEMENTS_FOLDER'])

            new_story = {
                "id": str(uuid.uuid4()),
                "name": request.form.get('name'),
                "company": request.form.get('company'),
                "package": request.form.get('package'),
                "quote": request.form.get('quote'),
                "image": image_filename if image_filename else "https://via.placeholder.com/100"
            }
            if 'stories' not in data: data['stories'] = []
            data['stories'].append(new_story)
            flash('Success story added!', 'success')
            
        utils.save_json('placements.json', data)
        return redirect(url_for('manage_placements'))
        
    return render_template('admin/manage_placements.html', data=data)

@app.route('/admin/placements/delete_story/<id>')
@login_required
def delete_story(id):
    data = utils.load_json('placements.json')
    if 'stories' in data:
        data['stories'] = [s for s in data['stories'] if s['id'] != id]
        utils.save_json('placements.json', data)
        flash('Story deleted.', 'info')
    return redirect(url_for('manage_placements'))

@app.route('/about')
def about():
    leadership_data = utils.load_json('leadership.json')
    return render_template('about.html', leadership=leadership_data)

# --- Leadership Management ---
@app.route('/admin/leadership', methods=['GET', 'POST'])
@login_required
def manage_leadership():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        designation = request.form.get('designation')
        message = request.form.get('message')
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # Use faculty folder as they are staff/faculty essentially
                image_filename = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        new_leader = {
            "id": str(uuid.uuid4()),
            "name": name,
            "role": role,
            "designation": designation,
            "message": message,
            "image": image_filename
        }
        
        leadership_list = utils.load_json('leadership.json')
        leadership_list.append(new_leader)
        utils.save_json('leadership.json', leadership_list)
        flash('Leadership profile added!', 'success')
        return redirect(url_for('manage_leadership'))
        
    leadership_list = utils.load_json('leadership.json')
    return render_template('admin/manage_leadership.html', leadership=leadership_list)

@app.route('/admin/leadership/delete/<id>')
@login_required
def delete_leadership(id):
    leadership_list = utils.load_json('leadership.json')
    leadership_list = [l for l in leadership_list if l['id'] != id]
    utils.save_json('leadership.json', leadership_list)
    flash('Leadership profile deleted.', 'info')
    return redirect(url_for('manage_leadership'))

@app.route('/admin/leadership/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_leadership(id):
    leadership_list = utils.load_json('leadership.json')
    leader = next((l for l in leadership_list if l['id'] == id), None)
    
    if not leader:
        flash('Leadership profile not found.', 'danger')
        return redirect(url_for('manage_leadership'))

    if request.method == 'POST':
        leader['name'] = request.form.get('name')
        leader['role'] = request.form.get('role')
        leader['designation'] = request.form.get('designation')
        leader['message'] = request.form.get('message')
        
        # Handle Image Upload - Only update if a new file is provided
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                leader['image'] = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        utils.save_json('leadership.json', leadership_list)
        flash('Leadership details updated successfully!', 'success')
        return redirect(url_for('manage_leadership'))
        
    return render_template('admin/edit_leadership.html', leader=leader)

@app.route('/departments')
def departments():
    departments_list = utils.load_json('departments.json')
    return render_template('departments.html', departments=departments_list)

@app.route('/departments/<dept_id>/labs')
def department_labs(dept_id):
    departments_list = utils.load_json('departments.json')
    dept = next((d for d in departments_list if d['id'] == dept_id), None)
    if not dept:
        flash('Department not found.', 'danger')
        return redirect(url_for('departments'))
    return render_template('department_labs.html', dept=dept)

# --- Departments Management ---
@app.route('/admin/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if request.method == 'POST':
        # Basic fields
        dept_id = request.form.get('id')
        name = request.form.get('name')
        icon = request.form.get('icon')
        theme_color = request.form.get('theme_color')
        tagline = request.form.get('tagline')
        intake = request.form.get('intake')
        description = request.form.get('description')
        vision = request.form.get('vision')
        mission = request.form.get('mission')
        
        # HOD fields
        hod_name = request.form.get('hod_name')
        hod_role = request.form.get('hod_role')
        hod_quote = request.form.get('hod_quote')
        
        # Handle HOD Image Upload
        hod_image_filename = ""
        if 'hod_image' in request.files:
            file = request.files['hod_image']
            if file and file.filename != '':
                hod_image_filename = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        # Construct new department object
        new_dept = {
            "id": dept_id if dept_id else str(uuid.uuid4()), # Use provided ID or generate one
            "name": name,
            "icon": icon,
            "theme_color": theme_color,
            "tagline": tagline,
            "intake": intake,
            "description": description,
            "vision": vision,
            "mission": mission,
            "labs": [], # Labs can be added separately or parsed from a complex form if needed. For now, empty or basic.
            "hod": {
                "name": hod_name,
                "role": hod_role,
                "quote": hod_quote,
                "image": hod_image_filename if hod_image_filename else ""
            }
        }
        
        departments_list = utils.load_json('departments.json')
        # Check if ID exists to avoid duplicates if user manually typed it? 
        # For simplicity, just append. If we wanted update, we'd check ID.
        departments_list.append(new_dept)
        utils.save_json('departments.json', departments_list)
        flash('Department added successfully!', 'success')
        return redirect(url_for('manage_departments'))

    departments_list = utils.load_json('departments.json')
    return render_template('admin/manage_departments.html', departments=departments_list)

@app.route('/admin/departments/edit/<dept_id>', methods=['GET', 'POST'])
@login_required
def edit_department(dept_id):
    departments_list = utils.load_json('departments.json')
    dept = next((d for d in departments_list if d['id'] == dept_id), None)
    
    if not dept:
        flash('Department not found.', 'danger')
        return redirect(url_for('manage_departments'))

    if request.method == 'POST':
        dept['name'] = request.form.get('name')
        dept['icon'] = request.form.get('icon')
        dept['theme_color'] = request.form.get('theme_color')
        dept['tagline'] = request.form.get('tagline')
        dept['intake'] = int(request.form.get('intake', 0))
        dept['description'] = request.form.get('description')
        dept['vision'] = request.form.get('vision')
        dept['mission'] = request.form.get('mission')
        
        # HOD fields
        dept['hod']['name'] = request.form.get('hod_name')
        dept['hod']['role'] = request.form.get('hod_role')
        dept['hod']['quote'] = request.form.get('hod_quote')
        
        # Handle HOD Image Upload
        if 'hod_image' in request.files:
            file = request.files['hod_image']
            if file and file.filename != '':
                dept['hod']['image'] = save_file_safely(file, app.config['UPLOAD_FOLDER'])

        # Handle Labs (Parsed from dynamic form fields)
        lab_names = request.form.getlist('lab_name[]')
        lab_icons = request.form.getlist('lab_icon[]')
        lab_colors = request.form.getlist('lab_color[]')
        lab_descriptions = request.form.getlist('lab_description[]')
        lab_existing_imgs = request.form.getlist('lab_existing_image[]')
        lab_files = request.files.getlist('lab_image[]')
        
        new_labs = []
        # In multi-file upload, empty inputs are still sent. We need to match by index.
        # However, browsers sometimes skip empty file inputs or send empty objects.
        # A safer way is to check the length of lab_names and iterate.
        for i in range(len(lab_names)):
            if lab_names[i].strip():
                lab_img = lab_existing_imgs[i] if i < len(lab_existing_imgs) else ""
                
                # Check if a new file was uploaded for this specific index
                if i < len(lab_files):
                    file = lab_files[i]
                    if file and file.filename != '':
                        lab_img = save_file_safely(file, app.config['LABS_FOLDER'])
                
                new_labs.append({
                    "name": lab_names[i],
                    "icon": lab_icons[i] if i < len(lab_icons) else "fas fa-flask",
                    "color": lab_colors[i] if i < len(lab_colors) else "#666",
                    "image": lab_img,
                    "description": lab_descriptions[i] if i < len(lab_descriptions) else ""
                })
        dept['labs'] = new_labs

        utils.save_json('departments.json', departments_list)
        flash('Department details updated successfully!', 'success')
        return redirect(url_for('manage_departments'))
        
    return render_template('admin/edit_department.html', dept=dept)

@app.route('/admin/departments/delete/<dept_id>')
@login_required
def delete_department(dept_id):
    departments_list = utils.load_json('departments.json')
    departments_list = [d for d in departments_list if d['id'] != dept_id]
    utils.save_json('departments.json', departments_list)
    flash('Department deleted.', 'info')
    return redirect(url_for('manage_departments'))

@app.route('/facilities')
def facilities():
    facilities_list = utils.load_json('facilities.json')
    return render_template('facilities.html', facilities=facilities_list)

@app.route('/library')
def library():
    library_data = utils.load_json('library.json')
    return render_template('library.html', library=library_data)

# --- Facilities Management ---
@app.route('/admin/facilities', methods=['GET', 'POST'])
@login_required
def manage_facilities():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon = request.form.get('icon')
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = save_file_safely(file, app.config['FACILITIES_FOLDER'])
        
        new_facility = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "icon": icon,
            "image": image_filename
        }
        
        facilities_list = utils.load_json('facilities.json')
        facilities_list.append(new_facility)
        utils.save_json('facilities.json', facilities_list)
        flash('Facility added successfully!', 'success')
        return redirect(url_for('manage_facilities'))
        
    facilities_list = utils.load_json('facilities.json')
    return render_template('admin/manage_facilities.html', facilities=facilities_list)

@app.route('/admin/facilities/delete/<id>')
@login_required
def delete_facility(id):
    facilities = utils.load_json('facilities.json')
    facilities = [f for f in facilities if f['id'] != id]
    utils.save_json('facilities.json', facilities)
    flash('Facility removed.', 'success')
    return redirect(url_for('manage_facilities'))

# --- Academics Management ---
@app.route('/admin/academics', methods=['GET', 'POST'])
@login_required
def manage_academics():
    academics_data = utils.load_json('academics.json')
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'event':
            new_event = {
                "id": str(uuid.uuid4()),
                "activity": request.form.get('activity'),
                "date": request.form.get('date'),
                "category": request.form.get('category'),
                "badge_class": request.form.get('badge_class')
            }
            academics_data['calendar'].append(new_event)
            flash('Academic event added!', 'success')
            
        elif form_type == 'notice':
            new_notice = {
                "id": str(uuid.uuid4()),
                "title": request.form.get('title'),
                "date": request.form.get('date'),
                "content": request.form.get('content'),
                "border_color": request.form.get('border_color') or None
            }
            academics_data['notices'].insert(0, new_notice)
            flash('Notice board updated!', 'success')
            
        utils.save_json('academics.json', academics_data)
        return redirect(url_for('manage_academics'))
        
    return render_template('admin/manage_academics.html', academics=academics_data)

@app.route('/admin/academics/event/delete/<id>')
@login_required
def delete_academic_event(id):
    academics_data = utils.load_json('academics.json')
    academics_data['calendar'] = [e for e in academics_data['calendar'] if e['id'] != id]
    utils.save_json('academics.json', academics_data)
    flash('Event removed from calendar.', 'success')
    return redirect(url_for('manage_academics'))

@app.route('/admin/academics/notice/delete/<id>')
@login_required
def delete_academic_notice(id):
    academics_data = utils.load_json('academics.json')
    academics_data['notices'] = [n for n in academics_data['notices'] if n['id'] != id]
    utils.save_json('academics.json', academics_data)
    flash('Notice removed from feed.', 'success')
    return redirect(url_for('manage_academics'))

@app.route('/activities')
def activities():
    activities_list = utils.load_json('activities.json')
    # Sort by date descending
    activities_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    return render_template('activities.html', activities=activities_list)

@app.route('/governance')
def governance():
    governance_data = utils.load_json('governance.json')
    return render_template('governance.html', governance=governance_data)

@app.route('/news')
def news():
    news_items = utils.load_json('news.json')
    # Sort news by date if possible (assuming date format is consistent)
    return render_template('news.html', news=news_items)

@app.route('/admin/activities', methods=['GET', 'POST'])
@login_required
def manage_activities():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        date = request.form.get('date')
        image_file = request.files.get('image')
        
        if not title or not category:
            flash('Title and Category are required.', 'danger')
            return redirect(url_for('manage_activities'))
            
        activities_list = utils.load_json('activities.json')
        
        filename = ""
        if image_file and image_file.filename != '':
            filename = save_file_safely(image_file, app.config['ACTIVITIES_FOLDER'])
            
        new_activity = {
            "id": str(uuid.uuid4()),
            "title": title,
            "category": category,
            "description": description,
            "date": date,
            "image": filename
        }
        
        activities_list.append(new_activity)
        utils.save_json('activities.json', activities_list)
        flash('Activity added successfully!', 'success')
        return redirect(url_for('manage_activities'))
        
    activities_list = utils.load_json('activities.json')
    activities_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    return render_template('admin/manage_activities.html', activities=activities_list)

@app.route('/admin/activities/delete/<id>')
@login_required
def delete_activity(id):
    activities_list = utils.load_json('activities.json')
    activities_list = [a for a in activities_list if a['id'] != id]
    utils.save_json('activities.json', activities_list)
    flash('Activity deleted successfully!', 'success')
    return redirect(url_for('manage_activities'))

# --- Governance Management ---
@app.route('/admin/governance', methods=['GET', 'POST'])
@login_required
def manage_governance():
    if request.method == 'POST':
        name = request.form.get('name')
        full_name = request.form.get('full_name')
        type_body = request.form.get('type')
        description = request.form.get('description')
        website = request.form.get('website')
        
        # Handle Logo Upload
        logo_filename = ""
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename != '':
                # Ensure governance folder exists in static
                gov_folder = os.path.join('static', 'images', 'governance')
                safe_makedirs(gov_folder)
                logo_filename = save_file_safely(file, gov_folder)

        new_body = {
            "id": str(uuid.uuid4()),
            "name": name,
            "full_name": full_name,
            "type": type_body,
            "description": description,
            "logo": logo_filename,
            "website": website
        }
        
        governance_list = utils.load_json('governance.json')
        governance_list.append(new_body)
        utils.save_json('governance.json', governance_list)
        flash('Governing body added successfully!', 'success')
        return redirect(url_for('manage_governance'))
        
    governance_list = utils.load_json('governance.json')
    return render_template('admin/manage_governance.html', governance=governance_list)

@app.route('/admin/governance/delete/<id>')
@login_required
def delete_governance(id):
    governance_list = utils.load_json('governance.json')
    governance_list = [g for g in governance_list if g['id'] != id]
    utils.save_json('governance.json', governance_list)
    flash('Governing body removed successfully.', 'info')
    return redirect(url_for('manage_governance'))

@app.route('/admin/activities/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_activity(id):
    activities_list = utils.load_json('activities.json')
    activity = next((a for a in activities_list if a['id'] == id), None)
    
    if not activity:
        flash('Activity not found.', 'danger')
        return redirect(url_for('manage_activities'))
        
    if request.method == 'POST':
        activity['title'] = request.form.get('title')
        activity['category'] = request.form.get('category')
        activity['description'] = request.form.get('description')
        activity['date'] = request.form.get('date')
        
        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            filename = save_file_safely(image_file, app.config['ACTIVITIES_FOLDER'])
            activity['image'] = filename
            
        utils.save_json('activities.json', activities_list)
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('manage_activities'))
        
    return render_template('admin/edit_activity.html', activity=activity)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/academics')
def academics():
    academics_data = utils.load_json('academics.json')
    return render_template('academics.html', academics=academics_data)

@app.route('/faculty')
def faculty():
    faculty_list = utils.load_json('faculty.json')
    # Group by department using helper
    grouped_faculty = utils.get_faculty_by_dept(faculty_list)
    return render_template('faculty.html', grouped_faculty=grouped_faculty)

@app.route('/faculty/<id>')
def faculty_detail(id):
    faculty_list = utils.load_json('faculty.json')
    faculty_member = next((f for f in faculty_list if f['id'] == id), None)
    
    if not faculty_member:
        flash('Faculty member not found.', 'danger')
        return redirect(url_for('faculty'))
        
    return render_template('faculty_detail.html', faculty=faculty_member)

@app.route('/placement')
def placement():
    data = utils.load_json('placements.json')
    return render_template('placement.html', data=data)

@app.route('/gallery')
def gallery():
    gallery_items = utils.load_json('gallery.json')
    return render_template('gallery.html', gallery_items=gallery_items)

@app.route('/admission')
def admission():
    return render_template('admission.html')

@app.route('/upload_faculty', methods=['GET', 'POST'])
def upload_faculty():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        custom_name = request.form.get('filename')
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file:
            # Use custom name if provided, else original filename
            image_filename = save_file_safely(file, app.config['UPLOAD_FOLDER'])
            flash(f'Image uploaded successfully!', 'success')
            return redirect(url_for('upload_faculty'))
            
    return render_template('upload_faculty.html')

if __name__ == '__main__':
    app.run(debug=True)

