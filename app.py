import os
import logging
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file, session
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
import csv
import io
import openpyxl

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - use local SQLite for privacy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///student_engagement.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import and initialize database
from models import db, Class, Student, Observation
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Main dashboard showing recent activity and quick access"""
    classes = Class.query.all()
    recent_observations = Observation.query.order_by(Observation.timestamp.desc()).limit(10).all()
    
    # Get today's observation count
    today_count = Observation.query.filter(
        func.date(Observation.timestamp) == date.today()
    ).count()
    
    return render_template('index.html', 
                         classes=classes, 
                         recent_observations=recent_observations,
                         today_count=today_count)

@app.route('/manage_classes')
def manage_classes():
    """Manage classes and students"""
    classes = Class.query.all()
    print(f"DEBUG: Found {len(classes)} classes in database")
    for cls in classes:
        print(f"DEBUG: Class: {cls.name} (ID: {cls.id})")
    selected_class_id = request.args.get('class_id', type=int)
    selected_class = None
    if selected_class_id:
        selected_class = Class.query.get(selected_class_id)
    return render_template('manage_classes.html', classes=classes, selected_class=selected_class)

@app.route('/add_class', methods=['POST'])
def add_class():
    """Add a new class"""
    class_name = request.form.get('class_name', '').strip()
    print(f"DEBUG: Attempting to add class: '{class_name}'")
    
    if not class_name:
        flash('Klassenavn er påkrevd', 'error')
        return redirect(url_for('manage_classes'))
    
    # Check if class already exists
    existing_class = Class.query.filter_by(name=class_name).first()
    if existing_class:
        print(f"DEBUG: Class '{class_name}' already exists")
        flash('Klassen eksisterer allerede', 'error')
        return redirect(url_for('manage_classes'))
    
    try:
        new_class = Class(name=class_name)
        db.session.add(new_class)
        db.session.commit()
        print(f"DEBUG: Successfully added class '{class_name}'")
        flash(f'Klasse "{class_name}" ble lagt til', 'success')
    except Exception as e:
        print(f"DEBUG: Error adding class: {e}")
        db.session.rollback()
        flash('Feil ved lagring av klasse', 'error')
    
    return redirect(url_for('manage_classes'))

@app.route('/add_student', methods=['POST'])
def add_student():
    """Add a student to a class"""
    class_id = request.form.get('class_id')
    student_name = request.form.get('student_name', '').strip()
    print(f"DEBUG: Attempting to add student '{student_name}' to class {class_id}")
    
    if not class_id or not student_name:
        print(f"DEBUG: Missing data - class_id: {class_id}, student_name: '{student_name}'")
        flash('Klasse og elevnavn er påkrevd', 'error')
        return redirect(url_for('manage_classes', class_id=class_id))
    
    # Check if student already exists in this class
    existing_student = Student.query.filter_by(
        name=student_name, 
        class_id=class_id
    ).first()
    
    if existing_student:
        print(f"DEBUG: Student '{student_name}' already exists in class {class_id}")
        flash('Eleven eksisterer allerede i denne klassen', 'error')
        return redirect(url_for('manage_classes', class_id=class_id))
    
    try:
        new_student = Student(name=student_name, class_id=class_id)
        db.session.add(new_student)
        db.session.commit()
        print(f"DEBUG: Successfully added student '{student_name}' to class {class_id}")
        flash(f'Elev "{student_name}" ble lagt til', 'success')
    except Exception as e:
        print(f"DEBUG: Error adding student: {e}")
        db.session.rollback()
        flash('Feil ved lagring av elev', 'error')
    
    # Etter å ha lagt til elev, behold valgt klasse åpen
    return redirect(url_for('manage_classes', class_id=class_id))

@app.route('/delete_class/<int:class_id>', methods=['POST'])
def delete_class(class_id):
    """Delete a class and all its students and observations"""
    class_to_delete = Class.query.get_or_404(class_id)
    
    # Delete all observations for students in this class
    for student in class_to_delete.students:
        Observation.query.filter_by(student_id=student.id).delete()
    
    # Delete all students in this class
    Student.query.filter_by(class_id=class_id).delete()
    
    # Delete the class
    db.session.delete(class_to_delete)
    db.session.commit()
    
    flash(f'Klasse "{class_to_delete.name}" og alle tilhørende data ble slettet', 'success')
    return redirect(url_for('manage_classes'))

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """Delete a student and all their observations"""
    student_to_delete = Student.query.get_or_404(student_id)
    
    # Delete all observations for this student
    Observation.query.filter_by(student_id=student_id).delete()
    
    # Delete the student
    db.session.delete(student_to_delete)
    db.session.commit()
    
    flash(f'Elev "{student_to_delete.name}" og alle observasjoner ble slettet', 'success')
    return redirect(url_for('manage_classes'))

@app.route('/observe/<int:class_id>')
def observe_class(class_id):
    """Observation interface for a specific class"""
    selected_class = Class.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id).order_by(Student.name).all()
    if not students:
        flash('Ingen elever i denne klassen. Legg til elever først.', 'warning')
        return redirect(url_for('manage_classes'))
    return render_template(
        'observe_class.html',
        selected_class=selected_class,
        students=students,
        observation_categories={
    'faglig_initiativ': [
        'stiller_sporsmal',
        'utforsker_tema',
        'faglige_innspill',
        'bruker_fagbegreper',
    ],
    'sosialt_samspill': [
        'hjelper_medelever',
        'samarbeider_i_gruppe',
        'inkluderer_andre',
        'viser_empati',
    ],
    'selvstendighet_utholdenhet': [
        'jobber_jevnt',
        'folger_opp_oppgaver',
        'fullforer_arbeid',
        'viser_talmodighet',
    ],
    'engasjement_tilstede': [
        'rekker_opp_handa',
        'deltar_aktivt',
        'viser_interesse',
        'holder_seg_til_fag',
    ],
    'kreativitet_fleksibilitet': [
        'tenker_nytt',
        'ulike_losninger',
        'kommer_med_forslag',
        'viser_humor',
    ]
},
        observation_display={
            'stiller_sporsmal': 'Stiller spørsmål',
            'utforsker_tema': 'Utforsker tema på egen hånd',
            'faglige_innspill': 'Kommer med faglige innspill',
            'bruker_fagbegreper': 'Bruker fagbegreper i samtale',
            'hjelper_medelever': 'Hjelper medelever',
            'samarbeider_i_gruppe': 'Samarbeider i gruppe',
            'inkluderer_andre': 'Inkluderer andre',
            'viser_empati': 'Viser empati eller støtte',
            'jobber_jevnt': 'Jobber jevnt uten hjelp',
            'folger_opp_oppgaver': 'Følger opp egne oppgaver',
            'fullforer_arbeid': 'Fullfører arbeid selv om det er krevende',
            'viser_talmodighet': 'Viser tålmodighet og fokus',
            'rekker_opp_handa': 'Rekker opp hånda',
            'deltar_aktivt': 'Deltar aktivt i klassesamtaler',
            'viser_interesse': 'Viser interesse for faget',
            'holder_seg_til_fag': 'Holder seg til faglige aktiviteter',
            'tenker_nytt': 'Tenker nytt',
            'ulike_losninger': 'Løser oppgaver på uvanlige måter',
            'kommer_med_forslag': 'Kommer med forslag eller ideer',
            'viser_humor': 'Viser humor eller personlig uttrykk',
            'egne_notater': 'Egne notater',
        }
    )

@app.route('/record_observation', methods=['POST'])
def record_observation():
    """Record an observation for a student"""
    from datetime import timedelta
    student_id = request.form.get('student_id')
    observation_type = request.form.get('observation_type')
    notes = request.form.get('notes', '').strip()

    # Slett observasjoner eldre enn 30 dager
    cutoff_date = datetime.now() - timedelta(days=30)
    deleted = Observation.query.filter(Observation.timestamp < cutoff_date).delete()
    if deleted:
        db.session.commit()

    if not student_id or not observation_type:
        return jsonify({'success': False, 'message': 'Manglende data'})
    
    # --- NY KATEGORIVALIDERING ---
    valid_types = []
    for undercats in OBSERVATION_CATEGORIES.values():
        valid_types.extend(undercats)
    valid_types.append('egne_notater')
    if observation_type not in valid_types:
        return jsonify({'success': False, 'message': 'Ugyldig observasjonstype'})
    
    # For custom notes, require notes text
    if observation_type == 'egne_notater' and not notes:
        return jsonify({'success': False, 'message': 'Notater er påkrevd for egne notater'})
    
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Elev ikke funnet'})
    
    # Create new observation
    observation = Observation(
        student_id=student_id,
        observation_type=observation_type,
        notes=notes if notes else None,
        timestamp=datetime.now()
    )
    
    db.session.add(observation)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Observasjon registrert for {student.name}'
    })

@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    """Show engagement statistics for student or class"""
    from models import Observation, Student, Class
    classes = Class.query.all()
    students = Student.query.all()
    if request.method == 'POST':
        stats_type = request.form.get('statisticsType', 'class')
        selected_student_id = request.form.get('student_id')
        selected_class_id = request.form.get('class_id')
        if stats_type == 'student' and selected_student_id:
            students = [Student.query.get(selected_student_id)]
            selected_class = students[0].class_ref if students[0] else None
        elif selected_class_id:
            students = Student.query.filter_by(class_id=selected_class_id).all()
            selected_class = Class.query.get(selected_class_id)
        else:
            selected_class = None
    else:
        selected_class_id = request.args.get('class_id', type=int)
        if selected_class_id:
            selected_class = Class.query.get(selected_class_id)
            students = Student.query.filter_by(class_id=selected_class_id).all()
        else:
            selected_class = None
    # Bygg statistikk for alle underkategorier
    from models import Observation
    # Map for visning
    observation_display = {
        # Faglig initiativ
        'stiller_sporsmal': 'Stiller spørsmål',
        'utforsker_tema': 'Utforsker tema på egen hånd',
        'faglige_innspill': 'Kommer med faglige innspill',
        'bruker_fagbegreper': 'Bruker fagbegreper i samtale',
        # Sosialt samspill
        'hjelper_medelever': 'Hjelper medelever',
        'samarbeider_i_gruppe': 'Samarbeider i gruppe',
        'inkluderer_andre': 'Inkluderer andre',
        'viser_empati': 'Viser empati eller støtte',
        # Selvstendighet og utholdenhet
        'jobber_jevnt': 'Jobber jevnt uten hjelp',
        'folger_opp_oppgaver': 'Følger opp egne oppgaver',
        'fullforer_arbeid': 'Fullfører arbeid selv om det er krevende',
        'viser_talmodighet': 'Viser tålmodighet og fokus',
        # Engasjement og tilstedeværelse
        'rekker_opp_handa': 'Rekker opp hånda',
        'deltar_aktivt': 'Deltar aktivt i klassesamtaler',
        'viser_interesse': 'Viser interesse for faget',
        'holder_seg_til_fag': 'Holder seg til faglige aktiviteter',
        # Kreativitet og fleksibilitet
        'tenker_nytt': 'Tenker nytt',
        'ulike_losninger': 'Løser oppgaver på uvanlige måter',
        'kommer_med_forslag': 'Kommer med forslag eller ideer',
        'viser_humor': 'Viser humor eller personlig uttrykk',
        # Egne notater
        'egne_notater': 'Egne notater',
    }
    # Bygg stats
    student_stats = []
    for student in students:
        stats = {'student': student}
        total = 0
        for hoved, under in OBSERVATION_CATEGORIES.items():
            for underkat in under:
                count = Observation.query.filter_by(student_id=student.id, observation_type=underkat).count()
                stats[underkat] = count
                total += count
        stats['total'] = total
        student_stats.append(stats)
    # Sorter på total
    student_stats.sort(key=lambda x: x['total'], reverse=True)
    return render_template('statistics.html', 
        classes=classes, 
        selected_class=selected_class,
        student_stats=student_stats,
        observation_categories=OBSERVATION_CATEGORIES,
        observation_display=observation_display)

@app.route('/privacy_info')
def privacy_info():
    """GDPR and privacy information"""
    return render_template('privacy_info.html')

@app.route('/student_observation_history/<int:student_id>')
def student_observation_history(student_id):
    """Return time series of all observation types for a student (grouped per day)"""
    from collections import defaultdict
    student = Student.query.get_or_404(student_id)
    # List of all valid observation types (excluding 'egne_notater')
    observation_types = [
        'stiller_sporsmal',
        'samarbeider_med_andre',
        'tar_initiativ',
        'ferdigstiller_oppgaver',
        'behover_veiledning',
        'er_distrahert',
        'viser_glede_interesse',
        'tilbaketrukket',
    ]
    # Query all observations for this student
    observations = Observation.query.filter_by(student_id=student_id).all()
    # Group by date and type
    data = defaultdict(lambda: {k: 0 for k in observation_types})
    for obs in observations:
        obs_date = obs.timestamp.date().isoformat()
        if obs.observation_type in observation_types:
            data[obs_date][obs.observation_type] += 1
    # Sort dates
    sorted_dates = sorted(data.keys())
    # Build response
    result = {
        'dates': sorted_dates,
        'series': {k: [data[d][k] for d in sorted_dates] for k in observation_types}
    }
    return jsonify(result)

@app.route('/export_data')
def export_data():
    """Export all observations as JSON"""
    from models import Observation, Student, Class
    observations = Observation.query.all()
    data = []
    for obs in observations:
        elev = obs.student.name
        klasse = obs.student.class_ref.name
        obs_type = obs.observation_type
        notater = (obs.notes or '').replace('\n', ' ')
        tidspunkt = obs.timestamp.strftime('%Y-%m-%d %H:%M')
        data.append({
            'Elev': elev,
            'Klasse': klasse,
            'Observasjonstype': obs_type,
            'Notater': notater,
            'Tidspunkt': tidspunkt
        })
    return jsonify(data)

@app.route('/export_excel', methods=['GET', 'POST'])
def export_excel():
    """Export observations to Excel based on selected type (student/class)"""
    from models import Observation, Student, Class
    export_type = request.form.get('exportType', 'class')
    selected_student_id = request.form.get('student_id')
    selected_class_id = request.form.get('class_id')
    query = Observation.query
    if export_type == 'student' and selected_student_id:
        query = query.filter_by(student_id=selected_student_id)
    elif selected_class_id:
        students = Student.query.filter_by(class_id=selected_class_id).all()
        student_ids = [s.id for s in students]
        query = query.filter(Observation.student_id.in_(student_ids))
    observations = query.all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Observasjoner"
    ws.append(["Elev", "Klasse", "Observasjonstype", "Notater", "Tidspunkt"])
    for obs in observations:
        elev = obs.student.name
        klasse = obs.student.class_ref.name
        obs_type = obs.observation_type
        notater = (obs.notes or '').replace('\n', ' ')
        tidspunkt = obs.timestamp.strftime('%Y-%m-%d %H:%M')
        ws.append([elev, klasse, obs_type, notater, tidspunkt])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="observasjoner.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- PIN-håndtering med fil ---
PIN_FILE = os.path.join(app.instance_path, 'pin.txt')

def get_current_pin():
    try:
        with open(PIN_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return os.environ.get("APP_PIN", "1234")

def set_new_pin(new_pin):
    os.makedirs(app.instance_path, exist_ok=True)
    with open(PIN_FILE, 'w') as f:
        f.write(new_pin.strip())

# PIN for innlogging (kan settes via miljøvariabel eller hardkodes)
APP_PIN = os.environ.get("APP_PIN", "1234")

def login_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.url))
        return view_func(*args, **kwargs)
    return wrapped_view

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin', '')
        if pin == get_current_pin():
            session['logged_in'] = True
            # Fjern gamle flash-meldinger etter innlogging
            session.pop('_flashes', None)
            # Sjekk om PIN fortsatt er standard (1234)
            if get_current_pin() == '1234':
                return redirect(url_for('change_pin'))
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            error = 'Feil PIN-kode. Prøv igjen.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    # Tøm eventuelle gamle flash-meldinger etter utlogging
    session['_flashes'] = []
    flash('Du er logget ut.', 'info')
    return redirect(url_for('login'))

@app.route('/change_pin', methods=['GET', 'POST'])
def change_pin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    error = None
    success = None
    if request.method == 'POST':
        old_pin = request.form.get('old_pin', '')
        new_pin = request.form.get('new_pin', '')
        confirm_pin = request.form.get('confirm_pin', '')
        if old_pin != get_current_pin():
            error = 'Gammel PIN er feil.'
        elif not new_pin or len(new_pin) < 4:
            error = 'Ny PIN må være minst 4 tegn.'
        elif new_pin != confirm_pin:
            error = 'PIN-kodene er ikke like.'
        else:
            set_new_pin(new_pin)
            success = 'PIN er endret!'
            return redirect(url_for('index'))
    return render_template('change_pin.html', error=error, success=success)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    error = None
    success = None
    from models import Class, Student
    classes = Class.query.all()
    students = Student.query.all()
    # PIN-bytte via POST fra settings-siden
    if request.method == 'POST' and 'old_pin' in request.form:
        old_pin = request.form.get('old_pin', '')
        new_pin = request.form.get('new_pin', '')
        confirm_pin = request.form.get('confirm_pin', '')
        if old_pin != get_current_pin():
            error = 'Gammel PIN er feil.'
        elif not new_pin or len(new_pin) < 4:
            error = 'Ny PIN må være minst 4 tegn.'
        elif new_pin != confirm_pin:
            error = 'PIN-kodene er ikke like.'
        else:
            set_new_pin(new_pin)
            success = 'PIN er endret!'
    # Serialize classes and students for JS
    classes_serialized = [
        {'id': c.id, 'name': c.name} for c in classes
    ]
    students_serialized = [
        {'id': s.id, 'name': s.name, 'class_id': s.class_id} for s in students
    ]
    return render_template(
        'settings.html',
        observation_categories=OBSERVATION_CATEGORIES,
        observation_display={
            'stiller_sporsmal': 'Stiller spørsmål',
            'utforsker_tema': 'Utforsker tema på egen hånd',
            'faglige_innspill': 'Kommer med faglige innspill',
            'bruker_fagbegreper': 'Bruker fagbegreper i samtale',
            'hjelper_medelever': 'Hjelper medelever',
            'samarbeider_i_gruppe': 'Samarbeider i gruppe',
            'inkluderer_andre': 'Inkluderer andre',
            'viser_empati': 'Viser empati eller støtte',
            'jobber_jevnt': 'Jobber jevnt uten hjelp',
            'folger_opp_oppgaver': 'Følger opp egne oppgaver',
            'fullforer_arbeid': 'Fullfører arbeid selv om det er krevende',
            'viser_talmodighet': 'Viser tålmodighet og fokus',
            'rekker_opp_handa': 'Rekker opp hånda',
            'deltar_aktivt': 'Deltar aktivt i klassesamtaler',
            'viser_interesse': 'Viser interesse for faget',
            'holder_seg_til_fag': 'Holder seg til faglige aktiviteter',
            'tenker_nytt': 'Tenker nytt',
            'ulike_losninger': 'Løser oppgaver på uvanlige måter',
            'kommer_med_forslag': 'Kommer med forslag eller ideer',
            'viser_humor': 'Viser humor eller personlig uttrykk',
            'egne_notater': 'Egne notater',
        },
        classes=classes_serialized,
        students=students_serialized,
        error=error,
        success=success
    )

@app.route('/reset_app', methods=['POST'])
def reset_app():
    # Slett alle elever, klasser og observasjoner
    Observation.query.delete()
    Student.query.delete()
    Class.query.delete()
    db.session.commit()
    return ('', 204)

# Beskytt alle relevante ruter med login_required
app.view_functions['index'] = login_required(app.view_functions['index'])
app.view_functions['manage_classes'] = login_required(app.view_functions['manage_classes'])
app.view_functions['add_class'] = login_required(app.view_functions['add_class'])
app.view_functions['add_student'] = login_required(app.view_functions['add_student'])
app.view_functions['delete_class'] = login_required(app.view_functions['delete_class'])
app.view_functions['delete_student'] = login_required(app.view_functions['delete_student'])
app.view_functions['observe_class'] = login_required(app.view_functions['observe_class'])
app.view_functions['record_observation'] = login_required(app.view_functions['record_observation'])
app.view_functions['statistics'] = login_required(app.view_functions['statistics'])
app.view_functions['student_observation_history'] = login_required(app.view_functions['student_observation_history'])
app.view_functions['export_data'] = login_required(app.view_functions['export_data'])
app.view_functions['export_excel'] = login_required(app.view_functions['export_excel'])
# privacy_info forblir åpen

# --- NYE OBSERVASJONSKATEGORIER MED UNDERKATEGORIER ---
OBSERVATION_CATEGORIES = {
    'faglig_initiativ': [
        'stiller_sporsmal',
        'utforsker_tema',
        'faglige_innspill',
        'bruker_fagbegreper',
    ],
    'sosialt_samspill': [
        'hjelper_medelever',
        'samarbeider_i_gruppe',
        'inkluderer_andre',
        'viser_empati',
    ],
    'selvstendighet_utholdenhet': [
        'jobber_jevnt',
        'folger_opp_oppgaver',
        'fullforer_arbeid',
        'viser_talmodighet',
    ],
    'engasjement_tilstede': [
        'rekker_opp_handa',
        'deltar_aktivt',
        'viser_interesse',
        'holder_seg_til_fag',
    ],
    'kreativitet_fleksibilitet': [
        'tenker_nytt',
        'ulike_losninger',
        'kommer_med_forslag',
        'viser_humor',
    ]
}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
