from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Project, ProjectMember, User, Task
from app.forms import ProjectForm, AddMemberForm, TaskForm, StatusForm

projects_bp = Blueprint("projects", __name__)


def project_member_required(role=None):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(project_id, *args, **kwargs):
            project = db.session.get(Project, project_id)
            if not project:
                abort(404)
            membership_role = project.member_role_for(current_user.id)
            if not membership_role:
                abort(403)
            if role == "ADMIN" and membership_role != "ADMIN":
                flash("Only project admins can do that.", "error")
                return redirect(url_for("projects.detail", project_id=project_id))
            return view(project_id, project=project, *args, **kwargs)

        return wrapped

    return decorator


@projects_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data.strip(),
            description=(form.description.data or "").strip() or None,
            created_by=current_user.id,
        )
        project.members.append(ProjectMember(user_id=current_user.id, role="ADMIN"))
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{project.name}" created.', "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    member_rows = (
        ProjectMember.query.filter_by(user_id=current_user.id)
        .join(Project)
        .order_by(Project.created_at.desc())
        .all()
    )
    projects = [m.project for m in member_rows]
    project_role = {m.project_id: m.role for m in member_rows}

    return render_template(
        "projects/index.html",
        projects=projects,
        project_role=project_role,
        form=form,
    )


@projects_bp.route("/<project_id>", methods=["GET", "POST"])
@project_member_required()
def detail(project_id, project):
    task_form = TaskForm()
    member_choices = [("", "Unassigned")] + [
        (m.user.id, f"{m.user.name} ({m.user.email})") for m in project.members
    ]
    task_form.assigned_to.choices = member_choices

    add_member_form = AddMemberForm()

    if request.method == "POST" and request.form.get("form_type") == "task":
        if task_form.validate():
            task = Task(
                title=task_form.title.data.strip(),
                description=(task_form.description.data or "").strip() or None,
                project_id=project.id,
                status=task_form.status.data,
                due_date=task_form.due_date.data,
                assigned_to=task_form.assigned_to.data or None,
            )
            if task.assigned_to and not project.is_member(task.assigned_to):
                flash("Assignee must be a project member.", "error")
            else:
                db.session.add(task)
                db.session.commit()
                flash("Task created.", "success")
                return redirect(url_for("projects.detail", project_id=project.id))

    tasks = (
        Task.query.filter_by(project_id=project.id)
        .order_by(Task.status.asc(), Task.due_date.asc().nulls_last(), Task.created_at.desc())
        .all()
    )
    grouped = {"TODO": [], "IN_PROGRESS": [], "DONE": []}
    for t in tasks:
        grouped.setdefault(t.status, []).append(t)

    role = project.member_role_for(current_user.id)
    return render_template(
        "projects/detail.html",
        project=project,
        grouped=grouped,
        task_form=task_form,
        add_member_form=add_member_form,
        my_role=role,
        status_form=StatusForm(),
    )


@projects_bp.route("/<project_id>/delete", methods=["POST"])
@project_member_required(role="ADMIN")
def delete(project_id, project):
    name = project.name
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{name}" deleted.', "info")
    return redirect(url_for("projects.index"))


@projects_bp.route("/<project_id>/members", methods=["POST"])
@project_member_required(role="ADMIN")
def add_member(project_id, project):
    form = AddMemberForm()
    if not form.validate_on_submit():
        flash("Please provide a valid email.", "error")
        return redirect(url_for("projects.detail", project_id=project.id))

    email = form.email.data.strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("No user with that email. Ask them to sign up first.", "error")
        return redirect(url_for("projects.detail", project_id=project.id))

    if project.is_member(user.id):
        flash(f"{user.name} is already a member.", "info")
        return redirect(url_for("projects.detail", project_id=project.id))

    db.session.add(ProjectMember(user_id=user.id, project_id=project.id, role=form.role.data))
    db.session.commit()
    flash(f"Added {user.name} to the project.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<project_id>/members/<member_id>/remove", methods=["POST"])
@project_member_required(role="ADMIN")
def remove_member(project_id, project, member_id):
    member = db.session.get(ProjectMember, member_id)
    if not member or member.project_id != project.id:
        flash("Member not found.", "error")
        return redirect(url_for("projects.detail", project_id=project.id))

    if member.role == "ADMIN" and project.admin_count <= 1:
        flash("Cannot remove the last admin of the project.", "error")
        return redirect(url_for("projects.detail", project_id=project.id))

    is_self = member.user_id == current_user.id
    db.session.delete(member)
    db.session.commit()

    if is_self:
        flash("You left the project.", "info")
        return redirect(url_for("projects.index"))

    flash("Member removed.", "info")
    return redirect(url_for("projects.detail", project_id=project.id))
