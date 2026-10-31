"""Phase 3 SLA policy, monitoring, escalation and in-app notifications.

Calendar-time deadlines, UTC-naive timestamps matching the Phase 2 database.
Run automatic scans with the Flask development server (once per minute).
For production, run `flask --app app sla-scan` using an external scheduler.
"""
import os
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from flask import jsonify, request
from sqlalchemy import UniqueConstraint


def install(app, db, User, Ticket, TicketEvent, auth, utc_now, as_iso):
    class SLAPolicy(db.Model):
        __tablename__ = 'sla_policy'
        id = db.Column(db.Integer, primary_key=True)
        priority = db.Column(db.String(20), nullable=False, unique=True)
        response_minutes = db.Column(db.Integer, nullable=False)
        resolution_minutes = db.Column(db.Integer, nullable=False)

        def json(self):
            return {'priority': self.priority, 'response_minutes': self.response_minutes,
                    'resolution_minutes': self.resolution_minutes}

    class SLAAlert(db.Model):
        __tablename__ = 'sla_alert'
        __table_args__ = (UniqueConstraint('ticket_id', 'kind', name='uq_sla_alert_ticket_kind'),)
        id = db.Column(db.Integer, primary_key=True)
        ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
        kind = db.Column(db.String(30), nullable=False)
        created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    class Notification(db.Model):
        __tablename__ = 'notification'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
        body = db.Column(db.String(300), nullable=False)
        read_at = db.Column(db.DateTime)
        created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

        def json(self):
            return {'id': self.id, 'ticket_id': self.ticket_id, 'body': self.body,
                    'read': self.read_at is not None, 'created_at': as_iso(self.created_at)}

    defaults = {'Critical': (15, 240), 'High': (30, 480),
                'Medium': (120, 1440), 'Low': (240, 4320)}
    with app.app_context():
        db.create_all()
        for priority, (response, resolution) in defaults.items():
            if db.session.execute(db.select(SLAPolicy).filter_by(priority=priority)).scalar_one_or_none() is None:
                db.session.add(SLAPolicy(priority=priority, response_minutes=response,
                                         resolution_minutes=resolution))
        db.session.commit()

    def policy_for(priority):
        policy = db.session.execute(db.select(SLAPolicy).filter_by(priority=priority)).scalar_one()
        return policy.response_minutes, policy.resolution_minutes

    def send_email(to_address, subject, body):
        host = os.getenv('SMTP_HOST')
        sender = os.getenv('SMTP_FROM')
        if not host or not sender:
            return
        message = EmailMessage()
        message['From'], message['To'], message['Subject'] = sender, to_address, subject
        message.set_content(body)
        try:
            with smtplib.SMTP(host, int(os.getenv('SMTP_PORT', '587')), timeout=8) as smtp:
                if os.getenv('SMTP_TLS', 'true').lower() == 'true':
                    smtp.starttls()
                if os.getenv('SMTP_USER'):
                    smtp.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD', ''))
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            app.logger.warning('SLA email could not be sent: %s', exc)

    def scan():
        """Exactly one alert per ticket per SLA type, even after repeated scans."""
        now = utc_now()
        admins = db.session.execute(db.select(User).where(User.role == 'admin')).scalars().all()
        sent = []
        for ticket in db.session.execute(db.select(Ticket)).scalars():
            for kind, due, completed in (
                ('response', ticket.response_due_at, ticket.first_response_at),
                ('resolution', ticket.resolution_due_at, ticket.resolved_at),
            ):
                # A late completed response/resolution still counts as breached.
                if due is None or (completed or now) <= due:
                    continue
                exists = db.session.execute(db.select(SLAAlert).filter_by(ticket_id=ticket.id, kind=kind)).scalar_one_or_none()
                if exists:
                    continue
                db.session.add(SLAAlert(ticket_id=ticket.id, kind=kind))
                detail = f'{kind.capitalize()} SLA breached for ticket #{ticket.id}'
                db.session.add(TicketEvent(ticket_id=ticket.id, actor_id=ticket.creator_id,
                                           kind='sla_breach', detail=detail))
                for admin in admins:
                    db.session.add(Notification(user_id=admin.id, ticket_id=ticket.id, body=detail))
                sent.append((detail, [admin.email for admin in admins]))
        db.session.commit()
        for detail, emails in sent:
            for email in emails:
                send_email(email, 'IT Helpdesk: SLA breach', detail)
        return len(sent)

    @app.get('/api/sla/policies')
    @auth('admin')
    def get_sla_policies(user):
        policies = db.session.execute(db.select(SLAPolicy)).scalars().all()
        order = list(defaults)
        return jsonify(policies=[p.json() for p in sorted(policies, key=lambda p: order.index(p.priority))])

    @app.put('/api/sla/policies/<priority>')
    @auth('admin')
    def update_sla_policy(user, priority):
        policy = db.session.execute(db.select(SLAPolicy).filter_by(priority=priority)).scalar_one_or_none()
        if policy is None:
            return jsonify(error='Unknown priority'), 404
        data = request.get_json(silent=True) or {}
        response, resolution = data.get('response_minutes'), data.get('resolution_minutes')
        if any(type(v) is not int or v < 1 or v > 525600 for v in (response, resolution)) or response > resolution:
            return jsonify(error='Enter positive whole minutes; resolution must be >= response'), 400
        policy.response_minutes, policy.resolution_minutes = response, resolution
        db.session.commit()
        return jsonify(policy=policy.json(), note='Applies to newly created tickets only')

    @app.get('/api/notifications')
    @auth()
    def get_notifications(user):
        notes = db.session.execute(db.select(Notification).where(Notification.user_id == user.id)
                                   .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(50)).scalars()
        return jsonify(notifications=[n.json() for n in notes])

    @app.patch('/api/notifications/<int:notification_id>/read')
    @auth()
    def read_notification(user, notification_id):
        note = db.session.get(Notification, notification_id)
        if not note or note.user_id != user.id:
            return jsonify(error='Notification not found'), 404
        note.read_at = note.read_at or utc_now()
        db.session.commit()
        return jsonify(ok=True)

    @app.post('/api/sla/scan')
    @auth('admin')
    def manual_sla_scan(user):
        return jsonify(new_breaches=scan())

    @app.cli.command('sla-scan')
    def cli_scan():
        print('New SLA breaches:', scan())

    return policy_for, scan
