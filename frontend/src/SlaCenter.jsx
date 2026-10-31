import React, { useEffect, useState } from 'react';

export default function SlaCenter({ api, post, onScan }) {
  const [policies, setPolicies] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api('/sla/policies').then(x => setPolicies(x.policies)).catch(e => setError(e.message)); }, []);
  const change = (priority, field, value) => setPolicies(old => old.map(p => p.priority === priority ? { ...p, [field]: value } : p));
  async function save(p) {
    setBusy(true); setError(''); setNotice('');
    try {
      const data = await post('/sla/policies/' + p.priority, {response_minutes: Number(p.response_minutes), resolution_minutes: Number(p.resolution_minutes)}, 'PUT');
      setNotice(`${p.priority} policy updated. ${data.note}`);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function scan() {
    setBusy(true); setError(''); setNotice('');
    try {
      const { new_breaches } = await post('/sla/scan', {});
      setNotice(`Scan complete: ${new_breaches} new breach(es) logged.`);
      await onScan();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <>
    <div className="heading"><div><p className="eyebrow">SERVICE LEVEL MANAGEMENT</p><h1>SLA Policies</h1><p>Configure deadline targets and manually test breach detection.</p></div></div>
    <div className="panel sla-center">
      <p className="muted">Values are calendar minutes (24/7). New policy values apply only to future tickets. Existing tickets retain their current deadlines.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="sla-notice" role="status">{notice}</p>}
      <div className="sla-policy-list">{policies.map(p => <div className="sla-policy-row" key={p.priority}>
        <strong>{p.priority}</strong>
        <label>Response (minutes)<input type="number" min="1" max="525600" value={p.response_minutes} onChange={e => change(p.priority, 'response_minutes', e.target.value)}/></label>
        <label>Resolution (minutes)<input type="number" min="1" max="525600" value={p.resolution_minutes} onChange={e => change(p.priority, 'resolution_minutes', e.target.value)}/></label>
        <button className="primary" disabled={busy} onClick={() => save(p)}>Save</button>
      </div>)}</div>
      <div className="sla-tools"><button className="soft" disabled={busy} onClick={scan}>Run SLA scan now</button><span className="muted">Automatic checks run every 60 seconds while the Flask development server is running.</span></div>
    </div>
  </>;
}
