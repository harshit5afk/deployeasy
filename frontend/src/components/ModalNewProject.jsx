import React, { useState } from 'react';
import { api } from '../api';

export function ModalNewProject({ isOpen, onClose, onProjectCreated }) {
  const [name, setName] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [serviceUrl, setServiceUrl] = useState('');
  const [deployHookUrl, setDeployHookUrl] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.createProject({
        name,
        repo_url: repoUrl || undefined,
        service_url: serviceUrl || undefined,
        deploy_hook_url: deployHookUrl || undefined
      });
      setName('');
      setRepoUrl('');
      setServiceUrl('');
      setDeployHookUrl('');
      if (onProjectCreated) onProjectCreated(created);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Connect New Cloud Project</h3>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.25rem', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>

        {error && (
          <div style={{ padding: '0.65rem 0.85rem', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', color: '#fca5a5', fontSize: '0.82rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Project Name *</label>
            <input
              type="text"
              required
              className="form-input"
              placeholder="e.g. Payments Gateway API"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">GitHub Repository URL</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://github.com/myorg/payments-api"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Production Service URL (Health Probing)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://payments.example.com"
              value={serviceUrl}
              onChange={(e) => setServiceUrl(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Deploy Webhook / Integration URL (Masked)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://api.render.com/deploy/srv-12345?key=..."
              value={deployHookUrl}
              onChange={(e) => setDeployHookUrl(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '0.55rem 1rem' }}>
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn-primary" style={{ padding: '0.55rem 1.25rem' }}>
              {submitting ? 'Connecting...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
