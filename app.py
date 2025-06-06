import os
import logging
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
import csv

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
    
    return render_template('observe_class.html', 
                         selected_class=selected_class, 
                         students=students)

@app.route('/record_observation', methods=['POST'])
def record_observation():
    """Record an observation for a student"""
    student_id = request.form.get('student_id')
    observation_type = request.form.get('observation_type')
    notes = request.form.get('notes', '').strip()
    
    if not student_id or not observation_type:
        return jsonify({'success': False, 'message': 'Manglende data'})
    
    # Validate observation type
    valid_types = [
        'stiller_sporsmal',
        'samarbeider_med_andre',
        'tar_initiativ',
        'ferdigstiller_oppgaver',
        'behover_veiledning',
        'er_distrahert',
        'viser_glede_interesse',
        'tilbaketrukket',
        'egne_notater'
    ]
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

@app.route('/statistics')
def statistics():
    """Show engagement statistics"""
    classes = Class.query.all()
    print(f"DEBUG: Statistics - Found {len(classes)} classes")
    for cls in classes:
        print(f"DEBUG: Statistics - Class: {cls.name} (ID: {cls.id})")
    selected_class_id = request.args.get('class_id', type=int)
    
    if selected_class_id:
        selected_class = Class.query.get(selected_class_id)
        students = Student.query.filter_by(class_id=selected_class_id).all()
    else:
        selected_class = None
        students = Student.query.all()
    
    # Calculate statistics for each student
    student_stats = []
    for student in students:
        stats = {
            'student': student,
            'stiller_sporsmal': Observation.query.filter_by(student_id=student.id, observation_type='stiller_sporsmal').count(),
            'samarbeider_med_andre': Observation.query.filter_by(student_id=student.id, observation_type='samarbeider_med_andre').count(),
            'tar_initiativ': Observation.query.filter_by(student_id=student.id, observation_type='tar_initiativ').count(),
            'ferdigstiller_oppgaver': Observation.query.filter_by(student_id=student.id, observation_type='ferdigstiller_oppgaver').count(),
            'behover_veiledning': Observation.query.filter_by(student_id=student.id, observation_type='behover_veiledning').count(),
            'er_distrahert': Observation.query.filter_by(student_id=student.id, observation_type='er_distrahert').count(),
            'viser_glede_interesse': Observation.query.filter_by(student_id=student.id, observation_type='viser_glede_interesse').count(),
            'tilbaketrukket': Observation.query.filter_by(student_id=student.id, observation_type='tilbaketrukket').count(),
        }
        stats['total'] = sum([stats[key] for key in stats if key != 'student'])
        student_stats.append(stats)
    
    # Sort by total observations (most active first)
    student_stats.sort(key=lambda x: x['total'], reverse=True)
    
    return render_template('statistics.html', 
                         classes=classes, 
                         selected_class=selected_class,
                         student_stats=student_stats)

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
    """Export all observations as CSV"""
    from models import Observation, Student, Class
    observations = Observation.query.all()
    def generate():
        yield 'Elev,Klasse,Observasjonstype,Notater,Tidspunkt\n'
        for obs in observations:
            elev = obs.student.name
            klasse = obs.student.class_ref.name
            obs_type = obs.observation_type
            notater = (obs.notes or '').replace('\n', ' ')
            tidspunkt = obs.timestamp.strftime('%Y-%m-%d %H:%M')
            yield f'"{elev}","{klasse}","{obs_type}","{notater}","{tidspunkt}"\n'
    return Response(generate(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=observasjoner.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
