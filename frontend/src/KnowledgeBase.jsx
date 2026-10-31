import React, {useEffect, useState} from 'react';
import {BookOpen, Plus, Search, Pencil, Trash2, ArrowLeft} from 'lucide-react';

const blank = {title:'', category:'Network', summary:'', content:'', keywords:'', published:true};
export default function KnowledgeBase({api, post, user, initialArticleId}) {
  const [articles, setArticles] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [opened, setOpened] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(blank);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const isAdmin = user.role === 'admin';
  async function load() {
    try { const data = await api('/knowledge'); setArticles(data.articles); }
    catch(e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!initialArticleId) return;
    api('/knowledge/' + initialArticleId).then(r=>setOpened(r.article)).catch(e=>setError(e.message));
  }, [initialArticleId]);
  function beginEdit(a) {setOpened(null);setEditing(a?.id || 'new');setForm(a ? {title:a.title,category:a.category,summary:a.summary,content:a.content,keywords:a.keywords,published:a.published} : blank);setError('');setNotice('');}
  async function save(e) {
    e.preventDefault();setBusy(true);setError('');
    try {
      if (editing === 'new') await post('/knowledge',form);
      else await post('/knowledge/' + editing,form,'PATCH');
      setEditing(null);setNotice('Article saved successfully.');await load();
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function remove(a) {
    if (!window.confirm('Delete this article permanently?')) return;
    setBusy(true);setError('');
    try {await api('/knowledge/'+a.id,{method:'DELETE'});setOpened(null);setNotice('Article deleted.');await load();}
    catch(e) {setError(e.message);}finally{setBusy(false);}
  }
  const visible = articles.filter(a=>(!category || a.category===category) && (!search.trim() || [a.title,a.summary,a.content,a.keywords].join(' ').toLowerCase().includes(search.toLowerCase())));
  return <section className="kb-root">
    <div className="heading"><div><p className="eyebrow">SELF-SERVICE SUPPORT</p><h1>Knowledge Base</h1><p>Find practical fixes, explore guides, and get back to work faster.</p></div>{isAdmin && !editing && <button className="primary" onClick={()=>beginEdit(null)}><Plus size={16}/> New article</button>}</div>
    {!editing && !opened && <div className="kb-overview"><div className="kb-overview-icon"><BookOpen size={22}/></div><div><strong>Solutions at your fingertips</strong><p>Browse verified guides for connectivity, software, hardware and account access.</p></div><div className="kb-overview-count">{articles.filter(a=>a.published).length}<small>Published guides</small></div></div>}
    {error && <div className="error alert">{error}</div>}{notice && <p className="kb-notice">{notice}</p>}
    {editing ? <div className="panel kb-editor"><button type="button" className="back" onClick={()=>setEditing(null)}><ArrowLeft size={16}/> Cancel editing</button><h2>{editing==='new'?'Create article':'Edit article'}</h2><form onSubmit={save}>
      <label>Title<input required minLength="3" maxLength="180" value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label>
      <label>Category<select value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>{['Network','Hardware','Software','Access','Other'].map(c=><option key={c}>{c}</option>)}</select></label>
      <label>Summary<textarea required minLength="10" maxLength="400" rows="2" value={form.summary} onChange={e=>setForm({...form,summary:e.target.value})}/></label>
      <label>Troubleshooting steps<textarea required minLength="20" maxLength="10000" rows="9" value={form.content} onChange={e=>setForm({...form,content:e.target.value})}/></label>
      <label>Keywords (comma separated)<input maxLength="500" placeholder="wifi, internet, router" value={form.keywords} onChange={e=>setForm({...form,keywords:e.target.value})}/></label>
      <label className="kb-check"><input type="checkbox" checked={form.published} onChange={e=>setForm({...form,published:e.target.checked})}/> Published (visible to employees and engineers)</label>
      <button disabled={busy} className="primary">{busy?'Saving…':'Save article'}</button>
    </form></div> : opened ? <div className="panel kb-article"><button className="back" onClick={()=>setOpened(null)}><ArrowLeft size={16}/> All articles</button><p className="eyebrow">{opened.category}{!opened.published?' · DRAFT':''}</p><h2>{opened.title}</h2><p>{opened.summary}</p><div className="kb-steps">{opened.content}</div>{isAdmin && <div className="kb-actions"><button className="soft" onClick={()=>beginEdit(opened)}><Pencil size={15}/> Edit</button><button className="soft" disabled={busy} onClick={()=>remove(opened)}><Trash2 size={15}/> Delete</button></div>}</div> : <>
      <div className="panel kb-search"><div className="kb-search-input"><Search size={17}/><input aria-label="Search knowledge articles" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search Wi-Fi, password, printer…"/></div><select aria-label="Knowledge category" value={category} onChange={e=>setCategory(e.target.value)}><option value="">All categories</option>{['Network','Hardware','Software','Access','Other'].map(c=><option key={c}>{c}</option>)}</select></div>
      <p className="kb-results">Showing {visible.length} {visible.length===1 ? "guide" : "guides"}{category ? ` in ${category}` : ""}</p><div className="kb-grid">{visible.map(a=><article className="panel kb-card" key={a.id}><div className="kb-card-top"><span className="kb-icon"><BookOpen size={19}/></span><span className="kb-category">{a.category}{!a.published?" · Draft":""}</span></div><h2>{a.title}</h2><p>{a.summary}</p><button className="kb-read" onClick={()=>setOpened(a)}>Read troubleshooting guide <span aria-hidden="true">→</span></button></article>)}</div>{!visible.length&&<div className="panel kb-empty"><strong>No matching guides</strong><p>Try a different keyword or category, or create a support ticket.</p></div>}
    </>}
  </section>;
}
