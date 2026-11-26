import React, { useEffect, useState } from 'react';
import { api } from '../../api';
import { formatIndiaDate, formatIndiaDateTime } from './TabDeployments';

const Stat = ({ title, value }) => (
  <div className="stat-card card-cyan"><div className="stat-label">{title}</div><div className="stat-value">{value ?? '—'}</div></div>
);

export function AdminDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setError('');
    try { setData(await api.getAdminDashboard()); }
    catch (err) { setError(err.message || 'Could not load administrator dashboard.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <div className="telemetry-card">Loading admin dashboard…</div>;
  if (error) return <div className="telemetry-card" role="alert">{error} <button className="btn-secondary" onClick={load}>Retry</button></div>;

  const integrationRows = [
    ['GitHub token', data.integrations.github_token_configured],
    ['Deployment result callback', data.integrations.deployment_callback_configured],
    ['GitHub workflow webhook', data.integrations.github_webhook_configured],
  ];

  return <div style={{ display: 'grid', gap: '1.25rem' }}>
    <div className="telemetry-header">
      <div><h2>Administrator dashboard</h2><p style={{ color: 'var(--text-muted)' }}>Platform-wide account, repository, deployment, and integration overview.</p></div>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <a href="/docs" target="_blank" rel="noreferrer" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.55rem 0.95rem', fontSize: '0.88rem' }}>
          <span>📖</span> API Docs ↗
        </a>
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
    </div>

    <div className="grid-stats">
      <Stat title="Users" value={data.summary.users} />
      <Stat title="Projects" value={data.summary.projects} />
      <Stat title="Deployments" value={data.summary.deployments} />
      <Stat title="Successful / Failed" value={`${data.summary.successful_deployments} / ${data.summary.failed_deployments}`} />
    </div>

    <section className="telemetry-card">
      <div className="telemetry-header">
        <h3>Platform & API Documentation</h3>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#34d399' }}>Admin Only</span>
      </div>
      <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Interactive OpenAPI (Swagger) specifications, endpoints explorer, and platform architecture docs.
      </p>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <a href="/docs" target="_blank" rel="noreferrer" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.85rem', padding: '0.5rem 1rem' }}>
          Open Swagger UI (/docs) ↗
        </a>
        <a href="/redoc" target="_blank" rel="noreferrer" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.85rem', padding: '0.5rem 1rem' }}>
          Open ReDoc (/redoc) ↗
        </a>
      </div>
    </section>

    <section className="telemetry-card">
      <div className="telemetry-header"><h3>Integration configuration</h3><span>Environment: {data.integrations.environment}</span></div>
      <div style={{ display: 'grid', gap: '0.65rem' }}>
        {integrationRows.map(([label, configured]) => <div key={label} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', padding: '0.65rem 0' }}>
          <span>{label}</span><strong style={{ color: configured ? '#34d399' : '#fbbf24' }}>{configured ? 'Configured' : 'Not configured'}</strong>
        </div>)}
      </div>
      <small style={{ color: 'var(--text-muted)' }}>Secret values are never shown here.</small>
    </section>

    <section className="card-table-wrapper">
      <div className="table-header-bar"><h3>Users</h3><span>{data.users.length} accounts</span></div>
      <div style={{ overflowX: 'auto' }}><table className="custom-table"><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Projects</th><th>Account</th><th>Joined</th></tr></thead><tbody>
        {data.users.map((item) => <tr key={item.id}><td>{item.username}</td><td>{item.email}</td><td>{item.role}</td><td>{item.project_count}</td><td>{item.is_active ? 'Active' : 'Disabled'}</td><td>{item.created_at ? formatIndiaDate(item.created_at) : '—'}</td></tr>)}
      </tbody></table></div>
    </section>

    <section className="card-table-wrapper">
      <div className="table-header-bar"><h3>Connected repositories</h3><span>{data.projects.length} projects</span></div>
      <div style={{ overflowX: 'auto' }}><table className="custom-table"><thead><tr><th>Project</th><th>Repository</th><th>Owner</th><th>Branch</th><th>Status</th><th>Service URL</th><th>Deploy hook</th></tr></thead><tbody>
        {data.projects.map((item) => <tr key={item.id}><td>{item.name}</td><td><a href={`https://github.com/${item.repo_name}`} target="_blank" rel="noreferrer">{item.repo_name}</a></td><td>{item.owner}</td><td>{item.branch}</td><td>{item.status}</td><td>{item.service_configured ? 'Configured' : 'Missing'}</td><td>{item.deploy_hook_configured ? 'Configured' : 'Missing'}</td></tr>)}
        {data.projects.length === 0 && <tr><td colSpan="7">No repositories connected.</td></tr>}
      </tbody></table></div>
    </section>

    <section className="card-table-wrapper">
      <div className="table-header-bar"><h3>Recent deployments</h3><span>Latest 12</span></div>
      <div style={{ overflowX: 'auto' }}><table className="custom-table"><thead><tr><th>Project</th><th>Repository</th><th>Commit</th><th>Type</th><th>Status</th><th>Created</th></tr></thead><tbody>
        {data.recent_deployments.map((item) => <tr key={item.id}><td>{item.project_name}</td><td>{item.repo_name}</td><td><code>{item.commit_sha.slice(0, 8)}</code></td><td>{item.trigger_type}</td><td>{item.status}</td><td>{item.created_at ? formatIndiaDateTime(item.created_at) : '—'}</td></tr>)}
        {data.recent_deployments.length === 0 && <tr><td colSpan="6">No deployment activity yet.</td></tr>}
      </tbody></table></div>
    </section>
  </div>;
}
