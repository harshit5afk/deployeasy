import React, { useState } from 'react';
import { api } from '../../api';

export function TabProjects({ projects, onRefreshProjects, onOpenNewProject, onEditProject }) {
  const [probingId, setProbingId] = useState(null);
  const [probeResult, setProbeResult] = useState(null);

  const handleProbe = async (pId) => {
    setProbingId(pId);
    setProbeResult(null);
    try {
      const res = await api.probeHealth(pId);
      setProbeResult({
        projectId: pId,
        latency: res.response_time_ms,
        status: res.status_code,
        isHealthy: res.is_healthy
      });
      if (onRefreshProjects) onRefreshProjects();
    } catch (err) {
      setProbeResult({
        projectId: pId,
        latency: null,
        error: err.message || 'Probe failed'
      });
    } finally {
      setProbingId(null);
    }
  };

  return (
    <div>
      <div className="card-table-wrapper">
        <div className="table-header-bar">
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Connected Fleet & Microservices</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Continuous health monitoring, deployment dispatchers, and automated smoke testing</p>
          </div>
          {onOpenNewProject && <button onClick={onOpenNewProject} className="btn-sm-primary">
            + Connect Service
          </button>}
        </div>

        <table className="custom-table">
          <thead>
            <tr>
              <th>Service Name</th>
              <th>Status</th>
              <th>Production URL</th>
              <th>Last Probe Latency</th>
              <th>Deploy Hook (Masked)</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects && projects.length > 0 ? (
              projects.map((p) => {
                const isProbing = probingId === p.id;
                const result = probeResult && probeResult.projectId === p.id ? probeResult : null;
                return (
                  <tr key={p.id}>
                    <td>
                      <div style={{ fontWeight: 700, color: '#fff' }}>{p.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}><a href={`https://github.com/${p.repo_name}`} target="_blank" rel="noreferrer">{p.repo_name}</a> · {p.branch}</div>
                    </td>
                    <td>
                      <span className={`badge-status ${p.status === 'operational' ? 'badge-success' : 'badge-deploying'}`}>
                        {p.status?.toUpperCase() || 'OPERATIONAL'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#38bdf8' }}>
                      {p.service_url || 'Not configured'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                      {result ? (
                        result.isHealthy ? (
                          <span style={{ color: '#34d399', fontWeight: 700 }}>{result.latency}ms (200 OK)</span>
                        ) : (
                          <span style={{ color: '#f87171' }}>Failed</span>
                        )
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>No probe recorded</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                      {p.has_deploy_hook ? 'Configured' : 'Not configured'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {onEditProject && <button
                        onClick={() => onEditProject && onEditProject(p)}
                        className="btn-secondary"
                        style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', marginRight: '0.4rem' }}
                      >
                        Configure
                      </button>}
                      <button
                        onClick={() => handleProbe(p.id)}
                        disabled={isProbing}
                        className="btn-secondary"
                        style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem' }}
                      >
                        {isProbing ? 'Probing...' : '🩺 Probe /health'}
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No services connected. Click '+ Connect Service' above!
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
