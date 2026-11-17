import React, { useEffect, useState } from 'react';
import { api } from '../../api';

export function TabFinOps({ projects, selectedProject }) {
  const projectId = selectedProject?.id || projects?.[0]?.id;
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!projectId) { setData(null); return; }
    api.getCostEstimate(projectId).then(setData).catch((e) => { setError(e.message); setData(null); });
  }, [projectId]);
  if (!projectId) return <div className="telemetry-card">Select a project to estimate its costs.</div>;
  if (error) return <div className="telemetry-card">Cost estimate unavailable: {error}</div>;
  if (!data) return <div className="telemetry-card">Loading cost estimate…</div>;
  const money = (value) => `$${Number(value || 0).toFixed(2)}`;
  return <div style={{ display: 'grid', gap: '1rem' }}>
    <div className="stat-card card-amber"><div className="stat-label">Projected monthly cost</div><strong style={{ fontSize: '2rem' }}>{money(data.projected_monthly_cost_usd)}</strong><div>Estimate based on recorded deployment duration, hosting tier, and image count.</div></div>
    <div className="telemetry-card"><h3>Cost breakdown</h3><div style={{ display: 'grid', gap: '0.6rem' }}>{Object.entries(data.breakdown || {}).map(([key, value]) => <div key={key} style={{ display: 'flex', justifyContent: 'space-between' }}><span>{key.replaceAll('_', ' ')}</span><strong>{money(value)}</strong></div>)}</div></div>
    <div className="telemetry-card"><h3>Usage assumptions</h3><p>Instance tier: {data.metrics?.instance_tier || 'Unknown'} · Deploy minutes: {data.metrics?.total_deploy_minutes ?? '—'} · Projected monthly minutes: {data.metrics?.projected_monthly_minutes ?? '—'} · Images: {data.metrics?.images_stored_count ?? '—'} · Image size: {data.metrics?.container_image_size_mb ?? '—'} MB</p></div>
    <div className="telemetry-card"><h3>Recommendations</h3>{data.recommendations?.length ? <ul>{data.recommendations.map((item, index) => <li key={index}><strong>{item.title}</strong> ({item.impact}): {item.suggestion}</li>)}</ul> : <p>No recommendations returned.</p>}</div>
  </div>;
}
