from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Database instance will be injected
db = SQLAlchemy()

class Class(db.Model):
    """Model for school classes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to students
    students = db.relationship('Student', backref='class_ref', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Class {self.name}>'

class Student(db.Model):
    """Model for students"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to observations
    observations = db.relationship('Observation', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.name}>'

class Observation(db.Model):
    """Model for engagement observations"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    observation_type = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)  # For custom notes
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Valid observation types:
    # - deltar_muntlig: Student participates verbally
    # - folger_med: Student pays attention
    # - er_stille: Student is quiet
    # - urolig: Student is restless
    # - bortforklaring: Student is distracted/off-task
    # - egne_notater: Custom notes
    
    def __repr__(self):
        return f'<Observation {self.observation_type} for {self.student.name}>'
    
    @property
    def observation_display(self):
        # Map for visning av underkategorier
        display_map = {
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
        return display_map.get(self.observation_type, self.observation_type)