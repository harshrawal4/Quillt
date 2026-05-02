from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class SignupForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class ProjectForm(FlaskForm):
    name = StringField("Project name", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])


class AddMemberForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = SelectField(
        "Role", choices=[("MEMBER", "Member"), ("ADMIN", "Admin")], default="MEMBER"
    )


class TaskForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    assigned_to = SelectField("Assign to", choices=[], validators=[Optional()])
    due_date = DateField("Due date", validators=[Optional()], format="%Y-%m-%d")
    status = SelectField(
        "Status",
        choices=[("TODO", "To do"), ("IN_PROGRESS", "In progress"), ("DONE", "Done")],
        default="TODO",
    )


class StatusForm(FlaskForm):
    status = HiddenField(validators=[DataRequired()])
