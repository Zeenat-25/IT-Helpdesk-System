"""Phase 7 add-on: restricted ticket attachments and internal support notes."""
from pathlib import Path
from uuid import uuid4
from flask import jsonify, request, send_file, current_app
from werkzeug.utils import secure_filename

LIMIT = 4 * 1024 * 1024
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.txt'}
MIMES = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.pdf':'application/pdf','.txt':'text/plain'}


def is_allowed(name, content):
    ext = Path(name).suffix.lower()
    if ext not in EXTENSIONS or not content or len(content) > LIMIT:
        return False
    if ext == '.png': return content.startswith(b'\x89PNG\r\n\x1a\n')
    if ext in ('.jpg', '.jpeg'): return content.startswith(b'\xff\xd8\xff')
    if ext == '.pdf': return content.startswith(b'%PDF-')
    return b'\x00' not in content


def install(app, db, Ticket, TicketEvent, User, auth, can_see, current_user, utc_now, as_iso, record):
    class TicketAttachment(db.Model):
        __tablename__ = 'ticket_attachment'
        id = db.Column(db.Integer, primary_key=True)
        ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
        uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        original_name = db.Column(db.String(180), nullable=False)
        stored_name = db.Column(db.String(100), unique=True, nullable=False)
        size = db.Column(db.Integer, nullable=False)
        mime_type = db.Column(db.String(60), nullable=False)
        created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
        uploader = db.relationship(User)
        def json(self):
            return {'id':self.id,'ticket_id':self.ticket_id,'name':self.original_name,'size':self.size,
                    'uploaded_by':self.uploader.name,'created_at':as_iso(self.created_at)}

    class InternalNote(db.Model):
        __tablename__ = 'ticket_internal_note'
        id = db.Column(db.Integer, primary_key=True)
        ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
        author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        body = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
        author = db.relationship(User)
        def json(self):
            return {'id':self.id,'body':self.body,'author':self.author.name,'created_at':as_iso(self.created_at)}

    with app.app_context():
        db.create_all()

    folder = Path(app.root_path) / 'instance_uploads'
    folder.mkdir(exist_ok=True)

    def get_permitted(user, ticket_id):
        ticket = db.session.get(Ticket, ticket_id)
        if ticket is None: return None, (jsonify(error='Ticket not found'), 404)
        if not can_see(user, ticket): return None, (jsonify(error='Permission denied'), 403)
        return ticket, None

    @app.get('/api/tickets/<int:ticket_id>/attachments')
    @auth()
    def attachment_list(user, ticket_id):
        ticket, err = get_permitted(user, ticket_id)
        if err: return err
        stmt = db.select(TicketAttachment).where(TicketAttachment.ticket_id == ticket.id).order_by(TicketAttachment.id.desc())
        return jsonify(attachments=[a.json() for a in db.session.execute(stmt).scalars()])

    @app.post('/api/tickets/<int:ticket_id>/attachments')
    @auth()
    def attachment_upload(user, ticket_id):
        ticket, err = get_permitted(user, ticket_id)
        if err: return err
        if ticket.status == 'Closed': return jsonify(error='Closed tickets do not accept attachments'), 400
        item = request.files.get('file')
        if item is None: return jsonify(error='Choose a file'), 400
        filename = secure_filename(item.filename or '')
        if not filename or len(filename) > 180: return jsonify(error='Invalid filename'), 400
        content = item.read(LIMIT + 1)
        if not is_allowed(filename, content):
            return jsonify(error='Allowed: PNG, JPG, PDF, TXT up to 4 MB'), 400
        extension = Path(filename).suffix.lower()
        saved_name = uuid4().hex + extension
        target = folder / saved_name
        target.write_bytes(content)
        try:
            row = TicketAttachment(ticket_id=ticket.id, uploaded_by=user.id, original_name=filename,
                                   stored_name=saved_name,size=len(content),mime_type=MIMES[extension])
            db.session.add(row)
            record(ticket, user, 'attachment', f'Uploaded attachment: {filename}')
            ticket.updated_at = utc_now()
            db.session.commit()
        except Exception:
            db.session.rollback()
            target.unlink(missing_ok=True)
            raise
        return jsonify(attachment=row.json()), 201

    @app.get('/api/tickets/<int:ticket_id>/attachments/<int:attachment_id>/download')
    @auth()
    def attachment_download(user, ticket_id, attachment_id):
        ticket, err = get_permitted(user, ticket_id)
        if err: return err
        row = db.session.get(TicketAttachment, attachment_id)
        if not row or row.ticket_id != ticket.id: return jsonify(error='Attachment not found'), 404
        path = folder / row.stored_name
        if not path.is_file(): return jsonify(error='File missing from server'), 404
        result = send_file(path, as_attachment=True, download_name=row.original_name,
                           mimetype='application/octet-stream')
        result.headers['Cache-Control'] = 'private, no-store'
        result.headers['X-Content-Type-Options'] = 'nosniff'
        return result

    @app.get('/api/tickets/<int:ticket_id>/internal-notes')
    @auth('admin','engineer')
    def notes_list(user,ticket_id):
        ticket, err = get_permitted(user,ticket_id)
        if err: return err
        stmt = db.select(InternalNote).where(InternalNote.ticket_id == ticket.id).order_by(InternalNote.id.desc())
        return jsonify(notes=[n.json() for n in db.session.execute(stmt).scalars()])

    @app.post('/api/tickets/<int:ticket_id>/internal-notes')
    @auth('admin','engineer')
    def notes_create(user,ticket_id):
        ticket, err = get_permitted(user,ticket_id)
        if err: return err
        if user.role == 'engineer' and ticket.assignee_id not in (None,user.id):
            return jsonify(error='Assigned to another engineer'), 403
        data = request.get_json(silent=True) or {}
        body = str(data.get('body','')).strip()
        if not (3 <= len(body) <= 2000): return jsonify(error='Note length must be 3–2000 characters'), 400
        note = InternalNote(ticket_id=ticket.id, author_id=user.id, body=body)
        db.session.add(note)
        record(ticket,user,'internal_note','Added internal support note (staff only)')
        ticket.updated_at = utc_now()
        db.session.commit()
        return jsonify(note=note.json()), 201
