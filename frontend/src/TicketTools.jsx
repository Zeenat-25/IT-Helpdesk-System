import React, { useEffect, useState } from 'react';

export default function TicketTools({ ticketId, role, onChanged }) {
  const [files, setFiles] = useState([]);
  const [notes, setNotes] = useState([]);
  const [file, setFile] = useState(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const staff = role === 'admin' || role === 'engineer';
  async function requestJson(path, options = {}) {
    const response = await fetch('/api' + path, { credentials: 'include', ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }
  async function load() {
    try {
      const a = await requestJson(`/tickets/${ticketId}/attachments`);
      setFiles(a.attachments || []);
      if (staff) {
        const n = await requestJson(`/tickets/${ticketId}/internal-notes`);
        setNotes(n.notes || []);
      } else setNotes([]);
    } catch (e) { setError(e.message); }
  }
  useEffect(() => { setError(''); setNotice(''); setFile(null); load(); }, [ticketId, role]);
  async function upload(event) {
    event.preventDefault(); if (!file) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const form = new FormData(); form.append('file', file);
      await requestJson(`/tickets/${ticketId}/attachments`, { method: 'POST', body: form });
      setFile(null); event.target.reset(); setNotice('Attachment uploaded.');
      await load(); onChanged?.();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function download(f) {
    setError('');
    try {
      const r = await fetch(`/api/tickets/${ticketId}/attachments/${f.id}/download`, { credentials:'include' });
      if (!r.ok) { const data = await r.json().catch(()=>({})); throw new Error(data.error || 'Download failed'); }
      const blob = await r.blob(); const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = f.name; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e.message); }
  }
  async function addNote(event) {
    event.preventDefault(); if (!note.trim()) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await requestJson(`/tickets/${ticketId}/internal-notes`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({body:note}) });
      setNote(''); setNotice('Internal note saved.'); await load(); onChanged?.();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <section className="phase7-tools" aria-label="Attachments and support notes">
    <h2>Attachments</h2><p className="muted">Add screenshots, logs or evidence. PNG, JPG, PDF or TXT up to 4 MB.</p>
    {error && <p className="phase7-error" role="alert">{error}</p>}
    {notice && <p className="phase7-success">{notice}</p>}
    <form className="phase7-upload" onSubmit={upload}>
      <input key={ticketId} aria-label="Choose attachment" type="file" accept=".png,.jpg,.jpeg,.pdf,.txt" onChange={e=>setFile(e.target.files?.[0] || null)}/>
      <button className="soft" disabled={busy || !file}>Upload file</button>
    </form>
    {files.length ? <div className="phase7-file-list">{files.map(f=><div key={f.id} className="phase7-file"><div><strong>{f.name}</strong><small>{(f.size/1024).toFixed(1)} KB · {f.uploaded_by} · {new Date(f.created_at).toLocaleString()}</small></div><button className="soft" type="button" onClick={()=>download(f)}>Download</button></div>)}</div> : <p className="muted">No attachments yet.</p>}
    {staff && <div className="phase7-notes"><h2>Internal support notes</h2><p className="muted">Visible to IT engineers and administrators only. Employees cannot access these notes.</p>
      <form onSubmit={addNote}><textarea aria-label="Internal note" rows={3} maxLength={2000} value={note} onChange={e=>setNote(e.target.value)} placeholder="Investigation details, diagnosis, or handover notes…"/><button className="soft" disabled={busy || note.trim().length < 3}>Save internal note</button></form>
      {notes.map(n=><div className="phase7-note" key={n.id}><strong>{n.author}</strong><small>{new Date(n.created_at).toLocaleString()}</small><p>{n.body}</p></div>)}
    </div>}
  </section>;
}
