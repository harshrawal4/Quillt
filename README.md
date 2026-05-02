# Quill — Team Task Manager (Python / Flask)

A small, single-stack team task manager. Sign up, create projects, invite teammates with roles, assign tasks with due dates, and watch progress on a clean dashboard.

Built with Flask and Postgres. No JavaScript framework, no build step. Server-rendered HTML, plain CSS, one tiny JS file.

---

## What's in the box

- **Authentication** — signup, login, logout. Passwords hashed with Werkzeug's `pbkdf2`. Sessions managed by Flask-Login.
- **Roles** — global role per user (`ADMIN` / `MEMBER`) plus a per-project role for each membership. The first user to sign up becomes a workspace admin.
- **Projects** — create, list, delete (admin only). Add and remove members by email.
- **Tasks** — title, description, due date, assignee, status (`TODO` / `IN_PROGRESS` / `DONE`). Overdue is computed on read so it's always current.
- **Dashboard** — total / completed / pending / overdue counts, completion bar, recent activity, project filter.
- **Security** — CSRF tokens on every form (Flask-WTF), parameterized queries (SQLAlchemy), server-side validation (WTForms).

---

## Tech stack

| Layer    | Tool |
| -------- | ---- |
| Web      | Flask 3 |
| ORM      | SQLAlchemy + Flask-SQLAlchemy |
| Auth     | Flask-Login + Werkzeug password hashing |
| Forms    | Flask-WTF + WTForms |
| Database | PostgreSQL (Neon-hosted, swappable for any Postgres) |
| Templates| Jinja2 (server-rendered HTML) |
| Server   | Gunicorn in production, Flask dev server locally |

---

## Project structure

```
quill-py/
├── app/
│   ├── __init__.py            app factory, extensions, filters
│   ├── models.py              User, Project, ProjectMember, Task
│   ├── forms.py               WTForms classes
│   ├── routes/
│   │   ├── main.py            /
│   │   ├── auth.py            /auth/{signup,login,logout}
│   │   ├── projects.py        /projects, /projects/<id>, members
│   │   ├── tasks.py           /tasks/<id>/{status,edit,delete}
│   │   └── dashboard.py       /dashboard
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/{login,signup}.html
│   │   ├── projects/{index,detail}.html
│   │   └── dashboard.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── run.py                     entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Local setup

### 1. Prerequisites

- Python **3.10+** (`python --version`)
- pip
- A PostgreSQL database (the included `.env` points at a Neon instance — swap for your own in production)

### 2. Install

```bash
git clone <your-repo> quill-py
cd quill-py

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
SECRET_KEY=<run the line below to generate one>
FLASK_ENV=development
PORT=5000
```

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run

```bash
python run.py
```

The app starts at `http://localhost:5000`. Tables are created automatically on first launch (`db.create_all()`).

Sign up — the first user becomes the workspace admin.

---

## Environment variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | `sqlite:///quill.db` | Postgres connection string. `postgres://` URLs are auto-rewritten to `postgresql://`. |
| `SECRET_KEY` | yes | `dev-secret-change-me` | Long random string. Used for session cookies and CSRF. |
| `PORT` | no | `5000` | HTTP port. Railway / Heroku set this automatically. |
| `FLASK_ENV` | no | `development` | Set to `production` to disable debug mode. |

---

## Database schema

Four tables:

```
users            id, name, email (unique), password_hash, role, created_at
projects         id, name, description, created_by → users, created_at
project_members  id, user_id → users, project_id → projects, role,
                 UNIQUE(user_id, project_id)
tasks            id, title, description, status, due_date,
                 assigned_to → users, project_id → projects, created_at, updated_at
```

- All ids are UUIDs.
- Deleting a project cascades to its memberships and tasks.
- Indexes on `tasks.project_id`, `tasks.assigned_to`, `tasks.status` for dashboard queries.

---

## Routes

### Auth
| Method | Path | Description |
| --- | --- | --- |
| GET / POST | `/auth/signup` | Sign up (form on GET, submit on POST) |
| GET / POST | `/auth/login` | Sign in |
| POST | `/auth/logout` | Sign out |

### Projects
| Method | Path | Description |
| --- | --- | --- |
| GET / POST | `/projects/` | List your projects, create a new one (POST) |
| GET / POST | `/projects/<id>` | Project detail; create task (POST `form_type=task`) |
| POST | `/projects/<id>/delete` | Admin-only |
| POST | `/projects/<id>/members` | Add member (admin) |
| POST | `/projects/<id>/members/<member_id>/remove` | Remove member (admin or self) |

### Tasks
| Method | Path | Description |
| --- | --- | --- |
| POST | `/tasks/<id>/status` | Update status (any project member) |
| POST | `/tasks/<id>/edit` | Edit full task (admin only) |
| POST | `/tasks/<id>/delete` | Delete task (admin only) |

### Dashboard
| Method | Path | Description |
| --- | --- | --- |
| GET | `/dashboard/?project_id=` | Stats + recent activity, optional per-project filter |

---

## Roles & permissions

| Action | Project MEMBER | Project ADMIN |
| --- | :---: | :---: |
| View project | ✅ | ✅ |
| Create task | ✅ | ✅ |
| Update task **status** | ✅ | ✅ |
| Edit task title / description / due date / assignee | ❌ | ✅ |
| Delete task | ❌ | ✅ |
| Add / remove project members | ❌ | ✅ |
| Delete project | ❌ | ✅ |

The last admin of a project cannot be removed — that would leave it unmanageable.

---

## Deployment on Railway

1. Push the repo to GitHub.
2. **Railway → New Project → Deploy from GitHub.**
3. Set environment variables in the Railway dashboard:
   - `DATABASE_URL` — your Postgres URL (or attach the Postgres plugin and let Railway inject it)
   - `SECRET_KEY` — long random string
   - `FLASK_ENV` — `production`
4. Set the start command:
   ```
   gunicorn run:app --bind 0.0.0.0:$PORT
   ```
5. Railway auto-detects Python from `requirements.txt` and builds.

For Render, Heroku, Fly.io — same idea, same start command. Add a `Procfile` if your platform needs one:

```
web: gunicorn run:app --bind 0.0.0.0:$PORT
```

---

## Recording a demo video

Two- to four-minute flow that exercises every feature:

1. **Sign up** the first user (becomes admin). Show the clean login screen.
2. **Create a project** named "Q4 Launch" with a short description.
3. **In a private window, sign up a second user** — "Grace".
4. **Back as admin**, add Grace as a project member with `MEMBER` role.
5. **Create three tasks** — varied due dates including one in the past so it shows as **Overdue**. Assign one to Grace.
6. **Switch to Grace's window**, change her assigned task to `In progress`. Show that the Delete button isn't visible — members can't delete.
7. **Back as admin**, visit the Dashboard. Walk through the four stat cards and the completion bar. Use the filter dropdown to scope to one project.
8. **Mark a task `Done`** to show the completion bar tick up.
9. **Delete a task and a project** to show admin-only actions and cascade.

Good free recorders: Loom, OBS Studio, macOS QuickTime, Windows Game Bar (Win+G).

---

## Testing

A smoke test that exercises auth, project CRUD, task CRUD, role enforcement, and the dashboard:

```bash
python test_smoke.py
```

Uses an in-memory SQLite so it's fast and self-contained.

---

## Troubleshooting

**`sqlalchemy.exc.OperationalError: connection refused`**
Your `DATABASE_URL` is wrong or the host blocks your IP. With Neon, use the **pooled** connection string (host ends in `-pooler`).

**`The CSRF token is missing` or `400 Bad Request` on form submit**
Your `SECRET_KEY` is empty or changed mid-session. Set a permanent one in `.env` and re-run.

**`Address already in use`**
Default port is 5000. Change with `PORT=5001 python run.py`.

**Schema changes aren't reflected**
The app uses `db.create_all()` which only creates new tables, never alters existing ones. For production-grade schema migrations add Flask-Migrate (Alembic). For dev you can drop the tables and let them re-create.
