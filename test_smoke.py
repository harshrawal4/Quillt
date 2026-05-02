import os
import sys
import tempfile

os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mkdtemp()}/test.db'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['WTF_CSRF_ENABLED'] = 'False'

from app import create_app, db
from app.models import User, Project, ProjectMember, Task

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

client = app.test_client()


def assert_eq(actual, expected, msg=''):
    if actual != expected:
        print(f'FAIL {msg}: expected {expected!r}, got {actual!r}')
        sys.exit(1)
    print(f'OK   {msg}')


def assert_in(needle, haystack, msg=''):
    if needle not in haystack:
        print(f'FAIL {msg}: {needle!r} not in response')
        sys.exit(1)
    print(f'OK   {msg}')


print('=== Auth ===')

r = client.get('/')
assert_eq(r.status_code, 302, 'GET / unauthed redirects')

r = client.post('/auth/signup', data={
    'name': 'Ada Lovelace',
    'email': 'ada@example.com',
    'password': 'hunter12',
    'confirm': 'hunter12',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'signup first user')
assert_in(b'Dashboard', r.data, 'redirect to dashboard after signup')

with app.app_context():
    ada = User.query.filter_by(email='ada@example.com').first()
    assert_eq(ada is not None, True, 'first user persisted')
    assert_eq(ada.role, 'ADMIN', 'first user is global ADMIN')


print('\n=== Project create & list ===')

r = client.post('/projects/', data={
    'name': 'Q4 Launch',
    'description': 'Ship the redesign',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'create project')
assert_in(b'Q4 Launch', r.data, 'project visible on detail page')

with app.app_context():
    project = Project.query.filter_by(name='Q4 Launch').first()
    project_id = project.id
    assert_eq(project.is_admin(ada.id), True, 'creator is project ADMIN')


print('\n=== Member management ===')

client.post('/auth/logout')
r = client.post('/auth/signup', data={
    'name': 'Grace Hopper',
    'email': 'grace@example.com',
    'password': 'navy1906',
    'confirm': 'navy1906',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'sign up second user')

with app.app_context():
    grace = User.query.filter_by(email='grace@example.com').first()
    assert_eq(grace.role, 'MEMBER', 'second user is global MEMBER')
    grace_id = grace.id

client.post('/auth/logout')
r = client.post('/auth/login', data={
    'email': 'ada@example.com',
    'password': 'hunter12',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'ada logs back in')

r = client.post(f'/projects/{project_id}/members', data={
    'email': 'grace@example.com',
    'role': 'MEMBER',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'admin adds member')

with app.app_context():
    project = db.session.get(Project, project_id)
    assert_eq(len(project.members), 2, 'project has 2 members')


print('\n=== Task CRUD ===')

r = client.post(f'/projects/{project_id}', data={
    'form_type': 'task',
    'title': 'Write launch post',
    'description': 'Blog announcement',
    'assigned_to': grace_id,
    'due_date': '2027-01-15',
    'status': 'TODO',
}, follow_redirects=True)
assert_eq(r.status_code, 200, 'admin creates task')
assert_in(b'Write launch post', r.data, 'task appears in detail page')

with app.app_context():
    task = Task.query.filter_by(title='Write launch post').first()
    task_id = task.id
    assert_eq(task.assigned_to, grace_id, 'task assigned to grace')

r = client.post(f'/tasks/{task_id}/status', data={'status': 'IN_PROGRESS'}, follow_redirects=True)
assert_eq(r.status_code, 200, 'update status')

with app.app_context():
    task = db.session.get(Task, task_id)
    assert_eq(task.status, 'IN_PROGRESS', 'status persisted')


print('\n=== Member-level permissions ===')

client.post('/auth/logout')
client.post('/auth/login', data={'email': 'grace@example.com', 'password': 'navy1906'}, follow_redirects=True)

r = client.post(f'/tasks/{task_id}/status', data={'status': 'DONE'}, follow_redirects=True)
assert_eq(r.status_code, 200, 'member can change status')
with app.app_context():
    task = db.session.get(Task, task_id)
    assert_eq(task.status, 'DONE', 'status changed by member')

r = client.post(f'/tasks/{task_id}/delete', follow_redirects=True)
with app.app_context():
    task = db.session.get(Task, task_id)
    assert_eq(task is not None, True, 'member CANNOT delete task')

r = client.post(f'/projects/{project_id}/delete', follow_redirects=True)
with app.app_context():
    project = db.session.get(Project, project_id)
    assert_eq(project is not None, True, 'member CANNOT delete project')


print('\n=== Dashboard ===')

client.post('/auth/logout')
client.post('/auth/login', data={'email': 'ada@example.com', 'password': 'hunter12'}, follow_redirects=True)

r = client.get('/dashboard/')
assert_eq(r.status_code, 200, 'dashboard renders')
assert_in(b'Total tasks', r.data, 'has total tasks stat')
assert_in(b'Completed', r.data, 'has completed stat')
assert_in(b'Pending', r.data, 'has pending stat')
assert_in(b'Overdue', r.data, 'has overdue stat')


print('\n=== Admin task delete ===')

r = client.post(f'/tasks/{task_id}/delete', follow_redirects=True)
assert_eq(r.status_code, 200, 'admin deletes task')
with app.app_context():
    task = db.session.get(Task, task_id)
    assert_eq(task, None, 'task removed')


print('\n=== Project delete cascade ===')

r = client.post(f'/projects/{project_id}/delete', follow_redirects=True)
with app.app_context():
    project = db.session.get(Project, project_id)
    assert_eq(project, None, 'project removed')
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    assert_eq(len(members), 0, 'memberships cascaded')


print('\n=== All tests passed ===')
