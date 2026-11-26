import React from 'react';
import { MetricCard } from '../../components/MetricCard';
import { parseDate } from './TabDeployments';

export function TabOverview({ overview, projects, onSwitchTab }) {
  const total = overview?.total_projects ?? projects?.length ?? 0;
  const completed = (overview?.successful_deployments || 0) + (overview?.failed_deployments || 0);
  const rate = completed ? `${Math.round((overview.successful_deployments / completed) * 100)}%` : '—';
  const avg = overview?.avg_deploy_time_seconds;
  const uptime = overview?.process_uptime_seconds;
  const duration = (value) => value == null ? '—' : `${Math.floor(value / 60)}m ${Math.floor(value % 60)}s`;
  return <div>
    <div className="grid-stats">
      <MetricCard label="Projects" value={total} subtext="Projects visible to your account" color="purple" />
      <MetricCard label="Deployment Success" value={rate} subtext={`${overview?.successful_deployments ?? 0} successful · ${overview?.failed_deployments ?? 0} failed`} color="cyan" />
      <MetricCard label="Fleet Health" value={overview?.fleet_health || 'Unknown'} subtext="Based on latest recorded health probes" color="green" />
      <MetricCard label="Average Deploy Time" value={avg == null ? '—' : `${avg}s`} subtext="Recorded deployment durations" color="amber" />
    </div>
    <div className="telemetry-card" style={{ marginTop: '1rem' }}>
      <div className="telemetry-header"><div className="telemetry-title">DeployEasy server telemetry</div><span>This is the dashboard server, not your connected repository's app · {overview?.version || 'Version unavailable'}</span></div>
      <div className="hardware-metrics-row">
        <div className="hw-tile"><div className="hw-tile-label">Process uptime</div><div className="hw-tile-val">{duration(uptime)}</div></div>
        <div className="hw-tile"><div className="hw-tile-label">Requests served</div><div className="hw-tile-val">{overview?.requests_served ?? '—'}</div></div>
        <div className="hw-tile"><div className="hw-tile-label">Projects</div><div className="hw-tile-val">{overview?.active_deployments ?? '—'}</div><div className="hw-tile-sub">Operational status</div></div>
        <div className="hw-tile"><div className="hw-tile-label">Telemetry source</div><div className="hw-tile-val">Live API</div></div>
      </div>
    </div>
    <div className="telemetry-card" style={{ marginTop: '1rem' }}>
      <div className="telemetry-header"><div className="telemetry-title">Recent deployments</div><button className="btn-secondary" onClick={() => onSwitchTab('deployments')}>View deployments</button></div>
      {(overview?.recent_deployments || []).length === 0 ? <p>No deployment records yet.</p> : <table className="custom-table"><thead><tr><th>Project</th><th>Commit</th><th>Status</th><th>Created</th></tr></thead><tbody>
        {overview.recent_deployments.map((dep) => <tr key={dep.id}><td>{projects?.find((project) => project.id === dep.project_id)?.name || `Project ${dep.project_id}`}</td><td>{dep.commit_sha?.slice(0, 8)}</td><td>{dep.status}</td><td>{dep.created_at ? parseDate(dep.created_at).toLocaleString() : '—'}</td></tr>)}
      </tbody></table>}
    </div>
    <div style={{ marginTop: '1rem' }}><button className="btn-secondary" onClick={() => onSwitchTab('readiness')}>Review deployment readiness</button></div>
  </div>;
}
