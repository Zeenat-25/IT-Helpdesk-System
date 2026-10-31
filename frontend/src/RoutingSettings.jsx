import React, { useEffect, useState } from 'react';

export default function RoutingSettings({api,post}) {
 const [data,setData]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[saving,setSaving]=useState(false);
 const load=()=>api('/admin/routing').then(setData).catch(e=>setError(e.message));
 useEffect(()=>{load()},[]);
 const save=async()=>{setSaving(true);setError('');setNotice('');try{await post('/admin/routing',{auto_assign:data.auto_assign,rules:data.rules.map(({category,team_id})=>({category,team_id}))},'PUT');setNotice('Routing settings saved. They apply to new tickets only.');load()}catch(e){setError(e.message)}finally{setSaving(false)}};
 if (!data)return <div className="panel" style={{padding:24}}>{error||'Loading routing rules…'}</div>;
 return <section className="routing-page"><div className="heading"><div><p className="eyebrow">AUTOMATION</p><h1>Smart Routing</h1><p>Map ticket categories to support teams and recommend the least-busy active engineer.</p></div></div>
 {error&&<div className="routing-warning">{error}</div>}{notice&&<div className="routing-success">{notice}</div>}
 <div className="panel routing-panel"><label className="routing-toggle"><input type="checkbox" checked={data.auto_assign} onChange={e=>setData({...data,auto_assign:e.target.checked})}/><span><strong>Automatically assign new tickets</strong><small>Off by default. Existing tickets and manual assignments remain unchanged. Only engineers in mapped teams are eligible.</small></span></label>
 <div className="routing-table"><div className="routing-row routing-header"><span>Ticket category</span><span>Support team</span><span>Suggested engineer</span></div>{data.rules.map(rule=><div className="routing-row" key={rule.category}><strong>{rule.category}</strong><select value={rule.team_id??''} onChange={e=>setData(p=>({...p,rules:p.rules.map(r=>r.category===rule.category?{...r,team_id:e.target.value?Number(e.target.value):null}:r)}))}><option value="">Not configured</option>{data.teams.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select><span className="routing-note">{rule.recommendation?.engineer_name||'Save settings to refresh recommendations'}</span></div>)}</div>
 <div className="routing-actions"><button className="primary" disabled={saving} onClick={save}>{saving?'Saving…':'Save routing settings'}</button></div></div>
 <div className="panel routing-panel"><h3>How it works</h3><p>First create support teams and add engineers in Users & Teams. Map categories here. The routing engine picks the engineer with the fewest active tickets. Priority suggestions rely on problem wording and can be overridden by staff.</p><p>For an existing unassigned ticket, an admin may use Smart assign on its details page.</p></div></section>
}
