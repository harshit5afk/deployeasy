import React, { useEffect, useState } from 'react';
import { api } from '../../api';

export function TabReadiness({ projects, selectedProject }) {
  const projectId = selectedProject?.id || projects?.[0]?.id;
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!projectId) { setData(null); return; }
    setLoading(true); setError('');
    try { setData(await api.getReadinessScore(projectId)); }
    catch (err) { setData(null); setError(err.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [projectId]);

  if (!projectId) return <div className="telemetry-card">Add or select a project to evaluate deployment readiness.</div>;
  if (loading && !data) return <div className="telemetry-card">Evaluating current project evidence…</div>;
  if (error) return <div className="telemetry-card">Readiness could not be loaded: {error} <button className="btn-secondary" onClick={load}>Retry</button></div>;

  const score = data?.readiness_score ?? 0;
  const ready = data && !data.deployment_blocked;
  return <div className="telemetry-card">
    <div className="telemetry-header">
      <div className="telemetry-title">Deployment readiness · {score}/{data?.max_score ?? 100} · {data?.confidence_tier || 'Unknown'}</div>
      <button className="btn-secondary" onClick={load} disabled={loading}>Re-evaluate</button>
    </div>
    <p>{data?.recommendation || 'No readiness evidence is available.'}</p>
    <p className="badge-status" style={{ color: ready ? '#34d399' : '#f87171' }}>{ready ? 'No current deployment blockers' : 'Deployment blocked by current evidence'}</p>
    {data?.blocking_reasons?.length > 0 && <ul>{data.blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}
    <div style={{ display: 'grid', gap: '0.65rem', marginTop: '1rem' }}>
      {(data?.checklist || []).map((item) => <div key={item.category} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', borderBottom: '1px solid var(--border)', padding: '0.65rem 0' }}>
        <div><strong>{item.category}</strong><div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{item.message}</div></div>
        <span>{item.status} · {item.points} pts</span>
      </div>)}
    </div>
    <small style={{ color: 'var(--text-muted)' }}>Evaluated target: {data?.evaluated_target || 'Unavailable'} · {data?.evaluated_at ? new Date(data.evaluated_at).toLocaleString() : ''}</small>
  </div>;
}
