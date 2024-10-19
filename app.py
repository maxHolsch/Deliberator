from flask import Flask, render_template, redirect, url_for, flash, request, session, send_from_directory
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms import LoginForm, SignUpForm, CreateDialogueForm, JoinDialogueForm, ResponseForm, RateArgumentsForm
from models import db, User, Dialogue, Participant, Response, Argument, Rating
from werkzeug.utils import secure_filename
import os
import random
import string
import openai

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Generate unique 3-digit code
def generate_unique_code():
    while True:
        code = ''.join(random.choices(string.digits, k=3))
        if not Dialogue.query.filter_by(code=code).first():
            return code

# Home/Landing Page
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = JoinDialogueForm()
    if form.validate_on_submit():
        code = form.code.data
        dialogue = Dialogue.query.filter_by(code=code).first()
        if dialogue:
            return redirect(url_for('participant_waiting', code=code))
        else:
            flash('Dialogue with this code does not exist.', 'danger')
    return render_template('index.html', form=form)

# Sign Up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = SignUpForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Create New Dialogue
@app.route('/create-dialogue', methods=['GET', 'POST'])
@login_required
def create_dialogue():
    form = CreateDialogueForm()
    if form.validate_on_submit():
        code = generate_unique_code()
        time_limit = form.hours.data * 60 + form.minutes.data
        dialogue = Dialogue(
            host_id=current_user.id,
            code=code,
            time_limit=time_limit,
            topic_prompt=form.topic_prompt.data,
            relevant_info_text=form.relevant_info_text.data
        )
        # Handle file upload
        if form.relevant_info_file.data:
            file = form.relevant_info_file.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                dialogue.relevant_info_file = filename
            else:
                flash('Invalid file type.', 'danger')
                return render_template('create_dialogue.html', form=form)
        db.session.add(dialogue)
        db.session.commit()
        # Add host as a participant
        participant = Participant(user_id=current_user.id, dialogue_id=dialogue.id, is_host=True)
        db.session.add(participant)
        db.session.commit()
        return redirect(url_for('host_waiting', code=code))
    return render_template('create_dialogue.html', form=form)

# Host Waiting Page
@app.route('/host-waiting/<code>', methods=['GET', 'POST'])
@login_required
def host_waiting(code):
    dialogue = Dialogue.query.filter_by(code=code).first_or_404()
    if dialogue.host_id != current_user.id:
        flash('You are not authorized to view this page.', 'danger')
        return redirect(url_for('index'))
    participants = Participant.query.filter_by(dialogue_id=dialogue.id).count()
    if request.method == 'POST':
        if 'start' in request.form:
            dialogue.is_active = True
            db.session.commit()
            # Notify participants (Implement real-time notification)
            return redirect(url_for('deliberation', code=code))
        elif 'cancel' in request.form:
            # Remove dialogue and participants
            db.session.delete(dialogue)
            db.session.commit()
            flash('Dialogue cancelled.', 'info')
            return redirect(url_for('index'))
    return render_template('host_waiting.html', dialogue=dialogue, participants=participants)

# Participant Waiting Page
@app.route('/participant-waiting/<code>')
@login_required
def participant_waiting(code):
    dialogue = Dialogue.query.filter_by(code=code).first_or_404()
    participant = Participant.query.filter_by(user_id=current_user.id, dialogue_id=dialogue.id).first()
    if not participant:
        participant = Participant(user_id=current_user.id, dialogue_id=dialogue.id)
        db.session.add(participant)
        db.session.commit()
    if dialogue.is_active:
        return redirect(url_for('deliberation', code=code))
    return render_template('participant_waiting.html', dialogue=dialogue)

# Deliberation Page
@app.route('/deliberation/<code>', methods=['GET', 'POST'])
@login_required
def deliberation(code):
    dialogue = Dialogue.query.filter_by(code=code).first_or_404()
    participant = Participant.query.filter_by(user_id=current_user.id, dialogue_id=dialogue.id).first_or_404()
    form = ResponseForm()
    if form.validate_on_submit():
        response = Response(
            participant_id=participant.id,
            dialogue_id=dialogue.id,
            text=form.response.data
        )
        db.session.add(response)
        db.session.commit()
        # After all participants submit, process responses
        total_participants = Participant.query.filter_by(dialogue_id=dialogue.id).count()
        total_responses = Response.query.filter_by(dialogue_id=dialogue.id).count()
        if total_responses == total_participants:
            process_responses(dialogue)
            return redirect(url_for('rate_arguments', code=code))
        else:
            flash('Waiting for other participants to submit their responses.', 'info')
    return render_template('deliberation.html', dialogue=dialogue, form=form)

# Rate Arguments Page
@app.route('/rate-arguments/<code>', methods=['GET', 'POST'])
@login_required
def rate_arguments(code):
    dialogue = Dialogue.query.filter_by(code=code).first_or_404()
    participant = Participant.query.filter_by(user_id=current_user.id, dialogue_id=dialogue.id).first_or_404()
    arguments = Argument.query.filter_by(dialogue_id=dialogue.id).all()
    form = RateArgumentsForm()
    if request.method == 'POST':
        for arg in arguments:
            agreement_score = request.form.get(f'agreement_{arg.id}')
            validity_score = request.form.get(f'validity_{arg.id}')
            if agreement_score and validity_score:
                rating = Rating(
                    participant_id=participant.id,
                    argument_id=arg.id,
                    agreement_score=int(agreement_score),
                    validity_score=int(validity_score)
                )
                db.session.add(rating)
        db.session.commit()
        return redirect(url_for('results', code=code))
    return render_template('rate_arguments.html', dialogue=dialogue, arguments=arguments)

# Results Page
@app.route('/results/<code>')
@login_required
def results(code):
    dialogue = Dialogue.query.filter_by(code=code).first_or_404()
    # Calculate top arguments
    arguments = Argument.query.filter_by(dialogue_id=dialogue.id).all()
    argument_scores = []
    for arg in arguments:
        ratings = Rating.query.filter_by(argument_id=arg.id).all()
        if ratings:
            avg_agreement = sum([r.agreement_score for r in ratings]) / len(ratings)
            avg_validity = sum([r.validity_score for r in ratings]) / len(ratings)
            total_score = (avg_agreement + avg_validity) / 2
            argument_scores.append((arg, total_score))
    # Sort and select top N arguments
    argument_scores.sort(key=lambda x: x[1], reverse=True)
    num_participants = Participant.query.filter_by(dialogue_id=dialogue.id).count()
    top_n = num_participants // 3
    top_arguments = [arg[0] for arg in argument_scores[:top_n]]
    return render_template('results.html', dialogue=dialogue, top_arguments=top_arguments)

# Process Responses with OpenAI API
def process_responses(dialogue):
    responses = Response.query.filter_by(dialogue_id=dialogue.id).all()
    # Extract positions and justifications
    for response in responses:
        position, justification = extract_position_justification(response.text)
        response.position = position
        response.justification = justification
        db.session.commit()
    # Merge arguments
    merged_arguments = merge_arguments(responses)
    for arg_text in merged_arguments:
        argument = Argument(
            dialogue_id=dialogue.id,
            merged_text=arg_text
        )
        db.session.add(argument)
    db.session.commit()

# Extract Position and Justification
def extract_position_justification(text):
    prompt = f"""
    Please extract the main position and justification from the following text:

    "{text}"

    Provide the position and justification separately in the format:
    Position: ...
    Justification: ...
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    result = response.choices[0].text.strip()
    # Parse the result
    position = ''
    justification = ''
    lines = result.split('\n')
    for line in lines:
        if line.startswith('Position:'):
            position = line.replace('Position:', '').strip()
        elif line.startswith('Justification:'):
            justification = line.replace('Justification:', '').strip()
    return position, justification

# Merge Arguments
def merge_arguments(responses):
    positions_justifications = [f"Position: {r.position}\nJustification: {r.justification}" for r in responses]
    prompt = f"""
    Please group the following positions and justifications into major arguments, merging similar ones:

    {'\n\n'.join(positions_justifications)}

    Provide a list of merged arguments.
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=500
    )
    result = response.choices[0].text.strip()
    # Split the result into individual arguments
    merged_arguments = result.split('\n\n')
    return merged_arguments

# Serve Uploaded Files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
