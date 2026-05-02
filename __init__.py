import os
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

    db_url = os.environ.get("DATABASE_URL", "sqlite:///quill.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.tasks import tasks_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%b %d, %Y"):
        if not value:
            return ""
        return value.strftime(fmt)

    @app.template_filter("relative")
    def relative(value):
        if not value:
            return ""
        delta = value.date() - datetime.utcnow().date()
        days = delta.days
        if days == 0:
            return "today"
        if days == 1:
            return "tomorrow"
        if days == -1:
            return "yesterday"
        if days < 0:
            return f"{abs(days)} days ago"
        if days < 30:
            return f"in {days} days"
        return value.strftime("%b %d, %Y")

    with app.app_context():
        db.create_all()

    return app
