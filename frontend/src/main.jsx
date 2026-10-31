import RoutingSettings from './RoutingSettings.jsx';
import AdminManagement from './AdminManagement.jsx';
import TicketTools from './TicketTools.jsx';
import Conversations from './Conversations.jsx';
import Analytics from './Analytics.jsx';
import KnowledgeBase from './KnowledgeBase.jsx';
import SlaCenter from './SlaCenter.jsx';
import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, BarChart3, ArrowLeft, BookOpen, Bell, CheckCircle2, CircleHelp, ClipboardList, LayoutDashboard, LogOut, MessageSquare, Plus, Shield, Ticket, Users, Wrench } from 'lucide-react';
import './style.css';

async function api(path, options = {}) {
  const response = await fetch('/api' + path, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options });
  const type = response.headers.get('content-type') || '';
  if (!type.includes('application/json')) throw new Error(`API returned ${response.status} instead of JSON. Verify Flask routes and Vite proxy.`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
const post = (path, body, method = 'POST') => api(path, { method, body: JSON.stringify(body) });
const badge = s => <span className={'badge badge-' + s.toLowerCase().replace(/\s+/g, '-')}>{s}</span>;

function App() {
  const [user, setUser] = useState(null), [loading, setLoading] = useState(true);
  const [tickets, setTickets] = useState([]), [engineers, setEngineers] = useState([]);
  const [screen, setScreen] = useState('dashboard'), [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]), [events, setEvents] = useState([]), [reply, setReply] = useState('');
  const [filters, setFilters] = useState({search:'',status:'',priority:'',category:'',assignee:''});
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [authMode, setAuthMode] = useState('login'), [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [form, setForm] = useState({ title: '', description: '', category: '', priority: 'Medium' });
  const [stats, setStats] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [messageToasts, setMessageToasts] = useState([]);
  const knownNotificationIds = useRef(null);
  const toastTimers = useRef(new Map());
  const [suggestions, setSuggestions] = useState([]);
  const [articleToOpen, setArticleToOpen] = useState(null);
  const [chatTicketId, setChatTicketId] = useState(null);
  const [routingPreview,setRoutingPreview] = useState(null);

  async function refreshNotifications(current = user) {
    if (!current) return;
    try {
      const result = await api('/notifications');
      const incoming = result.notifications || [];
      // Initial fetch establishes a baseline. No popup flood from old alerts on login.
      if (knownNotificationIds.current === null) {
        knownNotificationIds.current = new Set(incoming.map(n => n.id));
      } else {
        const fresh = incoming.filter(n => !knownNotificationIds.current.has(n.id) && !n.read && n.body?.startsWith('New message from '));
        for (const n of incoming) knownNotificationIds.current.add(n.id);
        if (fresh.length) setMessageToasts(old => [...fresh.slice(0, 3).reverse(), ...old].slice(0, 4));
      }
      setNotifications(incoming);
    } catch (_) { /* Network error should not log the user out */ }
  }
  useEffect(() => { knownNotificationIds.current = null; setMessageToasts([]); toastTimers.current.forEach(clearTimeout); toastTimers.current.clear(); if (!user) return; refreshNotifications(user); const id = setInterval(() => refreshNotifications(user), 3000); return () => clearInterval(id); }, [user?.id]);
  useEffect(() => { if (!user) return; const id = setInterval(() => { if (document.visibilityState === 'visible') refresh(user).catch(() => {}); }, 6000); return () => clearInterval(id); }, [user?.id]);
  function dismissToast(id) {
    setMessageToasts(old => old.filter(n => n.id !== id));
    clearTimeout(toastTimers.current.get(id)); toastTimers.current.delete(id);
  }
  useEffect(() => {
    for (const n of messageToasts) {
      if (!toastTimers.current.has(n.id)) {
        toastTimers.current.set(n.id, setTimeout(() => dismissToast(n.id), 8500));
      }
    }
  }, [messageToasts]);
  async function openToast(n) {
    dismissToast(n.id);
    setChatTicketId(n.ticket_id);
    setScreen('conversations');
    try { await post('/notifications/' + n.id + '/read', {}, 'PATCH'); await refreshNotifications(); }
    catch (e) { setError(e.message); }
  }
  async function markRead(n) {
    try { await post('/notifications/' + n.id + '/read', {}, 'PATCH'); await refreshNotifications(); } catch(e) { setError(e.message); }
  }
  async function refresh(current = user) {
    if (!current) return;
    const result = await api('/tickets'); setTickets(result.tickets);
    if (current.role !== 'employee') {
      const [e, s] = await Promise.all([api('/users/engineers'), api('/stats')]);
      setEngineers(e.users); setStats(s);
    }
  }
  useEffect(() => { api('/auth/me').then(async ({ user }) => { setUser(user); await refresh(user); }).catch(() => {}).finally(() => setLoading(false)); }, []);
  async function signIn(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { user } = await post(authMode === 'login' ? '/auth/login' : '/auth/register', authForm);
      setUser(user); setScreen('dashboard'); await refresh(user);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function logout() { await post('/auth/logout', {}); knownNotificationIds.current = null; setMessageToasts([]); setUser(null); setSelected(null); setError(''); }
  async function previewRouting() { try { setRoutingPreview(await post('/routing/suggest', form)); } catch(e) { setError(e.message); } }
  async function create(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { await post('/tickets', form); setForm({ title: '', description: '', category: '', priority: 'Medium' }); await refresh(); setScreen('tickets'); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function openTicket(t) {
    setError(''); try { const data = await api('/tickets/' + t.id); setSelected(data.ticket); setMessages(data.messages); setEvents(data.events || []); setSuggestions([]); setArticleToOpen(null); setScreen('detail'); try { const r = await api('/tickets/' + t.id + '/suggestions'); setSuggestions(r.suggestions || []); } catch (_) {} } catch (e) { setError(e.message); }
  }
  async function update(fields) {
    setBusy(true); setError('');
    try { const { ticket } = await post('/tickets/' + selected.id, fields, 'PATCH'); setSelected(ticket); await refresh(); await refreshNotifications(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function send(e) {
    e.preventDefault(); if (!reply.trim()) return;
    setBusy(true); setError('');
    try { await post('/tickets/' + selected.id + '/messages', { body: reply }); setReply(''); await openTicket(selected); await refresh(); await refreshNotifications(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  if (loading) return <div className="loading">Loading Deskflow…</div>;
  if (!user) return <div className="auth-page"><div className="auth-card"><div className="brand large"><span className="brand-icon"><Wrench size={20}/></span> Deskflow</div><h1>{authMode === 'login' ? 'Welcome back' : 'Create an account'}</h1><p>Manage IT service requests in one place.</p><form onSubmit={signIn}>{authMode === 'register' && <label>Full name<input value={authForm.name} required onChange={e => setAuthForm({ ...authForm, name: e.target.value })} placeholder="Your full name"/></label>}<label>Email address<input type="email" value={authForm.email} required onChange={e => setAuthForm({ ...authForm, email: e.target.value })} placeholder="you@company.com"/></label><label>Password<input type="password" minLength={8} required value={authForm.password} onChange={e => setAuthForm({ ...authForm, password: e.target.value })} placeholder="Minimum 8 characters"/></label>{error && <p className="error">{error}</p>}<button className="primary full" disabled={busy}>{busy ? 'Working…' : authMode === 'login' ? 'Sign in' : 'Create account'}</button></form><p className="foot">{authMode === 'login' ? 'New employee?' : 'Already registered?'} <button className="link" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(''); }}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></p><div className="demo-hint">Demo accounts: admin@demo.local, engineer@demo.local, employee@demo.local<br/>Password: Demo12345!</div></div></div>;

  const filteredTickets = tickets.filter(t =>
    (!filters.search || (t.title + ' ' + t.description + ' ' + t.id).toLowerCase().includes(filters.search.toLowerCase())) &&
    (!filters.status || t.status === filters.status) &&
    (!filters.priority || t.priority === filters.priority) &&
    (!filters.category || t.category === filters.category) &&
    (!filters.assignee || (filters.assignee === 'unassigned' ? !t.assignee_id : t.assignee_id === user.id))
  );
  const roleName = user.role === 'admin' ? 'Administrator' : user.role === 'engineer' ? 'IT Engineer' : 'Employee';
  const counts = stats || { total: tickets.length, open: tickets.filter(t => t.status === 'Open').length, in_progress: tickets.filter(t => ['Assigned','In Progress'].includes(t.status)).length, resolved: tickets.filter(t => ['Resolved','Closed'].includes(t.status)).length };
  return <div className="shell"><aside className="sidebar"><div className="sidebar-header"><div className="brand"><span className="brand-icon"><Wrench size={18}/></span> Deskflow</div></div><nav className="sidebar-links" aria-label="Workspace navigation"><div className="side-label">WORKSPACE</div><button className={'nav ' + (screen === 'dashboard' ? 'active' : '')} onClick={() => { setScreen('dashboard'); setError(''); }}><LayoutDashboard size={18}/> Overview</button><button className={'nav ' + (screen === 'tickets' || screen === 'detail' ? 'active' : '')} onClick={() => { setScreen('tickets'); setError(''); }}><Ticket size={18}/> Tickets</button>{user.role === 'employee' && <button className={'nav ' + (screen === 'new' ? 'active' : '')} onClick={() => { setScreen('new'); setError(''); }}><Plus size={18}/> New Ticket</button>}{user.role === 'admin' && <button className={'nav ' + (screen === 'sla' ? 'active' : '')} onClick={() => { setScreen('sla'); setError(''); }}><Activity size={18}/> SLA Policies</button>}{user.role === 'admin' && <button className={'nav ' + (screen === 'analytics' ? 'active' : '')} onClick={() => { setScreen('analytics'); setError(''); }}><BarChart3 size={18}/> Analytics & Reports</button>}{user.role === 'admin' && <button className={'nav ' + (screen === 'routing' ? 'active' : '')} onClick={() => {setScreen('routing');setError('');}}><Activity size={18}/> Smart Routing</button>}{user.role === 'admin' && <button className={'nav ' + (screen === 'management' ? 'active' : '')} onClick={() => {setScreen('management');setError('');}}><Users size={18}/> Users & Teams</button>}<button className={'nav ' + (screen === 'conversations' ? 'active' : '')} onClick={() => { setScreen('conversations'); setError(''); }}><MessageSquare size={18}/> Conversations</button><button className={'nav ' + (screen === 'knowledge' ? 'active' : '')} onClick={() => { setScreen('knowledge'); setArticleToOpen(null); setError(''); }}><BookOpen size={18}/> Knowledge Base</button><button className={'nav ' + (screen === 'notifications' ? 'active' : '')} onClick={() => { setScreen('notifications'); setError(''); refreshNotifications(); }}><Bell size={18}/> Alerts {notifications.filter(n => !n.read).length > 0 && <span className="alert-count">{notifications.filter(n => !n.read).length}</span>}</button></nav><div className="sidebar-footer"><div className="user-box"><div className="avatar">{user.name.slice(0, 1).toUpperCase()}</div><div><strong>{user.name}</strong><small>{roleName}</small></div></div><button className="nav signout" onClick={logout}><LogOut size={17}/> Sign out</button></div></aside>
  <div className="phase10-toast-stack" role="region" aria-label="New message previews" aria-live="polite">
    {messageToasts.map(n => <div className="phase10-toast" key={n.id}>
      <span className="phase10-toast-icon"><MessageSquare size={19}/></span>
      <div className="phase10-toast-body"><strong>New ticket message</strong><p>{n.body}</p><button className="phase10-toast-open" onClick={() => openToast(n)}>Open conversation</button></div>
      <button className="phase10-toast-close" onClick={() => dismissToast(n.id)} aria-label="Dismiss notification">×</button>
    </div>)}
  </div>
  <main className="main"><header className="topbar"><span>IT Helpdesk <span className="crumb">/ {screen === 'detail' ? 'Ticket details' : screen === 'new' ? 'New ticket' : screen === 'dashboard' ? 'Overview' : screen === 'routing' ? 'Smart Routing' : screen === 'management' ? 'Users & Teams' : screen === 'analytics' ? 'Analytics & Reports' : screen === 'knowledge' ? 'Knowledge Base' : screen === 'sla' ? 'SLA Policies' : screen === 'conversations' ? 'Conversations' : screen === 'notifications' ? 'Alerts' : 'Tickets'}</span></span><span className="top-role"><Shield size={15}/> {roleName}</span></header><div className="content">{error && <div className="error alert">{error}</div>}
  {screen === 'conversations' && <Conversations api={api} post={post} user={user} tickets={tickets} initialTicketId={chatTicketId} onThreadChange={async () => { await refresh(); await refreshNotifications(); }} />}
  {screen === 'routing' && user.role === 'admin' && <RoutingSettings api={api} post={post}/>}
  {screen === 'management' && user.role === 'admin' && <AdminManagement api={api} post={post} onChanged={refresh} />}
  {screen === 'analytics' && user.role === 'admin' && <Analytics api={api} />}
  {screen === 'knowledge' && <KnowledgeBase api={api} post={post} user={user} initialArticleId={articleToOpen} />}
  {screen === 'sla' && user.role === 'admin' && <SlaCenter api={api} post={post} onScan={async () => { await refresh(); await refreshNotifications(); }}/>}
  {screen === 'notifications' && <><div className="heading"><div><p className="eyebrow">NOTIFICATIONS</p><h1>Alerts</h1><p>Updates about your requests, assignments, replies, and SLA deadlines.</p></div></div><div className="panel notification-list">{notifications.map(n => <div key={n.id} className={'notification-row ' + (n.read ? '' : 'unread')}><div><strong>{n.read ? 'Update' : 'New update'} · {n.body}</strong><small>{new Date(n.created_at).toLocaleString()} · Ticket #{n.ticket_id}</small></div><div className="notification-actions"><button className="soft" onClick={() => openTicket({ id: n.ticket_id })}>{'Open ticket'}</button>{!n.read && <button className="soft" onClick={() => markRead(n)}>Mark read</button>}</div></div>)}{!notifications.length && <p className="muted">No notifications yet.</p>}</div></>}
  {screen === 'dashboard' && <><div className="heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h1>Welcome back, {user.name.split(' ')[0]} <span className="hello">✳</span></h1><p>Here’s what’s happening with your support requests.</p></div>{user.role === 'employee' && <button className="primary" onClick={() => setScreen('new')}><Plus size={17}/> Create ticket</button>}</div><div className="metric-grid">{[{ label:'Total tickets', value:counts.total, icon:ClipboardList },{label:'Open',value:counts.open,icon:CircleHelp},{label:'In progress',value:counts.in_progress,icon:Activity},{label:'Resolved',value:counts.resolved,icon:CheckCircle2}].map(x => <div className="metric" key={x.label}><div className="metric-icon"><x.icon size={20}/></div><p>{x.label}</p><strong>{x.value}</strong></div>)}</div>{user.role !== 'employee' && stats && <div className="phase2-grid"><div className="panel"><h2>SLA monitoring</h2><div className="sla-numbers"><div><strong>{stats.sla_response_breaches}</strong><small>Response overdue</small></div><div><strong>{stats.sla_resolution_breaches}</strong><small>Resolution overdue</small></div></div><p className="muted">Calendar-time demo targets; missed deadlines are computed when the dashboard loads.</p></div><div className="panel"><h2>Engineer workload</h2>{stats.workload?.map(w=><div className="workload" key={w.id}><span>{w.name}</span><strong>{w.active} active / {w.total} total</strong></div>)}{!stats.workload?.length && <p className="muted">No engineers yet</p>}</div></div>}<div className="panel"><div className="panel-heading"><div><h2>Recent tickets</h2><p>Latest support requests</p></div><button className="soft" onClick={() => setScreen('tickets')}>View all</button></div><TicketTable items={tickets.slice(0, 6)} openTicket={openTicket}/></div></>}
  {screen === 'tickets' && <><div className="heading"><div><p className="eyebrow">TICKET MANAGEMENT</p><h1>All tickets</h1><p>{user.role === 'employee' ? 'Track your requests and their progress.' : 'Review, assign and resolve service requests.'}</p></div>{user.role === 'employee' && <button className="primary" onClick={() => setScreen('new')}><Plus size={17}/> New ticket</button>}</div><div className="panel"><div className="filter-grid"><input aria-label="Search tickets" placeholder="Search title, description or ID" value={filters.search} onChange={e=>setFilters({...filters,search:e.target.value})}/>{[['status',['Open','Assigned','In Progress','Resolved','Closed']],['priority',['Low','Medium','High','Critical']],['category',['Network','Hardware','Software','Access','Other']]].map(([key,values])=><select aria-label={'Filter '+key} key={key} value={filters[key]} onChange={e=>setFilters({...filters,[key]:e.target.value})}><option value="">All {key}</option>{values.map(v=><option key={v}>{v}</option>)}</select>)}{user.role !== 'employee' && <select aria-label="Filter assignment" value={filters.assignee} onChange={e=>setFilters({...filters,assignee:e.target.value})}><option value="">All assignments</option><option value="unassigned">Unassigned</option><option value="mine">Assigned to me</option></select>}<button className="soft" onClick={()=>setFilters({search:'',status:'',priority:'',category:'',assignee:''})}>Clear</button></div><div className="filter-caption">Showing {filteredTickets.length} of {tickets.length} tickets</div><TicketTable items={filteredTickets} openTicket={openTicket}/></div></>}
  {screen === 'new' && user.role === 'employee' && <><div className="heading"><div><p className="eyebrow">NEW REQUEST</p><h1>Create a support ticket</h1><p>Tell us about the problem so the IT team can help.</p></div></div><div className="panel form-panel"><form onSubmit={create}><label>Problem title<input maxLength={180} required minLength={3} placeholder="e.g. Laptop cannot connect to Wi-Fi" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}/></label><label>Detailed description<textarea minLength={10} maxLength={5000} rows="6" required placeholder="Describe the issue and any error messages…" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}/></label><div className="two-col"><label>Category<select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}><option value="">Auto detect</option>{['Network','Hardware','Software','Access','Other'].map(x => <option key={x}>{x}</option>)}</select></label><label>Priority<select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>{['Low','Medium','High','Critical'].map(x => <option key={x}>{x}</option>)}</select></label></div><div className="routing-preview"><button type="button" className="soft" onClick={previewRouting}>Suggest category & priority</button>{routingPreview && <div className="routing-result"><strong>Suggestion:</strong> {routingPreview.category} · {routingPreview.priority} · Team: {routingPreview.recommendation.team_name || "Not mapped"} <button type="button" className="soft" onClick={() => setForm(p => ({...p,category:routingPreview.category,priority:routingPreview.priority}))}>Use suggestions</button></div>}</div><button className="primary" disabled={busy}><Plus size={17}/> Submit ticket</button></form></div></>}
  {screen === 'detail' && selected && <><button className="back" onClick={() => setScreen('tickets')}><ArrowLeft size={17}/> Back to tickets</button><div className="heading"><div><p className="eyebrow">TICKET #{String(selected.id).padStart(4, '0')}</p><h1>{selected.title}</h1><p>Created by {selected.creator} · {new Date(selected.created_at).toLocaleString()}</p></div>{badge(selected.status)}</div><div className="detail-grid"><div className="panel detail-main"><h2>Description</h2><p className="description">{selected.description}</p><TicketTools ticketId={selected.id} role={user.role} onChanged={() => openTicket(selected)} /><h2>Activity timeline</h2><div className="activity-list">{events.map(ev=><div className="activity-item" key={ev.id}><span className="activity-dot"/><div><strong>{ev.detail}</strong><small>{ev.actor} · {new Date(ev.created_at).toLocaleString()}</small></div></div>)}{!events.length && <p className="muted">No recorded activity yet (older tickets begin recording after this upgrade).</p>}</div><h2>Suggested troubleshooting</h2><div className="kb-suggestions">{suggestions.length ? suggestions.map(a=><button key={a.id} className="kb-suggestion" onClick={()=>{setArticleToOpen(a.id);setScreen('knowledge')}}><strong>{a.title}</strong><span>{a.summary}</span><small>{a.category} · Read guide →</small></button>) : <p className="muted">No matching published guides yet. Open Knowledge Base to search all articles.</p>}</div><div className="conversation-link-panel"><h2>Ticket conversation</h2><p className="muted">Use the dedicated Conversations workspace to message the employee or engineer.</p><button className="primary" onClick={() => { setChatTicketId(selected.id); setScreen('conversations'); }}><MessageSquare size={16}/> Open conversation</button></div></div><div className="panel detail-aside"><h2>Ticket details</h2><dl><dt>Status</dt><dd>{badge(selected.status)}</dd><dt>Category</dt><dd>{selected.category}</dd><dt>Priority</dt><dd>{badge(selected.priority)}</dd><dt>Assigned to</dt><dd>{selected.assignee || 'Unassigned'}</dd><dt>Response due</dt><dd>{selected.response_due_at ? new Date(selected.response_due_at).toLocaleString() : '—'} {selected.response_breached && <span className="sla-breach">OVERDUE</span>}{selected.first_response_at && <span className="sla-ok">Responded</span>}</dd><dt>Resolution due</dt><dd>{selected.resolution_due_at ? new Date(selected.resolution_due_at).toLocaleString() : '—'} {selected.resolution_breached && <span className="sla-breach">OVERDUE</span>}{selected.resolved_at && <span className="sla-ok">Resolved</span>}</dd></dl>{user.role === 'admin' && <><h3>Assign engineer</h3><select value={selected.assignee_id || ''} onChange={e => e.target.value && update({assignee_id:Number(e.target.value)})}><option value="">Select engineer</option>{engineers.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select></>}{user.role !== 'employee' && <><h3>Update status</h3><div className="action-list">{(selected.status === 'Open' ? ['In Progress'] : selected.status === 'Assigned' ? ['In Progress'] : selected.status === 'In Progress' ? ['Resolved'] : []).map(s => <button className="soft full" disabled={busy} onClick={() => update({status:s})} key={s}>Mark {s}</button>)}{selected.status === 'Open' && user.role === 'admin' && selected.assignee_id && <button className="soft full" onClick={() => update({status:'Assigned'})}>Mark Assigned</button>}</div></>}{user.role === 'employee' && selected.status === 'Resolved' && <><h3>Confirm resolution</h3><div className="action-list"><button className="primary full" onClick={() => update({status:'Closed'})}>Confirm and close</button><button className="soft full" onClick={() => update({status:'Reopened'})}>Issue not fixed — reopen</button></div></>}</div></div></>}
  </div></main></div>;
}
function TicketTable({items, openTicket}) { return <div className="table-wrap"><table><thead><tr><th>Ticket</th><th>Category</th><th>Priority</th><th>Status</th><th>Assigned to</th><th>Created</th></tr></thead><tbody>{items.map(t => <tr key={t.id} onClick={() => openTicket(t)}><td><strong>{t.title}</strong><small>#{String(t.id).padStart(4,'0')} · {t.creator}</small></td><td>{t.category}</td><td>{badge(t.priority)}</td><td>{badge(t.status)}</td><td>{t.assignee || '—'}</td><td>{new Date(t.created_at).toLocaleDateString()}</td></tr>)}</tbody></table>{items.length === 0 && <div className="empty"><Ticket size={30}/><h3>No tickets yet</h3><p>Requests will appear here when created.</p></div>}</div>; }
createRoot(document.getElementById('root')).render(<App/>);
