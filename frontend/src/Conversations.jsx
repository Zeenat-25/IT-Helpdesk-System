import React, { useEffect, useRef, useState } from 'react';
import { MessageSquare, Send, Search } from 'lucide-react';

export default function Conversations({ api, post, user, tickets, initialTicketId, onThreadChange }) {
  const [ticketId, setTicketId] = useState(initialTicketId || null);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [ticket, setTicket] = useState(null);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const bottom = useRef(null);
  const active = useRef(null);
  useEffect(() => { if (initialTicketId) setTicketId(initialTicketId); }, [initialTicketId]);
  useEffect(() => { active.current = ticketId; }, [ticketId]);
  useEffect(() => {
    if (!ticketId) { setMessages([]); setTicket(null); return; }
    let alive = true;
    const load = async () => {
      try {
        const data = await api('/tickets/' + ticketId);
        if (!alive || active.current !== ticketId) return;
        setTicket(data.ticket); setMessages(data.messages || []); setError('');
      } catch (e) { if (alive) setError(e.message); }
    };
    load();
    const interval = setInterval(() => { if (document.visibilityState === 'visible') load(); }, 4000);
    return () => { alive = false; clearInterval(interval); };
  }, [ticketId]);
  const lastId = messages.at(-1)?.id;
  useEffect(() => { bottom.current?.scrollIntoView({ behavior:'smooth', block:'end' }); }, [lastId, ticketId]);
  async function send(e) {
    e.preventDefault(); if (!ticketId || !draft.trim() || sending) return;
    setSending(true);
    try {
      await post('/tickets/' + ticketId + '/messages', { body: draft.trim() });
      setDraft('');
      const data = await api('/tickets/' + ticketId);
      setMessages(data.messages || []); setTicket(data.ticket);
      await onThreadChange?.();
    } catch(e) { setError(e.message); } finally { setSending(false); }
  }
  const visible = tickets.filter(t => (t.title+' '+t.id+' '+t.creator).toLowerCase().includes(query.toLowerCase()));
  return <div className="conversations-root">
    <div className="heading"><div><p className="eyebrow">SUPPORT MESSAGING</p><h1>Conversations</h1><p>Talk to your IT support team directly inside each ticket.</p></div></div>
    <div className="chat-layout">
      <aside className="chat-threads"><div className="chat-threads-header"><strong>Ticket conversations</strong><small>{tickets.length} accessible tickets</small><div className="chat-search"><Search size={16}/><input aria-label="Search conversations" placeholder="Search tickets..." value={query} onChange={e => setQuery(e.target.value)}/></div></div><div className="chat-thread-list">
      {visible.map(t=><button key={t.id} className={'chat-thread '+(ticketId===t.id?'selected':'')} onClick={()=>{setTicketId(t.id);setError('');}}><span className="chat-thread-icon"><MessageSquare size={18}/></span><span className="chat-thread-content"><strong>{t.title}</strong><small>#{String(t.id).padStart(4,'0')} · {user.role==='employee'?(t.assignee||'Awaiting assignment'):(t.creator||'Employee')}</small><em>{t.status}</em></span></button>)}
      {!visible.length && <p className="muted chat-no-threads">No matching tickets found.</p>}</div></aside>
      <section className="chat-panel">{ticketId && ticket ? <><div className="chat-header"><div><strong>{ticket.title}</strong><small>Ticket #{ticket.id} · {ticket.status} · {ticket.assignee||'Unassigned'}</small></div></div><div className="chat-messages">{!messages.length && <div className="chat-empty">No messages yet. Start a conversation about this ticket.</div>}{messages.map(m=><div className={'chat-bubble '+(m.user_id===user.id?'self':'')} key={m.id}><small>{m.author} · {new Date(m.created_at).toLocaleString()}</small><p>{m.body}</p></div>)}<div ref={bottom}/></div><form className="chat-compose" onSubmit={send}><textarea aria-label="Conversation message" rows={2} maxLength={2000} placeholder="Type a message to the support team..." value={draft} onChange={e=>setDraft(e.target.value)}/><button className="primary" disabled={sending||!draft.trim()}><Send size={16}/> Send</button></form></> : <div className="chat-empty large"><MessageSquare size={36}/><h2>Select a conversation</h2><p>Choose a ticket on the left to read messages or reply.</p></div>}{error && <p className="error chat-error">{error}</p>}</section>
    </div>
  </div>;
}
