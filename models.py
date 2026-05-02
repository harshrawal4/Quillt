import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, Index
from app import db


def gen_id():
    return str(uuid.uuid4())


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="MEMBER")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    memberships = db.relationship(
        "ProjectMember", back_populates="user", cascade="all, delete-orphan"
    )
    created_projects = db.relationship(
        "Project", back_populates="creator", foreign_keys="Project.created_by"
    )
    assigned_tasks = db.relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assigned_to"
    )

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def initials(self):
        parts = self.name.strip().split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def color_seed(self):
        s = (self.email or self.name or "").lower()
        return sum(ord(c) for c in s) % 8


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship("User", back_populates="created_projects", foreign_keys=[created_by])
    members = db.relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    tasks = db.relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )

    def member_role_for(self, user_id):
        for m in self.members:
            if m.user_id == user_id:
                return m.role
        return None

    def is_admin(self, user_id):
        return self.member_role_for(user_id) == "ADMIN"

    def is_member(self, user_id):
        return self.member_role_for(user_id) is not None

    @property
    def admin_count(self):
        return sum(1 for m in self.members if m.role == "ADMIN")


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_member"),)

    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="MEMBER")
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="memberships")
    project = db.relationship("Project", back_populates="members")


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_task_project", "project_id"),
        Index("ix_task_assignee", "assigned_to"),
        Index("ix_task_status", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="TODO")
    due_date = db.Column(db.DateTime)
    assigned_to = db.Column(db.String(36), db.ForeignKey("users.id"))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to])

    @property
    def is_overdue(self):
        return (
            self.due_date is not None
            and self.status != "DONE"
            and self.due_date < datetime.utcnow()
        )

    @property
    def status_label(self):
        return {"TODO": "To do", "IN_PROGRESS": "In progress", "DONE": "Done"}.get(
            self.status, self.status
        )
