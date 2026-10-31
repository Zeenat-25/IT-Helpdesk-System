"""Phase 9 smart routing. Rules are editable by admins and stored in SQLite."""
import re
from flask import jsonify, request
from sqlalchemy import func

CATEGORIES = ('Network','Hardware','Software','Access','Other')
PRIORITIES = ('Low','Medium','High','Critical')
DEFAULT_RULES = {
 'Network': 'Network Support', 'Hardware': 'Desktop Support',
 'Software': 'Application Support', 'Access': 'Access Support', 'Other': ''
}
WORDS = {
 'Network': ('wifi','wi-fi','vpn','internet','network','router','dns','connectivity','ethernet'),
 'Hardware': ('laptop','printer','keyboard','screen','monitor','mouse','battery','disk','hardware'),
 'Software': ('outlook','excel','software','application','crash','install','update','browser'),
 'Access': ('password','login','log in','account locked','mfa','permission','access denied','sign in'),
}
HIGH = ('cannot work','unable to work','preventing me from working','urgent','department affected','many employees','multiple employees','business operations')
CRITICAL = ('entire office','company wide','company-wide','all employees','complete outage','entire network','production down')

def install(app, db, Ticket, User, auth, utc_now, record, notify, disabled):
    class RoutingRule(db.Model):
        __tablename__ = 'routing_rule'
        category = db.Column(db.String(40), primary_key=True)
        team_id = db.Column(db.Integer, db.ForeignKey('support_team.id'), nullable=True)

    class RoutingSetting(db.Model):
        __tablename__ = 'routing_setting'
        key = db.Column(db.String(80), primary_key=True)
        value = db.Column(db.String(20), nullable=False)

    # Phase 8 must already have created team tables.
    from phase8_admin import install as _phase8_install  # import only, for deployment validation
    with app.app_context():
        db.create_all()
        if not db.session.get(RoutingSetting,'auto_assign'):
            db.session.add(RoutingSetting(key='auto_assign',value='false'))
        for category in CATEGORIES:
            if not db.session.get(RoutingRule,category):
                db.session.add(RoutingRule(category=category))
        db.session.commit()

    def suggest(text):
        t=' '.join(text.lower().split())
        scores={c:sum(1 for w in keywords if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',t)) for c,keywords in WORDS.items()}
        category=max(scores,key=lambda c:scores[c]) if max(scores.values(),default=0)>0 else 'Other'
        if any(p in t for p in CRITICAL):priority='Critical'
        elif any(p in t for p in HIGH):priority='High'
        elif any(p in t for p in ('minor','cosmetic','when convenient','not urgent')):priority='Low'
        else:priority='Medium'
        return category,priority

    def recommend(category):
        rule=db.session.get(RoutingRule,category)
        tid=rule.team_id if rule else None
        team=db.session.execute(db.text('SELECT id,name FROM support_team WHERE id=:id'),{'id':tid}).mappings().first() if tid else None
        if not team:return {'team_id':None,'team_name':None,'engineer_id':None,'engineer_name':None,'active_tickets':None}
        members=db.session.execute(db.text('SELECT user_id FROM team_member WHERE team_id=:tid'),{'tid':tid}).scalars().all()
        engineers=[u for uid in members if (u:=db.session.get(User,uid)) and u.role=='engineer' and not disabled(u.id)]
        if not engineers:return {'team_id':tid,'team_name':team['name'],'engineer_id':None,'engineer_name':None,'active_tickets':None}
        counts={u.id:db.session.query(func.count(Ticket.id)).filter(Ticket.assignee_id==u.id,Ticket.status.notin_(['Resolved','Closed'])).scalar() or 0 for u in engineers}
        chosen=min(engineers,key=lambda u:(counts[u.id],u.id))
        return {'team_id':tid,'team_name':team['name'],'engineer_id':chosen.id,'engineer_name':chosen.name,'active_tickets':counts[chosen.id]}

    def auto_on():
        setting=db.session.get(RoutingSetting,'auto_assign')
        return bool(setting and setting.value=='true')

    def route_new(ticket, actor):
        if not auto_on():return
        rec=recommend(ticket.category)
        if not rec['engineer_id']:return
        ticket.assignee_id=rec['engineer_id']
        ticket.status='Assigned'
        record(ticket,actor,'auto_assignment',f"Auto-assigned to {rec['engineer_name']} ({rec['team_name']})")
        notify(ticket,actor,f"Automatically assigned ticket #{ticket.id}: {ticket.title}",extra_user_ids=(ticket.assignee_id,))

    @app.post('/api/routing/suggest')
    @auth()
    def routing_suggest(user):
        d=request.get_json(silent=True) or {}
        title=str(d.get('title',''))[:180];description=str(d.get('description',''))[:5000]
        if not (title or description):return jsonify(error='Enter a title or description'),400
        category,priority=suggest(title+' '+description)
        selection=d.get('category')
        chosen=selection if selection in CATEGORIES else category
        return jsonify(category=category,priority=priority,recommendation=recommend(chosen),routing_category=chosen,
                       note='Suggestions are rule-based; assess business impact before raising priority.')

    @app.get('/api/admin/routing')
    @auth('admin')
    def routing_get(user):
        teams=db.session.execute(db.text('SELECT id,name FROM support_team ORDER BY name')).mappings().all()
        return jsonify(auto_assign=auto_on(),teams=[dict(t) for t in teams],rules=[{
            'category':c,'team_id':db.session.get(RoutingRule,c).team_id,
            'recommendation':recommend(c)} for c in CATEGORIES])

    @app.put('/api/admin/routing')
    @auth('admin')
    def routing_update(user):
        d=request.get_json(silent=True) or {}
        if 'auto_assign' in d:
            if not isinstance(d['auto_assign'],bool):return jsonify(error='auto_assign must be true/false'),400
            db.session.get(RoutingSetting,'auto_assign').value='true' if d['auto_assign'] else 'false'
        if 'rules' in d:
            if not isinstance(d['rules'],list):return jsonify(error='rules must be an array'),400
            for item in d['rules']:
                if not isinstance(item,dict) or item.get('category') not in CATEGORIES:return jsonify(error='Invalid category'),400
                tid=item.get('team_id')
                if tid is not None and (type(tid) is not int or not db.session.execute(db.text('SELECT id FROM support_team WHERE id=:id'),{'id':tid}).first()):
                    return jsonify(error='Invalid team ID'),400
                db.session.get(RoutingRule,item['category']).team_id=tid
        db.session.commit()
        return routing_get.__wrapped__(user) if hasattr(routing_get,'__wrapped__') else jsonify(ok=True)

    @app.post('/api/admin/tickets/<int:ticket_id>/auto-assign')
    @auth('admin')
    def assign_one(user,ticket_id):
        ticket=db.get_or_404(Ticket,ticket_id)
        if ticket.status in ('Resolved','Closed'):return jsonify(error='Cannot reassign resolved/closed tickets'),409
        if ticket.assignee_id:return jsonify(error='Ticket is already assigned. Use manual assignment to change engineer.'),409
        rec=recommend(ticket.category)
        if not rec['engineer_id']:return jsonify(error='No active engineer in configured support team'),409
        ticket.assignee_id=rec['engineer_id']
        if ticket.status=='Open':ticket.status='Assigned'
        ticket.updated_at=utc_now()
        record(ticket,user,'auto_assignment',f"Admin applied smart assignment to {rec['engineer_name']}")
        notify(ticket,user,f"New assignment: Ticket #{ticket.id} — {ticket.title}",extra_user_ids=(ticket.assignee_id,))
        db.session.commit()
        return jsonify(ticket=ticket.json(),recommendation=rec)

    return suggest,route_new
