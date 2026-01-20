import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
import utils
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey' # Needed for flash messages
app.config['UPLOAD_FOLDER'] = 'static/images/faculty'

# Admin Credentials (Hardcoded for simplicity)
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = 'password123'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['GALLERY_FOLDER'] = 'static/images/gallery'
os.makedirs(app.config['GALLERY_FOLDER'], exist_ok=True)

app.config['NEWS_FOLDER'] = 'static/images/news'
os.makedirs(app.config['NEWS_FOLDER'], exist_ok=True)
app.config['PLACEMENTS_FOLDER'] = 'static/images/placements'
os.makedirs(app.config['PLACEMENTS_FOLDER'], exist_ok=True)

app.config['FACILITIES_FOLDER'] = 'static/images/facilities'
os.makedirs(app.config['FACILITIES_FOLDER'], exist_ok=True)

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
    return render_template('index.html', news=news_items, stories=stories)

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
    return render_template('admin/dashboard.html')

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
        
        # Handle Image Upload
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename

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
            "qualification": qualification
        }
        
        faculty_list = utils.load_json('faculty.json')
        faculty_list.append(new_faculty)
        utils.save_json('faculty.json', faculty_list)
        flash('Faculty member added successfully!', 'success')
        return redirect(url_for('manage_faculty'))
        
    faculty_list = utils.load_json('faculty.json')
    return render_template('admin/manage_faculty.html', faculty=faculty_list)

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
        
        # Handle Image Upload - Only update if a new file is provided
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                faculty_member['image'] = filename

        utils.save_json('faculty.json', faculty_list)
        flash('Faculty details updated!', 'success')
        return redirect(url_for('manage_faculty'))
        
    return render_template('admin/edit_faculty.html', faculty=faculty_member)

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
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['NEWS_FOLDER'], filename))
                image_filename = filename
        
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
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['GALLERY_FOLDER'], filename))
                image_filename = filename
        
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
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['PLACEMENTS_FOLDER'], filename))
                    image_filename = filename

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
                filename = secure_filename(file.filename)
                # Store in faculty folder for simplicity or create specific leadership folder
                # Using faculty folder as they are staff/faculty essentially
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) 
                image_filename = filename

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

@app.route('/departments')
def departments():
    departments_list = utils.load_json('departments.json')
    return render_template('departments.html', departments=departments_list)

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
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                hod_image_filename = filename

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
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['FACILITIES_FOLDER'], filename))
                image_filename = filename
        
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
    facilities_list = utils.load_json('facilities.json')
    facilities_list = [f for f in facilities_list if f['id'] != id]
    utils.save_json('facilities.json', facilities_list)
    flash('Facility deleted.', 'info')
    return redirect(url_for('manage_facilities'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/academics')
def academics():
    return render_template('academics.html')

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
            if custom_name:
                filename = secure_filename(custom_name)
            else:
                filename = secure_filename(file.filename)
                
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'Image uploaded successfully as {filename}!', 'success')
            return redirect(url_for('upload_faculty'))
            
    return render_template('upload_faculty.html')

if __name__ == '__main__':
    app.run(debug=True)

