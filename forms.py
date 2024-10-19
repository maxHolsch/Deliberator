# forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    FileField,
    IntegerField,
    ValidationError,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)
from flask_wtf.file import FileAllowed

def word_count_check(min=60, max=200):
    message = f'Field must be between {min} and {max} words.'
    def _word_count_check(form, field):
        word_count = len(field.data.strip().split())
        if word_count < min or word_count > max:
            raise ValidationError(message)
    return _word_count_check

class LoginForm(FlaskForm):
    email = StringField(
        'Email', validators=[DataRequired(), Email(message='Invalid email address')]
    )
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignUpForm(FlaskForm):
    email = StringField(
        'Email', validators=[DataRequired(), Email(message='Invalid email address')]
    )
    password = PasswordField(
        'Password', validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match'),
        ],
    )
    submit = SubmitField('Sign Up')

class CreateDialogueForm(FlaskForm):
    hours = IntegerField(
        'Hours', validators=[NumberRange(min=0)], default=0
    )
    minutes = IntegerField(
        'Minutes', validators=[NumberRange(min=0, max=59)], default=0
    )
    topic_prompt = TextAreaField('Topic/Prompt', validators=[DataRequired()])
    relevant_info_text = TextAreaField(
        'Relevant Information (Text)', validators=[Optional()]
    )
    relevant_info_file = FileField(
        'Relevant Information (File)',
        validators=[
            Optional(),
            FileAllowed(
                ['pdf', 'docx', 'csv', 'txt'], 'Invalid file type'
            ),
        ],
    )
    submit = SubmitField('Create')

class JoinDialogueForm(FlaskForm):
    code = StringField(
        '3-Digit Code',
        validators=[DataRequired(), Length(min=3, max=3)],
    )
    submit = SubmitField('Join Dialogue')

class ResponseForm(FlaskForm):
    response = TextAreaField(
        'Your Response (60-200 words)',
        validators=[DataRequired(), word_count_check(min=60, max=200)],
    )
    submit = SubmitField('Submit Response')

class RateArgumentsForm(FlaskForm):
    # The rating fields are dynamically generated in the template
    pass
