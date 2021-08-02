from wtforms import StringField, SubmitField, SelectField, PasswordField
from flask_wtf import FlaskForm
from wtforms.validators import *
import email_validator

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class UserForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired()])
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField("Choose a password",
                             validators=[DataRequired(), EqualTo('confirm', message="Passwords must match.")])
    confirm = PasswordField("Confirm password", validators=[DataRequired()])
    submit = SubmitField('Register')
