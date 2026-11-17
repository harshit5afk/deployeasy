import React, { useState } from 'react';
import { api } from '../../api';

export function TabConsole() {
  const [activeEndpoint, setActiveEndpoint] = useState('/health');
  const [responseOutput, setResponseOutput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusCode, setStatusCode] = useState(null);
  const [latencyMs, setLatencyMs] = useState(null);

  const endpoints = [
    { path: '/health', method: 'GET', desc: 'Basic platform liveness health probe' },
    { path: '/version', method: 'GET', desc: 'Active version tag and Git commit SHA' },
    { path: '/metrics', method: 'GET', desc: 'System metrics and request counters' },
    { path: '/api/system/overview', method: 'GET', desc: 'Live fleet telemetry and uptime summary' },
    { path: '/api/projects', method: 'GET', desc: 'Authenticated microservice fleet list' },
    { path: '/api/runs', method: 'GET', desc: 'Recent GitHub Actions pipeline execution cache' }
  ];

  const handleExecute = async (endpointPath) => {
    setActiveEndpoint(endpointPath);
    setLoading(true);
    setResponseOutput('Executing request...');
    const start = performance.now();
    try {
      let data;
      if (endpointPath === '/health') data = await api.apiFetch ? await fetch('/health').then((r) => r.json()) : { status: 'ok' };
      else if (endpointPath === '/version') data = await api.getVersion();
      else if (endpointPath === '/metrics') data = await api.getMetrics();
      else if (endpointPath === '/api/system/overview') data = await api.getOverview();
      else if (endpointPath === '/api/projects') data = await api.getProjects();
      else if (endpointPath === '/api/runs') data = await api.getRuns();
      else {
        const res = await fetch(endpointPath, { credentials: 'include' });
        data = await res.json();
      }
      setStatusCode(200);
      setLatencyMs(Math.round(performance.now() - start));
      setResponseOutput(JSON.stringify(data, null, 2));
    } catch (err) {
      setStatusCode(err.status || 500);
      setLatencyMs(Math.round(performance.now() - start));
      setResponseOutput(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Controls */}
        <div className="telemetry-card">
          <div className="telemetry-header">
            <div className="telemetry-title">
              <span>⚡</span> REST API Interactive Playground
            </div>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            Directly probe internal DeployEasy backend endpoints to verify responses and latency.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {endpoints.map((ep) => (
              <button
                key={ep.path}
                onClick={() => handleExecute(ep.path)}
                className="btn-secondary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  borderColor: activeEndpoint === ep.path ? 'rgba(99, 102, 241, 0.5)' : 'var(--border)',
                  background: activeEndpoint === ep.path ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.02)'
                }}
              >
                <div style={{ textAlign: 'left' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{ep.method}</span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fff' }}>{ep.path}</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>{ep.desc}</div>
                </div>
                <span style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>→</span>
              </button>
            ))}
          </div>
        </div>

        {/* Response Viewer */}
        <div className="telemetry-card">
          <div className="telemetry-header">
            <div className="telemetry-title">
              <span>📄</span> Response Viewer
            </div>
            {statusCode && (
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <span className={`badge-status ${statusCode < 300 ? 'badge-success' : 'badge-failed'}`}>
                  HTTP {statusCode}
                </span>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                  {latencyMs}ms
                </span>
              </div>
            )}
          </div>

          <pre style={{
            background: '#090c15',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '1rem',
            fontSize: '0.78rem',
            color: '#a7f3d0',
            fontFamily: 'var(--font-mono)',
            maxHeight: '420px',
            overflowY: 'auto',
            lineHeight: 1.5
          }}>
            {responseOutput || '// Click any endpoint on the left to execute...'}
          </pre>
        </div>
      </div>
    </div>
  );
}
