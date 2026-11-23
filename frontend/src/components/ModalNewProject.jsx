import React, { useEffect, useState } from 'react';
import { api } from '../api';

export function ModalNewProject({ isOpen, onClose, onProjectCreated, project = null, onProjectUpdated }) {
  const [name, setName] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [serviceUrl, setServiceUrl] = useState('');
  const [deployHookUrl, setDeployHookUrl] = useState('');
  const [repositoryCheck, setRepositoryCheck] = useState(null);
  const [checkingRepository, setCheckingRepository] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [deploymentMode, setDeploymentMode] = useState('frontend');
  const [serviceType, setServiceType] = useState('static_site');
  const [runtime, setRuntime] = useState('node');
  const [buildCommand, setBuildCommand] = useState('npm run build');
  const [startCommand, setStartCommand] = useState('npm start');
  const [publishPath, setPublishPath] = useState('dist');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const applyRepoPresets = (urlOrName, mode = deploymentMode) => {
    const lower = (urlOrName || '').toLowerCase();
    if (lower.includes('hisaab')) {
      if (mode === 'frontend') {
        setBuildCommand('npm install && npm run build:web');
        setPublishPath('apps/web/dist/web/browser');
      } else {
        setBuildCommand('npm ci && npm run build:all');
        setStartCommand('node apps/api/dist/main.js');
      }
    } else if (lower.includes('brinhack')) {
      if (mode === 'frontend') {
        setBuildCommand('cd mock && npm install --legacy-peer-deps && CI=false npm run build');
        setPublishPath('mock/build');
      } else {
        setBuildCommand('cd mock && npm install --legacy-peer-deps');
        setStartCommand('npm start --prefix mock');
      }
    } else {
      if (mode === 'frontend') {
        setBuildCommand('npm run build');
        setPublishPath('dist');
      } else {
        setBuildCommand('npm install');
        setStartCommand('npm start');
      }
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    const rName = project?.name || '';
    const rUrl = project ? `https://github.com/${project.repo_name}` : '';
    setName(rName);
    setRepoUrl(rUrl);
    setBranch(project?.branch || 'main');
    setServiceUrl(project?.service_url || '');
    setDeployHookUrl('');
    setDeploymentMode('frontend');
    setServiceType('static_site');
    setRuntime('node');
    applyRepoPresets(project?.repo_name || rUrl, 'frontend');
    setStartCommand('npm start');
    setRepositoryCheck(null);
    setError(null);
  }, [isOpen, project]);

  if (!isOpen) return null;

  const handleCheckRepository = async () => {
    setCheckingRepository(true);
    setError(null);
    try {
      const res = await api.checkGithubRepository(repoUrl);
      setRepositoryCheck(res);
      applyRepoPresets(repoUrl);
    } catch (err) {
      setRepositoryCheck(null);
      setError(err.message || 'Could not check this repository');
    } finally {
      setCheckingRepository(false);
    }
  };

  const selectDeploymentMode = (mode) => {
    setDeploymentMode(mode);
    setServiceType(mode === 'frontend' ? 'static_site' : 'web_service');
    applyRepoPresets(project?.repo_name || repoUrl, mode);
  };

  const handleProvisionRender = async () => {
    if (!project || provisioning) return;
    setProvisioning(true);
    setError(null);
    try {
      const updated = await api.provisionRenderService(project.id, {
        service_type: serviceType,
        runtime,
        region: 'singapore',
        plan: 'free',
        build_command: buildCommand,
        start_command: startCommand,
        publish_path: publishPath
      });
      if (onProjectUpdated) onProjectUpdated(updated);
      onClose();
    } catch (err) {
      setError(err.message || 'Could not create the Render service');
    } finally {
      setProvisioning(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (project) {
        const changes = { name, branch, service_url: serviceUrl.trim() };
        // Keep the stored secret unless the user enters a replacement.
        if (deployHookUrl.trim()) changes.deploy_hook_url = deployHookUrl.trim();
        const updated = await api.updateProject(project.id, changes);
        if (onProjectUpdated) onProjectUpdated(updated);
        onClose();
        return;
      }

      let finalBranch = branch?.trim() || 'main';
      try {
        const checkedRepository = await api.checkGithubRepository(repoUrl);
        if (checkedRepository?.default_branch && (!branch || branch === 'main')) {
          finalBranch = checkedRepository.default_branch;
        }
      } catch (_) {
        // Continue smoothly even if GitHub rate limits or repo check is unavailable
      }

      const created = await api.createProject({
        name,
        repo_url: repoUrl || undefined,
        branch: finalBranch,
        service_url: serviceUrl || undefined,
        deploy_hook_url: deployHookUrl || undefined
      });
      if (onProjectCreated) onProjectCreated(created);
      onClose();
    } catch (err) {
      setError(err.message || (project ? 'Failed to save project settings' : 'Failed to create project'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>{project ? 'Configure Project' : 'Connect New Cloud Project'}</h3>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.25rem', cursor: 'pointer' }} aria-label="Close">
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
            <input type="text" required className="form-input" placeholder="e.g. Payments Gateway API" value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div className="form-group">
            <label className="form-label">GitHub Repository URL</label>
            <input
              type="url"
              required
              readOnly={Boolean(project)}
              className="form-input"
              placeholder="https://github.com/myorg/payments-api"
              value={repoUrl}
              onChange={(e) => { 
                setRepoUrl(e.target.value); 
                applyRepoPresets(e.target.value);
                setRepositoryCheck(null); 
              }}
            />
            {!project && <>
              <button type="button" className="btn-secondary" disabled={checkingRepository || !repoUrl.trim()} onClick={handleCheckRepository} style={{ marginTop: '0.5rem', padding: '0.4rem 0.7rem' }}>
                {checkingRepository ? 'Checking GitHub...' : 'Check repository setup'}
              </button>
              {repositoryCheck && <p style={{ fontSize: '0.78rem', color: repositoryCheck.ready ? '#34d399' : '#fbbf24', marginTop: '0.5rem' }}>
                {repositoryCheck.repo_name} · default branch: {repositoryCheck.default_branch} · repo access {repositoryCheck.token_can_access_repo ? 'verified' : 'public read only'} · pipeline {repositoryCheck.workflows['pipeline.yml'] ? 'found' : 'missing'} · rollback {repositoryCheck.workflows['rollback.yml'] ? 'found' : 'missing'} · verify the token has Actions: write permission
              </p>}
            </>}
          </div>

          <div className="form-group">
            <label className="form-label">Production Branch</label>
            <input type="text" required className="form-input" placeholder="main" value={branch} onChange={(e) => setBranch(e.target.value)} />
          </div>

          <div className="form-group">
            <label className="form-label">Production Service URL (Website Link)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://your-app.onrender.com"
              value={serviceUrl}
              onChange={(e) => setServiceUrl(e.target.value)}
            />
            <p style={{ fontSize: '0.75rem', color: '#38bdf8', marginTop: '0.35rem' }}>
              💡 Live website ka URL dalein — save karte hi table mein click karke seedhe khol sakte hain!
            </p>
          </div>

          <div className="form-group">
            <label className="form-label">Deploy Webhook / Integration URL (Optional)</label>
            {project?.has_deploy_hook && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                Deploy hook saved hai. Change karna ho toh naya link dalein, nahi toh blank chhod dein.
              </p>
            )}
            <input
              type="url"
              className="form-input"
              placeholder="https://api.render.com/deploy/srv-12345?key=..."
              value={deployHookUrl}
              onChange={(e) => setDeployHookUrl(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '0.55rem 1rem' }}>Cancel</button>
            <button type="submit" disabled={submitting} className="btn-primary" style={{ padding: '0.55rem 1.25rem' }}>
              {submitting ? (project ? 'Saving...' : 'Connecting...') : (project ? 'Save Configuration' : 'Connect Service')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
