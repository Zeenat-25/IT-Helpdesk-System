import React, { useEffect, useState } from 'react';
import { BarChart3, Download, RefreshCcw } from 'lucide-react';

const dataPoints = (obj) => Object.entries(obj || {}).map(([name, value]) => ({name, value}));
function Bars({title, data, empty='No tickets in this period'}) {
  const max = Math.max(1, ...data.map(x => x.value));
  return <div className="panel analytics-panel"><h2>{title}</h2>{data.length ? <div className="analytics-bars">
    {data.map(d => <div className="analytics-bar" key={d.name}><div className="analytics-row"><span>{d.name}</span><strong>{d.value}</strong></div><div className="analytics-track"><div style={{width:`${100*d.value/max}%`}} /></div></div>)}
  </div> : <p className="muted">{empty}</p>}</div>;
}
export default function Analytics({api}) {
  const [start,setStart] = useState(''), [end,setEnd] = useState('');
  const [summary,setSummary] = useState(null),[error,setError] = useState(''),[busy,setBusy] = useState(false);
  const params = () => {const q = new URLSearchParams(); if(start)q.set('start',start); if(end)q.set('end',end);return q.toString();};
  async function load() {setBusy(true);setError('');try{setSummary(await api('/reports/summary?'+params()));}catch(e){setError(e.message)}finally{setBusy(false)}}
  useEffect(()=>{load()},[]);
  async function download(format) {
    setError('');
    try {
      const resp=await fetch('/api/reports/export?'+params()+'&format='+format,{credentials:'include'});
      if(!resp.ok){const body=await resp.json().catch(()=>({}));throw new Error(body.error||`Export failed (${resp.status})`)}
      const blob=await resp.blob();const url=URL.createObjectURL(blob);
      const link=document.createElement('a');link.href=url;link.download=`helpdesk-report.${format}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
    }catch(e){setError(e.message)}
  }
  return <div className="analytics-page">
    <div className="heading"><div><p className="eyebrow">ADMIN ANALYTICS</p><h1>Analytics & Reports</h1><p>Track tickets created within the selected UTC date range.</p></div></div>
    <div className="panel analytics-toolbar"><label>From (UTC)<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>To (UTC)<input type="date" value={end} min={start||undefined} onChange={e=>setEnd(e.target.value)}/></label>
      <button className="soft" onClick={load} disabled={busy}><RefreshCcw size={16}/>{busy?'Loading…':'Apply filters'}</button>
      <button className="soft" onClick={()=>download('csv')}><Download size={16}/>CSV</button><button className="primary" onClick={()=>download('xlsx')}><Download size={16}/>Excel</button></div>
    {error && <div className="error alert">{error}</div>}
    {summary && <><div className="analytics-metrics">{[
      ['Total tickets',summary.total],['Resolved tickets',summary.resolved_count],['Avg. resolution',summary.average_resolution_hours===null?'—':summary.average_resolution_hours+' hrs'],['Response breaches',summary.response_breaches],['Resolution breaches',summary.resolution_breaches]
    ].map(([label,value])=><div className="metric" key={label}><div className="metric-icon"><BarChart3 size={18}/></div><p>{label}</p><strong>{value}</strong></div>)}</div>
    <div className="analytics-grid"><Bars title="Ticket status" data={dataPoints(summary.statuses)}/><Bars title="Categories" data={dataPoints(summary.categories)}/><Bars title="Priority distribution" data={dataPoints(summary.priorities)}/><Bars title="Created by month" data={(summary.months||[]).map(x=>({name:x.month,value:x.count}))}/><Bars title="Engineer workload (active)" data={(summary.engineer_workload||[]).map(x=>({name:x.name,value:x.active}))}/></div>
    <p className="muted">Breach counts include overdue tickets and historical misses for the selected tickets. Filters apply to ticket creation date (UTC), not resolution date. Resolution time measures time from creation to the latest resolution.</p></>}
  </div>;
}
