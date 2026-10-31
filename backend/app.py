"""Development MVP API. Use stronger deployment/session policies before production."""
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'development-only-replace-me'),
    SQLALCHEMY_DATABASE_URI='sqlite:///' + str(BASE / 'helpdesk.db').replace('\\', '/'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # Set True when served over HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
)
CORS(app, origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')], supports_credentials=True)
db = SQLAlchemy(app)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')

    def json(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Open')
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    response_due_at = db.Column(db.DateTime)
    resolution_due_at = db.Column(db.DateTime)
    creator = db.relationship('User', foreign_keys=[creator_id])
    assignee = db.relationship('User', foreign_keys=[assignee_id])

    def json(self):
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'category': self.category, 'priority': self.priority, 'status': self.status,
            'creator_id': self.creator_id, 'creator': self.creator.name,
            'assignee_id': self.assignee_id,
            'assignee': self.assignee.name if self.assignee else None,
            'first_response_at': as_iso(self.first_response_at),
            'resolved_at': as_iso(self.resolved_at),
            'response_due_at': as_iso(self.response_due_at),
            'resolution_due_at': as_iso(self.resolution_due_at),
            'response_breached': bool(self.response_due_at and not self.first_response_at and utc_now() > self.response_due_at),
            'resolution_breached': bool(self.resolution_due_at and not self.resolved_at and utc_now() > self.resolution_due_at),
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z',
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    author = db.relationship('User')

    def json(self):
        return {'id': self.id, 'body': self.body, 'author': self.author.name,
                'user_id': self.user_id, 'created_at': self.created_at.isoformat() + 'Z'}


SLA_TARGETS = {
    'Critical': (15, 4), 'High': (30, 8), 'Medium': (120, 24), 'Low': (240, 72),
}  # response minutes, resolution hours; calendar time for Phase 2


def as_iso(value):
    return value.isoformat() + 'Z' if value else None


class TicketEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    detail = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    actor = db.relationship('User')

    def json(self):
        return {'id': self.id, 'kind': self.kind, 'detail': self.detail,
                'actor': self.actor.name, 'created_at': as_iso(self.created_at)}


def record(ticket, user, kind, detail):
    db.session.add(TicketEvent(ticket_id=ticket.id, actor_id=user.id,
                               kind=kind, detail=detail))


def migrate_phase2():
    """Idempotent additive SQLite migration; preserves existing Phase 1 tickets."""
    from sqlalchemy import inspect, text
    db.create_all()
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns('ticket')}
    with db.engine.begin() as connection:
        for name in ('first_response_at', 'resolved_at', 'response_due_at', 'resolution_due_at'):
            if name not in existing:
                connection.execute(text(f'ALTER TABLE ticket ADD COLUMN {name} DATETIME'))
    db.create_all()
    for ticket in db.session.execute(db.select(Ticket).where(Ticket.response_due_at.is_(None))).scalars():
        response_min, resolution_hours = SLA_TARGETS[ticket.priority]
        ticket.response_due_at = ticket.created_at + timedelta(minutes=response_min)
        ticket.resolution_due_at = ticket.created_at + timedelta(hours=resolution_hours)
        if ticket.status in ('Resolved', 'Closed'):
            ticket.resolved_at = ticket.updated_at
    db.session.commit()


def current_user():
    uid = session.get('user_id')
    user = db.session.get(User, uid) if uid else None
    return user if user and not phase8_is_disabled(user.id) else None


def auth(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(error='Please sign in'), 401
            if roles and user.role not in roles:
                return jsonify(error='Permission denied'), 403
            return fn(user, *args, **kwargs)
        return wrapper
    return decorator


def payload():
    return request.get_json(silent=True) or {}


def can_see(user, ticket):
    return user.role in ('admin', 'engineer') or ticket.creator_id == user.id


def classify(description):
    text = description.lower()
    rules = [
        ('Network', ['wifi', 'wi-fi', 'internet', 'vpn', 'network', 'router']),
        ('Hardware', ['laptop', 'keyboard', 'monitor', 'printer', 'mouse', 'battery']),
        ('Software', ['application', 'software', 'install', 'crash', 'outlook']),
        ('Access', ['password', 'login', 'account', 'locked', 'permission']),
    ]
    for category, words in rules:
        if any(word in text for word in words):
            return category
    return 'Other'


@app.get('/api/health')
def health():
    return jsonify(status='ok')


@app.post('/api/auth/register')
def register():
    data = payload()
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    if not name or len(name) > 100 or '@' not in email or len(email) > 200 or len(password) < 8:
        return jsonify(error='Provide a name, valid email, and password of at least 8 characters'), 400
    if db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none():
        return jsonify(error='Email already registered'), 409
    user = User(name=name, email=email, password_hash=generate_password_hash(password), role='employee')
    db.session.add(user)
    db.session.commit()
    session.clear()
    session.permanent = True
    session['user_id'] = user.id
    return jsonify(user=user.json()), 201


@app.post('/api/auth/login')
def login():
    data = payload()
    user = db.session.execute(db.select(User).filter_by(email=str(data.get('email', '')).strip().lower())).scalar_one_or_none()
    if not user or phase8_is_disabled(user.id) or not check_password_hash(user.password_hash, str(data.get('password', ''))):
        return jsonify(error='Invalid email or password'), 401
    session.clear()
    session.permanent = True
    session['user_id'] = user.id
    return jsonify(user=user.json())


@app.post('/api/auth/logout')
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get('/api/auth/me')
@auth()
def me(user):
    return jsonify(user=user.json())


@app.get('/api/users/engineers')
@auth('admin', 'engineer')
def engineers(user):
    return jsonify(users=[x.json() for x in db.session.execute(db.select(User).where(User.role == 'engineer')).scalars() if not phase8_is_disabled(x.id)])


@app.get('/api/tickets')
@auth()
def tickets(user):
    query = db.select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc())
    filters = request.args
    if filters.get('status'):
        query = query.where(Ticket.status == filters['status'])
    if filters.get('priority'):
        query = query.where(Ticket.priority == filters['priority'])
    if filters.get('category'):
        query = query.where(Ticket.category == filters['category'])
    if filters.get('search', '').strip():
        term = '%' + filters['search'].strip()[:100] + '%'
        query = query.where(or_(Ticket.title.ilike(term), Ticket.description.ilike(term)))
    if filters.get('assignee') == 'unassigned':
        query = query.where(Ticket.assignee_id.is_(None))
    elif filters.get('assignee') == 'mine':
        query = query.where(Ticket.assignee_id == user.id)
    if user.role == 'employee':
        query = query.where(Ticket.creator_id == user.id)
    return jsonify(tickets=[t.json() for t in db.session.execute(query).scalars()])


@app.post('/api/tickets')
@auth('employee', 'admin')
def new_ticket(user):
    data = payload()
    title = str(data.get('title', '')).strip()
    description = str(data.get('description', '')).strip()
    if not (3 <= len(title) <= 180 and 10 <= len(description) <= 5000):
        return jsonify(error='Title must be 3–180 characters and description 10–5000 characters'), 400
    category = data.get('category') or classify(title + ' ' + description)
    priority = data.get('priority', 'Medium')
    if category not in ('Network', 'Hardware', 'Software', 'Access', 'Other') or priority not in ('Low', 'Medium', 'High', 'Critical'):
        return jsonify(error='Invalid category or priority'), 400
    ticket = Ticket(title=title, description=description, category=category,
                    priority=priority, creator_id=user.id, created_at=utc_now(), updated_at=utc_now())
    response_min, resolution_min = sla_policy_for(priority)
    ticket.response_due_at = ticket.created_at + timedelta(minutes=response_min)
    ticket.resolution_due_at = ticket.created_at + timedelta(minutes=resolution_min)
    db.session.add(ticket)
    db.session.flush()
    record(ticket, user, 'created', 'Ticket created')
    phase9_route_new(ticket, user)
    db.session.commit()
    return jsonify(ticket=ticket.json()), 201


@app.get('/api/tickets/<int:ticket_id>')
@auth()
def get_ticket(user, ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    if not can_see(user, ticket):
        return jsonify(error='Permission denied'), 403
    messages = db.session.execute(db.select(Message).where(Message.ticket_id == ticket.id).order_by(Message.created_at)).scalars()
    events = db.session.execute(db.select(TicketEvent).where(TicketEvent.ticket_id == ticket.id).order_by(TicketEvent.created_at, TicketEvent.id)).scalars()
    return jsonify(ticket=ticket.json(), messages=[m.json() for m in messages], events=[e.json() for e in events])




def notify_ticket_participants(ticket, actor, body, extra_user_ids=()):
    """Create in-app notifications with existing Phase 3 notification table."""
    recipients = {ticket.creator_id, ticket.assignee_id, *extra_user_ids}
    recipients.discard(None)
    recipients.discard(actor.id)
    notification_table = db.metadata.tables.get('notification')
    if notification_table is None:
        return
    for recipient in recipients:
        db.session.execute(notification_table.insert().values(
            user_id=recipient, ticket_id=ticket.id, body=body[:300], created_at=utc_now()
        ))

@app.post('/api/tickets/<int:ticket_id>/messages')
@auth()
def post_message(user, ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    if not can_see(user, ticket):
        return jsonify(error='Permission denied'), 403
    body = str(payload().get('body', '')).strip()
    if not (1 <= len(body) <= 2000):
        return jsonify(error='Message must be 1–2000 characters'), 400
    message = Message(ticket_id=ticket.id, user_id=user.id, body=body)
    db.session.add(message)
    if user.role in ('admin', 'engineer') and ticket.first_response_at is None:
        ticket.first_response_at = utc_now()
        record(ticket, user, 'first_response', 'First support response recorded')
    record(ticket, user, 'message', 'Message sent')
    # Phase 10: messages reach the employee, assigned engineer AND active administrators.
    # Do not notify the sender or inactive administrators.
    admin_ids = [admin.id for admin in db.session.execute(
        db.select(User).where(User.role == 'admin')
    ).scalars() if not phase8_is_disabled(admin.id)]
    excerpt = ' '.join(body.split())[:115]
    notify_ticket_participants(
        ticket, user,
        f'New message from {user.name} on ticket #{ticket.id}: {excerpt}',
        extra_user_ids=admin_ids,
    )
    ticket.updated_at = utc_now()
    db.session.commit()
    return jsonify(message=message.json()), 201


@app.patch('/api/tickets/<int:ticket_id>')
@auth()
def edit_ticket(user, ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    data = payload()
    status = data.get('status')
    if user.role == 'employee':
        if ticket.creator_id != user.id or status not in ('Closed', 'Reopened'):
            return jsonify(error='Permission denied'), 403
        if ticket.status != 'Resolved' or status not in ('Closed', 'Reopened'):
            return jsonify(error='Only a resolved ticket can be confirmed or reopened'), 400
        ticket.status = 'Closed' if status == 'Closed' else 'Open'
        record(ticket, user, 'status', f'Status changed to {ticket.status}')
        if ticket.status == 'Open':
            ticket.resolved_at = None
    else:
        if 'assignee_id' in data:
            if user.role != 'admin':
                return jsonify(error='Only admins assign engineers'), 403
            assignee = db.session.get(User, data['assignee_id']) if isinstance(data['assignee_id'], int) else None
            if not assignee or assignee.role != 'engineer' or phase8_is_disabled(assignee.id):
                return jsonify(error='Choose a valid engineer'), 400
            old = ticket.assignee.name if ticket.assignee else 'Unassigned'
            ticket.assignee_id = assignee.id
            record(ticket, user, 'assignment', f'Assigned from {old} to {assignee.name}')
            if ticket.status == 'Open':
                ticket.status = 'Assigned'
        if status is not None:
            allowed = {
                'Open': ('Assigned', 'In Progress'),
                'Assigned': ('In Progress',),
                'In Progress': ('Resolved',),
                'Resolved': (),
                'Closed': (),
            }
            if status not in allowed.get(ticket.status, ()):
                return jsonify(error='Invalid status transition'), 400
            if user.role == 'engineer':
                if ticket.assignee_id not in (None, user.id):
                    return jsonify(error='Assigned to another engineer'), 403
                if ticket.assignee_id is None:
                    ticket.assignee_id = user.id
            previous = ticket.status
            if user.role in ('engineer', 'admin') and ticket.first_response_at is None:
                ticket.first_response_at = utc_now()
                record(ticket, user, 'first_response', 'First support action recorded')
            ticket.status = status
            record(ticket, user, 'status', f'Status changed from {previous} to {status}')
            if status == 'Resolved':
                ticket.resolved_at = utc_now()
            if ticket.status == 'Assigned' and ticket.assignee_id is None:
                return jsonify(error='Assign an engineer first'), 400
    if 'assignee_id' in data and user.role == 'admin':
        # Explicitly target the new assignee as well as the employee.
        notify_ticket_participants(ticket, user, f'New assignment: Ticket #{ticket.id} — {ticket.title}', extra_user_ids=(ticket.assignee_id,))
    if status is not None:
        notify_ticket_participants(ticket, user, f'Ticket #{ticket.id} status updated to {ticket.status}')
    ticket.updated_at = utc_now()
    db.session.commit()
    return jsonify(ticket=ticket.json())


@app.get('/api/stats')
@auth('admin', 'engineer')
def stats(user):
    tickets = db.session.execute(db.select(Ticket)).scalars().all()
    engineers = [x for x in db.session.execute(db.select(User).where(User.role == 'engineer')).scalars().all() if not phase8_is_disabled(x.id)]
    active = ('Open', 'Assigned', 'In Progress')
    return jsonify(workload=[{'id': e.id, 'name': e.name,
                             'active': sum(t.assignee_id == e.id and t.status in active for t in tickets),
                             'total': sum(t.assignee_id == e.id for t in tickets)} for e in engineers],
                   sla_response_breaches=sum(bool(t.response_due_at and not t.first_response_at and utc_now() > t.response_due_at) for t in tickets),
                   sla_resolution_breaches=sum(bool(t.resolution_due_at and not t.resolved_at and utc_now() > t.resolution_due_at) for t in tickets),
                   total=len(tickets), open=sum(t.status == 'Open' for t in tickets),
                   in_progress=sum(t.status in ('Assigned', 'In Progress') for t in tickets),
                   resolved=sum(t.status in ('Resolved', 'Closed') for t in tickets),
                   categories={c: sum(t.category == c for t in tickets) for c in ('Network', 'Hardware', 'Software', 'Access', 'Other')})


@app.cli.command('seed')
def seed():
    """Create development demo users. NEVER run this in production."""
    demo = [('Admin', 'admin@demo.local', 'admin'), ('Engineer', 'engineer@demo.local', 'engineer'),
            ('Employee', 'employee@demo.local', 'employee')]
    for name, email, role in demo:
        if not db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none():
            db.session.add(User(name=name, email=email, role=role,
                                password_hash=generate_password_hash('Demo12345!')))
    db.session.commit()
    print('Demo accounts seeded. Password for all: Demo12345! (local development only)')


with app.app_context():
    migrate_phase2()

from sla_phase3 import install as install_sla_phase3
sla_policy_for, sla_scan = install_sla_phase3(app, db, User, Ticket, TicketEvent, auth, utc_now, as_iso)



# Phase 4: persistent knowledge base. create_all() is safe for additive tables.
class KnowledgeArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    summary = db.Column(db.String(400), nullable=False)
    content = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(500), nullable=False, default='')
    published = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def json(self):
        return {'id': self.id, 'title': self.title, 'category': self.category,
                'summary': self.summary, 'content': self.content,
                'keywords': self.keywords, 'published': self.published,
                'created_at': as_iso(self.created_at), 'updated_at': as_iso(self.updated_at)}


def article_query_for(user):
    q = db.select(KnowledgeArticle)
    return q if user.role == 'admin' else q.where(KnowledgeArticle.published.is_(True))


def score_article(article, text, category=''):
    import re
    # Word-boundary matching prevents e.g. 'vpn' matching inside other words.
    hay = set(re.findall(r'[a-z0-9]+', text.lower()))
    phrases = [s.strip().lower() for s in article.keywords.split(',') if s.strip()]
    score = 4 if category and article.category == category else 0
    combined = text.lower()
    for phrase in phrases:
        if phrase in combined if ' ' in phrase else phrase in hay:
            score += 3
    score += sum(1 for word in re.findall(r'[a-z0-9]+', article.title.lower()) if len(word) > 3 and word in hay)
    return score


@app.get('/api/knowledge')
@auth()
def knowledge_list(user):
    query = article_query_for(user)
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()[:120]
    if category:
        query = query.where(KnowledgeArticle.category == category)
    if search:
        term = '%' + search.replace('%', r'\%').replace('_', r'\_') + '%'
        query = query.where(or_(KnowledgeArticle.title.ilike(term, escape=chr(92)),
                                KnowledgeArticle.summary.ilike(term, escape=chr(92)),
                                KnowledgeArticle.keywords.ilike(term, escape=chr(92)),
                                KnowledgeArticle.content.ilike(term, escape=chr(92))))
    articles = db.session.execute(query.order_by(KnowledgeArticle.updated_at.desc(), KnowledgeArticle.id.desc())).scalars().all()
    return jsonify(articles=[a.json() for a in articles])


@app.get('/api/knowledge/<int:article_id>')
@auth()
def knowledge_detail(user, article_id):
    article = db.get_or_404(KnowledgeArticle, article_id)
    if not article.published and user.role != 'admin':
        return jsonify(error='Article not available'), 404
    return jsonify(article=article.json())


def validate_article(data, current=None):
    fields = {k: str(data.get(k, getattr(current, k, ''))).strip() for k in ('title', 'category', 'summary', 'content', 'keywords')}
    allowed = ('Network', 'Hardware', 'Software', 'Access', 'Other')
    if not (3 <= len(fields['title']) <= 180 and fields['category'] in allowed
            and 10 <= len(fields['summary']) <= 400 and 20 <= len(fields['content']) <= 10000
            and len(fields['keywords']) <= 500):
        return None, 'Invalid article fields. Title: 3–180, summary: 10–400, content: 20–10000 characters.'
    flag = data.get('published', current.published if current else True)
    if not isinstance(flag, bool):
        return None, 'published must be true or false'
    fields['published'] = flag
    return fields, None


@app.post('/api/knowledge')
@auth('admin')
def knowledge_create(user):
    values, error = validate_article(payload())
    if error:
        return jsonify(error=error), 400
    article = KnowledgeArticle(**values)
    db.session.add(article)
    db.session.commit()
    return jsonify(article=article.json()), 201


@app.patch('/api/knowledge/<int:article_id>')
@auth('admin')
def knowledge_update(user, article_id):
    article = db.get_or_404(KnowledgeArticle, article_id)
    values, error = validate_article(payload(), article)
    if error:
        return jsonify(error=error), 400
    for field, value in values.items():
        setattr(article, field, value)
    article.updated_at = utc_now()
    db.session.commit()
    return jsonify(article=article.json())


@app.delete('/api/knowledge/<int:article_id>')
@auth('admin')
def knowledge_delete(user, article_id):
    article = db.get_or_404(KnowledgeArticle, article_id)
    db.session.delete(article)
    db.session.commit()
    return jsonify(ok=True)


@app.get('/api/tickets/<int:ticket_id>/suggestions')
@auth()
def ticket_suggestions(user, ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    if not can_see(user, ticket):
        return jsonify(error='Permission denied'), 403
    text = ticket.title + ' ' + ticket.description
    ranked = [(score_article(a, text, ticket.category), a) for a in db.session.execute(
        db.select(KnowledgeArticle).where(KnowledgeArticle.published.is_(True))).scalars()]
    ranked = sorted((x for x in ranked if x[0] > 0), key=lambda x: (-x[0], x[1].title))[:5]
    return jsonify(suggestions=[{'score': s, **a.json()} for s, a in ranked])


@app.cli.command('seed-knowledge')
def seed_knowledge():
    """Add demo help articles only when not already present; safe to rerun."""
    samples = [
        ('Wi-Fi connection troubleshooting', 'Network', 'Steps to restore office Wi-Fi connectivity.',
         '1. Toggle Wi-Fi off and on.\n2. Confirm airplane mode is off.\n3. Reconnect to the correct SSID.\n4. Restart the device.\n5. Contact IT if the issue persists.',
         'wifi, wi-fi, internet, wireless, network, router'),
        ('Reset a locked account password', 'Access', 'Safely restore access to a locked work account.',
         '1. Verify the user identity using approved procedures.\n2. Use the official password reset page.\n3. Update the password.\n4. Check MFA enrollment.\n5. Escalate repeated lockouts to IT.',
         'password, login, locked, account, sign in, access'),
        ('Printer not responding', 'Hardware', 'Check common printer connection and queue issues.',
         '1. Check printer power and error lights.\n2. Confirm paper and toner.\n3. Reconnect the printer.\n4. Clear stuck print jobs.\n5. Escalate hardware faults.',
         'printer, print, paper, toner, queue'),
        ('Application crashes on startup', 'Software', 'Diagnose recurring application crashes.',
         '1. Save your work.\n2. Restart the application.\n3. Check available disk space.\n4. Install approved updates.\n5. Send error messages to IT if the crash continues.',
         'application, crash, crashes, software, install, error'),
    ]
    created = 0
    for title, category, summary, content, keywords in samples:
        if not db.session.execute(db.select(KnowledgeArticle).where(KnowledgeArticle.title == title)).scalar_one_or_none():
            db.session.add(KnowledgeArticle(title=title, category=category, summary=summary, content=content, keywords=keywords))
            created += 1
    db.session.commit()
    print(f'Knowledge articles added: {created}')


with app.app_context():
    db.create_all()  # Create the new knowledge_article table after Phase 3 models are loaded.

# Phase 5: reporting API. Admin-only; all timestamps stored UTC.
from collections import Counter, defaultdict
from io import BytesIO, StringIO
import csv
from flask import Response, send_file


def report_filters():
    start_raw = request.args.get('start', '').strip()
    end_raw = request.args.get('end', '').strip()
    try:
        start = datetime.strptime(start_raw, '%Y-%m-%d') if start_raw else None
        end = datetime.strptime(end_raw, '%Y-%m-%d') + timedelta(days=1) if end_raw else None
    except ValueError:
        return None, None, 'Dates must be YYYY-MM-DD'
    if start and end and start >= end:
        return None, None, 'Start date must be on or before end date'
    return start, end, None


def report_tickets(start, end):
    stmt = db.select(Ticket)
    if start is not None:
        stmt = stmt.where(Ticket.created_at >= start)
    if end is not None:
        stmt = stmt.where(Ticket.created_at < end)
    return db.session.execute(stmt.order_by(Ticket.created_at.desc())).scalars().all()


def report_rows(tickets):
    now = utc_now()
    result = []
    for t in tickets:
        response_breach = bool(t.response_due_at and
                               (t.first_response_at or now) > t.response_due_at)
        resolution_breach = bool(t.resolution_due_at and
                                 (t.resolved_at or now) > t.resolution_due_at)
        resolution_hours = round((t.resolved_at-t.created_at).total_seconds()/3600, 2) if t.resolved_at else None
        result.append({'Ticket ID':t.id,'Title':t.title,'Category':t.category,'Priority':t.priority,
                       'Status':t.status,'Employee':t.creator.name,'Engineer':t.assignee.name if t.assignee else '',
                       'Created UTC':as_iso(t.created_at),'Resolved UTC':as_iso(t.resolved_at) or '',
                       'Resolution hours':resolution_hours if resolution_hours is not None else '',
                       'Response breached':'Yes' if response_breach else 'No',
                       'Resolution breached':'Yes' if resolution_breach else 'No'})
    return result


@app.get('/api/reports/summary')
@auth('admin')
def reports_summary(user):
    start, end, error = report_filters()
    if error:
        return jsonify(error=error), 400
    items = report_tickets(start, end)
    rows = report_rows(items)
    status = Counter(t.status for t in items)
    categories = Counter(t.category for t in items)
    priorities = Counter(t.priority for t in items)
    months = Counter(t.created_at.strftime('%Y-%m') for t in items)
    engineers = db.session.execute(db.select(User).where(User.role == 'engineer').order_by(User.name)).scalars().all()
    closed_durations = [(t.resolved_at-t.created_at).total_seconds()/3600 for t in items if t.resolved_at]
    response_breaches = sum(r['Response breached']=='Yes' for r in rows)
    resolution_breaches = sum(r['Resolution breached']=='Yes' for r in rows)
    return jsonify(total=len(items),statuses=dict(status),categories=dict(categories),priorities=dict(priorities),
                   months=[{'month':m,'count':v} for m,v in sorted(months.items())],
                   response_breaches=response_breaches,resolution_breaches=resolution_breaches,
                   average_resolution_hours=round(sum(closed_durations)/len(closed_durations),2) if closed_durations else None,
                   resolved_count=len(closed_durations),
                   engineer_workload=[{'name':e.name,'active':sum(t.assignee_id==e.id and t.status not in ('Resolved','Closed') for t in items),
                                       'total':sum(t.assignee_id==e.id for t in items)} for e in engineers],
                   date_range={'start':request.args.get('start',''),'end':request.args.get('end','')})


@app.get('/api/reports/export')
@auth('admin')
def reports_export(user):
    start, end, error = report_filters()
    if error:
        return jsonify(error=error), 400
    format_ = request.args.get('format','csv').lower()
    if format_ not in ('csv','xlsx'):
        return jsonify(error='Format must be csv or xlsx'), 400
    rows = report_rows(report_tickets(start, end))
    headers = ['Ticket ID','Title','Category','Priority','Status','Employee','Engineer','Created UTC',
               'Resolved UTC','Resolution hours','Response breached','Resolution breached']
    if format_ == 'csv':
        buf = StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            # Prevent spreadsheet formula injection when importing CSV.
            writer.writerow({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v)
                             for k,v in r.items()})
        return Response('\ufeff'+buf.getvalue(),mimetype='text/csv',
                        headers={'Content-Disposition':'attachment; filename="helpdesk-report.csv"',
                                 'Cache-Control':'no-store'})
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title='Tickets'
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='245EE9')
    for r in rows:
        ws.append([r[k] for k in headers])
    ws.freeze_panes = 'A2';ws.auto_filter.ref=ws.dimensions
    for col in ws.columns:
        letter=col[0].column_letter
        ws.column_dimensions[letter].width=min(55,max(15,max(len(str(cell.value or '')) for cell in col)+2))
    buf=BytesIO();wb.save(buf);buf.seek(0)
    return send_file(buf,as_attachment=True,download_name='helpdesk-report.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


from phase8_admin import install as install_phase8
phase8_is_disabled = install_phase8(app, db, User, Ticket, auth, utc_now)

# Phase 7: secure attachments and staff-only audit notes.
from phase7_ticket_tools import install as install_phase7
install_phase7(app, db, Ticket, TicketEvent, User, auth, can_see, current_user, utc_now, as_iso, record)

# Phase 9: configurable, opt-in intelligent ticket routing.
from phase9_routing import install as install_phase9
phase9_suggest, phase9_route_new = install_phase9(app, db, Ticket, User, auth, utc_now, record, notify_ticket_participants, phase8_is_disabled)


if __name__ == '__main__':
    from apscheduler.schedulers.background import BackgroundScheduler
    # Flask debug reloader starts two processes; only the child runs the scanner.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler(daemon=True)
        def scheduled_scan():
            with app.app_context():
                sla_scan()
        scheduler.add_job(scheduled_scan, 'interval', seconds=60, id='sla-monitor', max_instances=1)
        scheduler.start()
    app.run(debug=True, port=5000)
