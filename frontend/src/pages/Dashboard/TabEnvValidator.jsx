import React, { useEffect, useState } from 'react';
import { api } from '../../api';

export function TabEnvValidator({ projects = [], selectedProject, onSelectProject }) {
  const [envText, setEnvText] = useState('');
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const activeProject = projects.find((project) => project.id === selectedProject?.id) || projects[0] || null;

  useEffect(() => {
    setValidation(null);
    setError('');
  }, [activeProject?.id]);

  const handleValidate = async () => {
    if (!envText.trim()) {
      setError('Enter at least one KEY=VALUE line to validate.');
      return;
    }
    setLoading(true);
    setValidation(null);
    setError('');
    try {
      const res = await api.validateEnv(envText);
      setValidation(res);
    } catch (err) {
      setError(err.message || 'Validation request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLiveAudit = async () => {
    if (!activeProject?.id || !activeProject.render_service_created) return;
    setLoading(true);
    setValidation(null);
    setError('');
    try {
      const result = await api.auditRenderEnv(activeProject.id);
      setValidation(result);
    } catch (err) {
      setError(err.message || 'Live Render audit failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="telemetry-card" style={{ marginBottom: '1.5rem' }}>
        <div className="telemetry-header">
          <div className="telemetry-title">
            <span>⚙️</span> Environment Variable Validator & Secret Leak Shield
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Audit a connected Render service or validate non-production variables. Live values are never shown or saved.
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <label className="form-label" htmlFor="env-audit-project" style={{ margin: 0 }}>Connected project:</label>
          <select
            id="env-audit-project"
            className="form-input"
            value={activeProject?.id || ''}
            disabled={loading || projects.length === 0}
            onChange={(event) => {
              const project = projects.find((item) => String(item.id) === event.target.value);
              if (project) onSelectProject?.(project);
            }}
            style={{ minWidth: '220px', width: 'auto' }}
          >
            {projects.length === 0 && <option value="">No projects connected</option>}
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem', padding: '0.9rem 1rem', background: 'rgba(129, 140, 248, 0.08)', border: '1px solid rgba(129, 140, 248, 0.25)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            {activeProject?.render_service_created
              ? `Audit environment variables configured directly on Render for ${activeProject.name}. Linked Render Environment Groups are not included.`
              : 'Select a project linked to Render to audit its live environment variables.'}
            <div style={{ marginTop: '0.25rem' }}>Values are checked server-side, redacted from results, and never stored.</div>
          </div>
          <button
            onClick={handleLiveAudit}
            disabled={loading || !activeProject?.render_service_created}
            className="btn-primary"
            style={{ padding: '0.5rem 1rem', whiteSpace: 'nowrap' }}
          >
            {loading ? 'Auditing...' : '🛡️ Audit Live Render Environment'}
          </button>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label className="form-label" htmlFor="env-validator-input">Or validate non-production sample variables (KEY=VALUE pairs):</label>
          <textarea
            id="env-validator-input"
            className="form-input"
            rows={7}
            style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', lineHeight: 1.5 }}
            value={envText}
            onChange={(e) => setEnvText(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button
            onClick={() => setEnvText('PORT=hello\nDATABASE_URL=sqlite:///./test.db\nSECRET_KEY=changeme')}
            className="btn-secondary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.82rem' }}
          >
            Load Bad Sample
          </button>
          <button
            onClick={handleValidate}
            disabled={loading || !envText.trim()}
            className="btn-secondary"
            style={{ padding: '0.5rem 1.25rem' }}
          >
            {loading ? 'Auditing...' : '🛡️ Validate Environment Variables'}
          </button>
        </div>
        {error && <p role="alert" style={{ marginTop: '0.85rem', color: '#f87171' }}>{error}</p>}
      </div>

      {validation && (
        <div className="card-table-wrapper">
          <div className="table-header-bar">
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>
                Audit Results: {validation.is_valid ? (
                  <span style={{ color: '#34d399' }}>✓ VALID CONFIGURATION</span>
                ) : (
                  <span style={{ color: '#f87171' }}>✕ ISSUES DETECTED</span>
                )}
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {validation.variables_evaluated} variables evaluated · {validation.errors?.length || 0} errors · {validation.warnings?.length || 0} warnings
              </p>
            </div>
          </div>

          {validation.source === 'render' && (
            <p style={{ padding: '0 1.25rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Live audit for {validation.project_name}. Values were read by the server and redacted before returning this result.
            </p>
          )}
          {validation.errors?.length > 0 && (
            <div role="alert" style={{ padding: '0.75rem 1.25rem', color: '#f87171' }}>
              <strong>Errors</strong>
              <ul>{validation.errors.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>
            </div>
          )}
          {validation.warnings?.length > 0 && (
            <div style={{ padding: '0.75rem 1.25rem', color: '#fbbf24' }}>
              <strong>Warnings</strong>
              <ul>{validation.warnings.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>
            </div>
          )}

          <table className="custom-table">
            <thead>
              <tr>
                <th>Variable Key</th>
                <th>{validation.source === 'render' ? 'Value' : 'Value Preview'}</th>
                <th>Presence</th>
                <th>Audit Notes</th>
              </tr>
            </thead>
            <tbody>
              {validation.sanitized_variables && Object.entries(validation.sanitized_variables).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>{k}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {v || '—'}
                  </td>
                  <td>
                    <span className="badge-status badge-success">PRESENT</span>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {validation.source === 'render' ? 'Value redacted; see audit findings above.' : 'Value is sanitized for display.'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
