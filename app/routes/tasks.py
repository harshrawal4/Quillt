from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Task, Project, ProjectMember
from app.forms import TaskForm

tasks_bp = Blueprint("tasks", __name__)


def _get_task_or_404(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)
    return task


def _membership(task):
    return ProjectMember.query.filter_by(
        user_id=current_user.id, project_id=task.project_id
    ).first()


@tasks_bp.route("/<task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    task = _get_task_or_404(task_id)
    membership = _membership(task)
    if not membership:
        abort(403)

    new_status = request.form.get("status", "").upper()
    if new_status not in ("TODO", "IN_PROGRESS", "DONE"):
        flash("Invalid status.", "error")
        return redirect(url_for("projects.detail", project_id=task.project_id))

    task.status = new_status
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("projects.detail", project_id=task.project_id))


@tasks_bp.route("/<task_id>/edit", methods=["POST"])
@login_required
def edit(task_id):
    task = _get_task_or_404(task_id)
    membership = _membership(task)
    if not membership or membership.role != "ADMIN":
        flash("Only project admins can edit task details.", "error")
        return redirect(url_for("projects.detail", project_id=task.project_id))

    project = db.session.get(Project, task.project_id)
    form = TaskForm()
    form.assigned_to.choices = [("", "Unassigned")] + [
        (m.user.id, f"{m.user.name} ({m.user.email})") for m in project.members
    ]

    if not form.validate_on_submit():
        flash("Please correct the form errors.", "error")
        return redirect(url_for("projects.detail", project_id=task.project_id))

    new_assignee = form.assigned_to.data or None
    if new_assignee and not project.is_member(new_assignee):
        flash("Assignee must be a project member.", "error")
        return redirect(url_for("projects.detail", project_id=task.project_id))

    task.title = form.title.data.strip()
    task.description = (form.description.data or "").strip() or None
    task.assigned_to = new_assignee
    task.due_date = form.due_date.data
    task.status = form.status.data
    task.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Task updated.", "success")
    return redirect(url_for("projects.detail", project_id=task.project_id))


@tasks_bp.route("/<task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    task = _get_task_or_404(task_id)
    membership = _membership(task)
    if not membership or membership.role != "ADMIN":
        flash("Only project admins can delete tasks.", "error")
        return redirect(url_for("projects.detail", project_id=task.project_id))

    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("projects.detail", project_id=project_id))
