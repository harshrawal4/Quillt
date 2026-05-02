from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from app import db
from app.models import Project, ProjectMember, Task

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    membership_rows = ProjectMember.query.filter_by(user_id=current_user.id).all()
    allowed_ids = [m.project_id for m in membership_rows]

    projects = (
        Project.query.filter(Project.id.in_(allowed_ids))
        .order_by(Project.created_at.desc())
        .all()
        if allowed_ids
        else []
    )

    selected_project_id = request.args.get("project_id") or ""
    if selected_project_id and selected_project_id not in allowed_ids:
        selected_project_id = ""

    if selected_project_id:
        task_filter = [Task.project_id == selected_project_id]
    else:
        task_filter = [Task.project_id.in_(allowed_ids)] if allowed_ids else [Task.id == None]

    now = datetime.utcnow()

    base = Task.query.filter(*task_filter)
    total = base.count()
    completed = base.filter(Task.status == "DONE").count()
    in_progress = base.filter(Task.status == "IN_PROGRESS").count()
    todo = base.filter(Task.status == "TODO").count()
    overdue = base.filter(
        and_(Task.status != "DONE", Task.due_date.isnot(None), Task.due_date < now)
    ).count()
    pending = todo + in_progress

    assigned_to_me = base.filter(Task.assigned_to == current_user.id).count()

    recent = (
        base.order_by(Task.updated_at.desc()).limit(8).all()
    )

    completion_pct = round((completed / total) * 100) if total else 0

    stats = {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "todo": todo,
        "in_progress": in_progress,
        "assigned_to_me": assigned_to_me,
        "projects": 1 if selected_project_id else len(allowed_ids),
        "completion_pct": completion_pct,
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        recent=recent,
        projects=projects,
        selected_project_id=selected_project_id,
    )
