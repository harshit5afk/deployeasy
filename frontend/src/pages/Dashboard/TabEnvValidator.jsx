import React, { useState } from 'react';
import { api } from '../../api';

export function TabEnvValidator() {
  const [envText, setEnvText] = useState('');

  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleValidate = async () => {
    setLoading(true);
    setValidation(null);
    try {
      const res = await api.validateEnv(envText);
      setValidation(res);
    } catch (err) {
      alert(err.message || 'Validation request failed');
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
            Validate key/value syntax and policy checks. Avoid pasting production secrets into this tool.
          </span>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label className="form-label">Enter non-production sample variables (Key=Value pairs):</label>
          <textarea
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
            disabled={loading}
            className="btn-primary"
            style={{ padding: '0.5rem 1.25rem' }}
          >
            {loading ? 'Auditing...' : '🛡️ Validate Environment Variables'}
          </button>
        </div>
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

          <table className="custom-table">
            <thead>
              <tr>
                <th>Variable Key</th>
                <th>Masked Value Preview</th>
                <th>Validation Status</th>
                <th>Notes / Recommendations</th>
              </tr>
            </thead>
            <tbody>
              {validation.sanitized_variables && Object.entries(validation.sanitized_variables).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fff' }}>{k}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {v || '—'}
                  </td>
                  <td>
                    {validation.errors?.length === 0 ? (
                      <span className="badge-status badge-success">OK</span>
                    ) : (
                      <span className="badge-status badge-failed">INVALID</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: v.warning ? '#fbbf24' : 'var(--text-muted)' }}>
                    {validation.warnings?.join(', ') || validation.errors?.join(', ') || 'Checked by server policy.'}
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
