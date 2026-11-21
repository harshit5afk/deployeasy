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
  const [serviceType, setServiceType] = useState('web_service');
  const [runtime, setRuntime] = useState('node');
  const [buildCommand, setBuildCommand] = useState('npm install');
  const [startCommand, setStartCommand] = useState('npm start');
  const [publishPath, setPublishPath] = useState('dist');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setName(project?.name || '');
    setRepoUrl(project ? `https://github.com/${project.repo_name}` : '');
    setBranch(project?.branch || 'main');
    setServiceUrl(project?.service_url || '');
    setDeployHookUrl('');
    setServiceType('web_service');
    setRuntime('node');
    setBuildCommand('npm install');
    setStartCommand('npm start');
    setPublishPath('dist');
    setRepositoryCheck(null);
    setError(null);
  }, [isOpen, project]);

  if (!isOpen) return null;

  const handleCheckRepository = async () => {
    setCheckingRepository(true);
    setError(null);
    try {
      setRepositoryCheck(await api.checkGithubRepository(repoUrl));
    } catch (err) {
      setRepositoryCheck(null);
      setError(err.message || 'Could not check this repository');
    } finally {
      setCheckingRepository(false);
    }
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

      const checkedRepository = await api.checkGithubRepository(repoUrl);
      const created = await api.createProject({
        name,
        repo_url: repoUrl || undefined,
        branch: branch || checkedRepository.default_branch || 'main',
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
              onChange={(e) => { setRepoUrl(e.target.value); setRepositoryCheck(null); }}
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
            <label className="form-label">Production Service URL (required for deploy verification)</label>
            <input type="url" className="form-input" placeholder="https://payments.example.com" value={serviceUrl} onChange={(e) => setServiceUrl(e.target.value)} />
          </div>

          <div className="form-group">
            <label className="form-label">Deploy Webhook / Integration URL (Secret)</label>
            {project?.has_deploy_hook && <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>A deploy hook is already saved. Leave blank to keep it, or enter a replacement.</p>}
            <input type="url" className="form-input" placeholder="https://api.render.com/deploy/srv-12345?key=..." value={deployHookUrl} onChange={(e) => setDeployHookUrl(e.target.value)} />
          </div>

          {project && !project.render_service_created && !project.service_url && (
            <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px' }}>
              <strong>Create this app on Render</strong>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.45rem 0 0.8rem' }}>
                This creates a new service and starts its first deployment on Render. DeployEasy needs RENDER_API_KEY and RENDER_OWNER_ID in its own Render environment. The free plan is selected; Render may require billing setup. Make sure the repository supports the commands below.
              </p>
              <div className="form-group">
                <label className="form-label">Service type</label>
                <select className="form-input" value={serviceType} onChange={(e) => { setServiceType(e.target.value); setBuildCommand(e.target.value === 'static_site' ? 'npm run build' : 'npm install'); }}>
                  <option value="web_service">Web service (API or server app)</option>
                  <option value="static_site">Static site (built frontend)</option>
                </select>
              </div>
              {serviceType === 'web_service' ? <>
                <div className="form-group">
                  <label className="form-label">Runtime</label>
                  <select className="form-input" value={runtime} onChange={(e) => setRuntime(e.target.value)}>
                    <option value="node">Node.js</option>
                    <option value="python">Python</option>
                    <option value="go">Go</option>
                    <option value="ruby">Ruby</option>
                    <option value="rust">Rust</option>
                    <option value="elixir">Elixir</option>
                    <option value="docker">Dockerfile at repository root</option>
                  </select>
                </div>
                {runtime !== 'docker' && <>
                  <div className="form-group">
                    <label className="form-label">Build command</label>
                    <input className="form-input" value={buildCommand} onChange={(e) => setBuildCommand(e.target.value)} placeholder="npm install" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Start command</label>
                    <input className="form-input" value={startCommand} onChange={(e) => setStartCommand(e.target.value)} placeholder="npm start" />
                  </div>
                </>}
              </> : <>
                <div className="form-group">
                  <label className="form-label">Build command</label>
                  <input className="form-input" value={buildCommand} onChange={(e) => setBuildCommand(e.target.value)} placeholder="npm run build" />
                </div>
                <div className="form-group">
                  <label className="form-label">Publish directory</label>
                  <input className="form-input" value={publishPath} onChange={(e) => setPublishPath(e.target.value)} placeholder="dist" />
                </div>
              </>}
              <button type="button" className="btn-primary" disabled={provisioning} onClick={handleProvisionRender}>
                {provisioning ? 'Creating Render service...' : 'Create free Render service'}
              </button>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '0.55rem 1rem' }}>Cancel</button>
            <button type="submit" disabled={submitting} className="btn-primary" style={{ padding: '0.55rem 1.25rem' }}>
              {submitting ? (project ? 'Saving...' : 'Connecting...') : (project ? 'Save Configuration' : 'Create Project')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
