from app import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dialogues = db.relationship('Dialogue', backref='host', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Dialogue Model
class Dialogue(db.Model):
    __tablename__ = 'dialogue'
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(3), unique=True, nullable=False)
    time_limit = db.Column(db.Integer)  # in minutes
    topic_prompt = db.Column(db.Text, nullable=False)
    relevant_info_text = db.Column(db.Text)
    relevant_info_file = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    participants = db.relationship('Participant', backref='dialogue', lazy=True)
    arguments = db.relationship('Argument', backref='dialogue', lazy=True)

# Participant Model
class Participant(db.Model):
    __tablename__ = 'participant'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogue.id'), nullable=False)
    is_host = db.Column(db.Boolean, default=False)
    responses = db.relationship('Response', backref='participant', lazy=True)
    ratings = db.relationship('Rating', backref='participant', lazy=True)

# Response Model
class Response(db.Model):
    __tablename__ = 'response'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogue.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    position = db.Column(db.Text)
    justification = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Argument Model
class Argument(db.Model):
    __tablename__ = 'argument'
    id = db.Column(db.Integer, primary_key=True)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogue.id'), nullable=False)
    merged_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.relationship('Rating', backref='argument', lazy=True)

# Rating Model
class Rating(db.Model):
    __tablename__ = 'rating'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    argument_id = db.Column(db.Integer, db.ForeignKey('argument.id'), nullable=False)
    agreement_score = db.Column(db.Integer, nullable=False)
    validity_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
