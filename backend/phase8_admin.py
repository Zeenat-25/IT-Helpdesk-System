"""Phase 8: admin-only user, team and membership management.
Additive schema; existing user and ticket tables are not rebuilt.
"""
from flask import jsonify, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash


def install(app, db, User, Ticket, auth, utc_now):
    class SupportTeam(db.Model):
        __tablename__ = 'support_team'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), unique=True, nullable=False)
        description = db.Column(db.String(500), nullable=False, default='')

    class TeamMember(db.Model):
        __tablename__ = 'team_member'
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        team_id = db.Column(db.Integer, db.ForeignKey('support_team.id'), nullable=False)

    class UserDisabled(db.Model):
        __tablename__ = 'user_disabled'
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        disabled_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    with app.app_context():
        db.create_all()

    def disabled(uid):
        return db.session.get(UserDisabled, uid) is not None

    def admin_user(u):
        member = db.session.get(TeamMember, u.id)
        team = db.session.get(SupportTeam, member.team_id) if member else None
        return {**u.json(), 'active': not disabled(u.id), 'team_id': team.id if team else None,
                'team_name': team.name if team else None,
                'active_tickets': db.session.query(func.count(Ticket.id)).filter(
                    Ticket.assignee_id == u.id, Ticket.status.notin_(['Resolved','Closed'])).scalar() or 0}

    @app.get('/api/admin/users')
    @auth('admin')
    def p8_users(admin):
        users = db.session.execute(db.select(User).order_by(User.name)).scalars().all()
        return jsonify(users=[admin_user(u) for u in users])

    @app.post('/api/admin/users')
    @auth('admin')
    def p8_create_user(admin):
        d = request.get_json(silent=True) or {}
        name = str(d.get('name','')).strip(); email = str(d.get('email','')).strip().lower()
        password = str(d.get('password','')); role = str(d.get('role','employee'))
        if not name or len(name)>100 or '@' not in email or len(email)>200 or len(password)<8 or role not in ('admin','engineer','employee'):
            return jsonify(error='Enter a valid name, email, role and password (8+ characters)'),400
        if db.session.execute(db.select(User).where(User.email==email)).scalar_one_or_none():
            return jsonify(error='Email already exists'),409
        user=User(name=name,email=email,password_hash=generate_password_hash(password),role=role)
        db.session.add(user);db.session.commit()
        return jsonify(user=admin_user(user)),201

    @app.patch('/api/admin/users/<int:uid>')
    @auth('admin')
    def p8_update_user(admin,uid):
        u=db.get_or_404(User,uid); d=request.get_json(silent=True) or {}
        if 'name' in d:
            name=str(d['name']).strip()
            if not name or len(name)>100:return jsonify(error='Invalid name'),400
            u.name=name
        if 'role' in d:
            role=d['role']
            if role not in ('admin','engineer','employee'):return jsonify(error='Invalid role'),400
            if uid==admin.id and role!='admin':return jsonify(error='You cannot remove your own admin role'),400
            if u.role=='engineer' and role!='engineer' and db.session.query(Ticket.id).filter(Ticket.assignee_id==uid,Ticket.status.notin_(['Closed','Resolved'])).first():
                return jsonify(error='Reassign active tickets before changing this engineer role'),409
            u.role=role
            if role!='engineer':db.session.query(TeamMember).filter_by(user_id=uid).delete()
        if 'active' in d:
            if uid==admin.id and not d['active']:return jsonify(error='You cannot deactivate your own account'),400
            if d['active']:
                db.session.query(UserDisabled).filter_by(user_id=uid).delete()
            elif not disabled(uid):
                db.session.add(UserDisabled(user_id=uid))
        if 'password' in d and d['password']:
            if len(str(d['password']))<8:return jsonify(error='Password must have at least 8 characters'),400
            u.password_hash=generate_password_hash(str(d['password']))
        db.session.commit()
        return jsonify(user=admin_user(u))

    @app.get('/api/admin/teams')
    @auth('admin')
    def p8_teams(admin):
        teams=db.session.execute(db.select(SupportTeam).order_by(SupportTeam.name)).scalars().all()
        users=db.session.execute(db.select(User).where(User.role=='engineer')).scalars().all()
        return jsonify(teams=[{'id':t.id,'name':t.name,'description':t.description,
                               'members':[admin_user(u) for u in users if (m:=db.session.get(TeamMember,u.id)) and m.team_id==t.id],
                               'active_tickets':sum(db.session.query(func.count(Ticket.id)).filter(Ticket.assignee_id==u.id,Ticket.status.notin_(['Resolved','Closed'])).scalar() or 0 for u in users if (m:=db.session.get(TeamMember,u.id)) and m.team_id==t.id)} for t in teams])

    @app.post('/api/admin/teams')
    @auth('admin')
    def p8_create_team(admin):
        d=request.get_json(silent=True) or {};name=str(d.get('name','')).strip();desc=str(d.get('description','')).strip()
        if not name or len(name)>100 or len(desc)>500:return jsonify(error='Invalid team name/description'),400
        if db.session.execute(db.select(SupportTeam).where(func.lower(SupportTeam.name)==name.lower())).scalar_one_or_none():return jsonify(error='Team name already exists'),409
        t=SupportTeam(name=name,description=desc);db.session.add(t);db.session.commit()
        return jsonify(team={'id':t.id,'name':t.name,'description':t.description}),201

    @app.patch('/api/admin/teams/<int:tid>')
    @auth('admin')
    def p8_update_team(admin,tid):
        t=db.get_or_404(SupportTeam,tid);d=request.get_json(silent=True) or {}
        name=str(d.get('name',t.name)).strip();description=str(d.get('description',t.description)).strip()
        if not name or len(name)>100 or len(description)>500:return jsonify(error='Invalid team'),400
        exists=db.session.execute(db.select(SupportTeam).where(func.lower(SupportTeam.name)==name.lower(), SupportTeam.id!=tid)).scalar_one_or_none()
        if exists:return jsonify(error='Team name already exists'),409
        t.name=name;t.description=description;db.session.commit();return jsonify(ok=True)

    @app.delete('/api/admin/teams/<int:tid>')
    @auth('admin')
    def p8_delete_team(admin,tid):
        t=db.get_or_404(SupportTeam,tid)
        if db.session.query(TeamMember).filter_by(team_id=tid).first():return jsonify(error='Remove team members before deleting'),409
        db.session.delete(t);db.session.commit();return jsonify(ok=True)

    @app.patch('/api/admin/users/<int:uid>/team')
    @auth('admin')
    def p8_team_membership(admin,uid):
        u=db.get_or_404(User,uid);d=request.get_json(silent=True) or {};tid=d.get('team_id')
        if u.role!='engineer':return jsonify(error='Only engineers can join support teams'),400
        if disabled(uid):return jsonify(error='Activate this engineer first'),400
        if tid is not None and (not isinstance(tid,int) or not db.session.get(SupportTeam,tid)):
            return jsonify(error='Invalid team'),400
        member=db.session.get(TeamMember,uid)
        if tid is None:
            if member:db.session.delete(member)
        elif member:member.team_id=tid
        else:db.session.add(TeamMember(user_id=uid,team_id=tid))
        db.session.commit();return jsonify(user=admin_user(u))

    return disabled
