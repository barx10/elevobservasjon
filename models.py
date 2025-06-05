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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Valid observation types:
    # - deltar_muntlig: Student participates verbally
    # - folger_med: Student pays attention
    # - er_stille: Student is quiet
    # - urolig: Student is restless
    # - bortforklaring: Student is distracted/off-task
    
    def __repr__(self):
        return f'<Observation {self.observation_type} for {self.student.name}>'
    
    @property
    def observation_display(self):
        """Return Norwegian display text for observation type"""
        display_map = {
            'deltar_muntlig': 'Deltar muntlig',
            'folger_med': 'Følger med',
            'er_stille': 'Er stille',
            'urolig': 'Urolig',
            'bortforklaring': 'Bortforklaring/avledning'
        }
        return display_map.get(self.observation_type, self.observation_type)