import React, { useState } from 'react';
import { api } from '../../api';

export function TabDiagnostics({ projects, selectedProject }) {
  const activeProjectId = selectedProject?.id || (projects && projects[0]?.id);

  // A. Failure Diagnostics
  const [logText, setLogText] = useState('');
  const [diagnosis, setDiagnosis] = useState(null);
  const [diagnosing, setDiagnosing] = useState(false);

  // B. Post-Mortem
  const [failedSha, setFailedSha] = useState('');
  const [incidentSummary, setIncidentSummary] = useState('');
  const [postMortem, setPostMortem] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  // C. Webhook Dispatcher
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookType, setWebhookType] = useState('discord');
  const [webhookMsg, setWebhookMsg] = useState(null);
  const [sendingWebhook, setSendingWebhook] = useState(false);

  const handleAnalyzeLogs = async () => {
    setDiagnosing(true);
    setDiagnosis(null);
    try {
      const res = await api.analyzeLogs(logText);
      setDiagnosis(res);
    } catch (err) {
      alert(err.message || 'Log analysis failed');
    } finally {
      setDiagnosing(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!activeProjectId) return;
    setGeneratingReport(true);
    try {
      const res = await api.generateIncidentReport(activeProjectId, {
        failed_sha: failedSha,
        symptoms: incidentSummary
      });
      setPostMortem(res);
    } catch (err) {
      alert(err.message || 'Report generation failed');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleSendWebhook = async () => {
    setSendingWebhook(true);
    setWebhookMsg(null);
    try {
      const res = await api.testWebhook(activeProjectId, webhookUrl, webhookType);
      setWebhookMsg({ type: res.success ? 'success' : 'error', text: res.message });
    } catch (err) {
      setWebhookMsg({ type: 'error', text: `✕ Webhook blocked: ${err.message}` });
    } finally {
      setSendingWebhook(false);
    }
  };

  return (
    <div>
      {/* Feature A: Failure Diagnostics */}
      <div className="telemetry-card" style={{ marginBottom: '1.5rem' }}>
        <div className="telemetry-header">
          <div className="telemetry-title">
            <span>🩺</span> A. Automated CI Failure Diagnostics
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Parse GitHub Actions logs to identify error category, root cause, and corrective action
          </span>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label className="form-label">Paste GitHub Actions / Container Logs:</label>
          <textarea
            className="form-input"
            rows={5}
            style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
            value={logText}
            onChange={(e) => setLogText(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleAnalyzeLogs}
            disabled={diagnosing}
            className="btn-primary"
            style={{ padding: '0.5rem 1.25rem' }}
          >
            {diagnosing ? 'Analyzing...' : '🔍 Analyze Failure Logs'}
          </button>
        </div>

        {diagnosis && (
          <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="badge-status badge-failed">{diagnosis.error_category || 'Analysis'}</span>
              <strong style={{ fontSize: '0.9rem', color: '#fff' }}>Root Cause Identified</strong>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#fca5a5', marginBottom: '0.65rem' }}>
              {diagnosis.root_cause || diagnosis.summary}
            </p>
            <div style={{ padding: '0.65rem 0.85rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontSize: '0.78rem', color: '#a7f3d0' }}>
              <strong>Suggested Fix:</strong> {diagnosis.suggested_fix}
            </div>
          </div>
        )}
      </div>

      {/* Feature B: Incident Post-Mortem */}
      <div className="telemetry-card" style={{ marginBottom: '1.5rem' }}>
        <div className="telemetry-header">
          <div className="telemetry-title">
            <span>📝</span> B. Incident Post-Mortem Generator
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Generate blameless post-mortem markdown document with timeline and root cause findings
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label className="form-label">Incident Title</label>
            <input type="text" className="form-input" placeholder="Failed release commit SHA" value={failedSha} onChange={(e) => setFailedSha(e.target.value)} />
          </div>
          <div>
            <label className="form-label">Brief Outage Summary</label>
            <input
              type="text"
              className="form-input"
              value={incidentSummary}
              onChange={(e) => setIncidentSummary(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="btn-primary"
            style={{ padding: '0.5rem 1.25rem' }}
          >
            {generatingReport ? 'Generating...' : '📄 Generate Post-Mortem Report'}
          </button>
        </div>

        {postMortem && (
          <div style={{ marginTop: '1.25rem', background: '#0a0d14', border: '1px solid var(--border)', borderRadius: '10px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <strong style={{ fontSize: '0.92rem', color: '#c7d2fe' }}>Generated Post-Mortem Document</strong>
              <button
                onClick={() => navigator.clipboard.writeText(postMortem.markdown || JSON.stringify(postMortem, null, 2))}
                className="btn-secondary"
                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
              >
                Copy Markdown
              </button>
            </div>
            <pre style={{ fontSize: '0.78rem', color: '#cbd5e1', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', lineHeight: 1.6 }}>
              {postMortem.markdown_report || JSON.stringify(postMortem, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Feature C: Webhook Dispatcher */}
      <div className="telemetry-card">
        <div className="telemetry-header">
          <div className="telemetry-title">
            <span>🔔</span> C. Discord / Slack Webhook Dispatcher
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Broadcast real-time alert notifications to team communication channels with SSRF validation
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr auto', gap: '1rem', alignItems: 'flex-end', marginBottom: '1rem' }}>
          <div>
            <label className="form-label">Platform</label>
            <select
              className="form-input"
              value={webhookType}
              onChange={(e) => setWebhookType(e.target.value)}
            >
              <option value="discord" style={{ background: '#111522' }}>Discord</option>
              <option value="slack" style={{ background: '#111522' }}>Slack</option>
            </select>
          </div>
          <div>
            <label className="form-label">Webhook Endpoint URL (HTTPS)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://discord.com/api/webhooks/..."
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
          </div>
          <button
            onClick={handleSendWebhook}
            disabled={sendingWebhook}
            className="btn-primary"
            style={{ padding: '0.65rem 1.25rem', height: '40px' }}
          >
            {sendingWebhook ? 'Sending...' : 'Dispatch Alert'}
          </button>
        </div>

        {webhookMsg && (
          <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', fontSize: '0.82rem', background: webhookMsg.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)', border: webhookMsg.type === 'error' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)', color: webhookMsg.type === 'error' ? '#fca5a5' : '#34d399' }}>
            {webhookMsg.text}
          </div>
        )}
      </div>
    </div>
  );
}
