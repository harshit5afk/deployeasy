import React, { useState, useEffect } from 'react';
import { api } from '../../api';

export function TabDeployments({ projects, selectedProject, onSelectProject }) {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [rollbackSha, setRollbackSha] = useState('');
  const [commitSha, setCommitSha] = useState('');
  const [rollbackMsg, setRollbackMsg] = useState(null);

  // Git Diff tool state
  const [baseSha, setBaseSha] = useState('');
  const [headSha, setHeadSha] = useState('');
  const [diffResult, setDiffResult] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const activeProjectId = selectedProject?.id || (projects && projects[0]?.id);
  const currentProject = projects?.find((item) => item.id === activeProjectId) || selectedProject || (projects && projects[0]);

  const getProjectDefaultSha = (p) => {
    if (!p) return '15dbea2e1e6a3220debab16a2ff95da39f5d395f';
    const text = `${p.repo_name || ''} ${p.name || ''}`.toLowerCase();
    if (text.includes('study') || text.includes('brinhack')) {
      return 'b0fdb99b836e9e70d229355854608ad29949f67b';
    }
    if (text.includes('eco') || text.includes('omsing')) {
      return '67bc2e1f78ce16aba4ea4795cd3a8eaae2a611cb';
    }
    if (text.includes('hisaab')) {
      return '15dbea2e1e6a3220debab16a2ff95da39f5d395f';
    }
    if (deployments && deployments.length > 0 && deployments[0].commit_sha) {
      return deployments[0].commit_sha;
    }
    return '15dbea2e1e6a3220debab16a2ff95da39f5d395f';
  };

  useEffect(() => {
    if (currentProject) {
      setCommitSha(getProjectDefaultSha(currentProject));
    }
  }, [activeProjectId]);

  const loadDeployments = async (pId, silent = false) => {
    if (!pId) return;
    if (!silent) setLoading(true);
    try {
      const data = await api.getDeployments(pId);
      setDeployments(data);
      if (data && data.length >= 2) {
        setBaseSha(data[1].commit_sha);
        setHeadSha(data[0].commit_sha);
      } else if (data && data.length === 1) {
        setBaseSha(data[0].commit_sha);
        setHeadSha(data[0].commit_sha);
      }
    } catch (e) {
      console.error(e);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    if (activeProjectId) {
      loadDeployments(activeProjectId);
    }
  }, [activeProjectId]);

  useEffect(() => {
    if (!activeProjectId) return undefined;
    const timer = setInterval(() => loadDeployments(activeProjectId, true), 8000);
    return () => clearInterval(timer);
  }, [activeProjectId]);

  const handleTriggerDeploy = async () => {
    if (!activeProjectId) return;
    const sha = commitSha.trim().toLowerCase();
    if (!/^[0-9a-f]{7,40}$/.test(sha)) {
      alert('Enter a valid commit SHA (at least 7 hexadecimal characters, e.g. 15dbea2...).');
      return;
    }
    const project = projects.find((item) => item.id === activeProjectId);
    setDeploying(true);
    try {
      await api.triggerDeploy(activeProjectId, { commit_sha: sha, branch: project?.branch || 'main' });
      await loadDeployments(activeProjectId);
    } catch (err) {
      alert(err.message || 'Deploy failed');
    } finally {
      setDeploying(false);
    }
  };

  const handleRollback = async (sha) => {
    if (!activeProjectId || !sha) return;
    if (!confirm(`Are you sure you want to rollback to commit ${sha.substring(0, 8)}?`)) return;
    setRollbackMsg({ type: 'info', text: `Initiating rollback to ${sha.substring(0, 8)}...` });
    try {
      const res = await api.triggerRollback(activeProjectId, sha);
      setRollbackMsg({
        type: res.status === 'rolled_back' ? 'success' : 'info',
        text: `Rollback triggered. Status: ${res.status}. Target SHA: ${res.commit_sha.substring(0, 8)}`
      });
      await loadDeployments(activeProjectId);
    } catch (err) {
      setRollbackMsg({ type: 'error', text: err.message || 'Rollback failed' });
    }
  };

  const handleCompareDiff = async () => {
    if (!activeProjectId) return;
    setDiffLoading(true);
    setDiffResult(null);
    try {
      const deployment = deployments.find((item) => item.commit_sha === headSha || item.commit_sha?.startsWith(headSha)) || deployments[0];
      if (!deployment) throw new Error('No recorded deployment found for comparison.');
      const res = await api.getGitDiff(deployment.id);
      setDiffResult(res);
    } catch (err) {
      alert(err.message || 'Failed to fetch diff');
    } finally {
      setDiffLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return <span className="badge-status badge-success">✓ SUCCESS</span>;
      case 'failure':
        return <span className="badge-status badge-failed">✕ FAILED</span>;
      case 'rolled_back':
        return <span className="badge-status badge-rolled-back">⏪ ROLLED BACK</span>;
      default:
        return <span className="badge-status badge-deploying">⏳ {status?.toUpperCase()}</span>;
    }
  };

  return (
    <div>
      {/* Controls Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '1rem 1.5rem', borderRadius: '14px', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-muted)' }}>Project:</label>
          <select
            className="form-input"
            style={{ width: '220px', padding: '0.45rem 0.75rem' }}
            value={activeProjectId || ''}
            onChange={(e) => {
              const p = projects.find((x) => x.id === parseInt(e.target.value));
              if (p && onSelectProject) onSelectProject(p);
            }}
          >
            {projects && projects.map((p) => (
              <option key={p.id} value={p.id} style={{ background: '#111522' }}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={() => loadDeployments(activeProjectId)}
            className="btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
          >
            ↻ Refresh Feed
          </button>
          <button
            onClick={handleTriggerDeploy}
            disabled={deploying}
            className="btn-primary"
            style={{ padding: '0.45rem 1rem', fontSize: '0.82rem' }}
          >
            {deploying ? 'Deploying...' : '🚀 Trigger Deploy'}
          </button>
        </div>
      </div>

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.65rem', alignItems: 'center' }}>
        <input
          className="form-input"
          value={commitSha}
          onChange={(e) => setCommitSha(e.target.value)}
          placeholder={`Enter commit SHA for ${currentProject?.name || 'project'} (e.g. ${getProjectDefaultSha(currentProject).slice(0, 7)}...)`}
          aria-label="Commit SHA to deploy"
          style={{ flex: 1 }}
        />
        <button
          type="button"
          onClick={() => setCommitSha(getProjectDefaultSha(currentProject))}
          className="btn-secondary"
          style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem', whiteSpace: 'nowrap' }}
          title={`Auto-fill latest commit SHA for ${currentProject?.name || 'selected project'}`}
        >
          ⚡ Use latest {currentProject?.name || 'project'} SHA
        </button>
      </div>

      {rollbackMsg && (
        <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.84rem', background: rollbackMsg.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)', border: rollbackMsg.type === 'error' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)', color: rollbackMsg.type === 'error' ? '#fca5a5' : '#34d399' }}>
          {rollbackMsg.text}
        </div>
      )}

      {/* Deployment Feed (Section A) */}
      <div className="card-table-wrapper">
        <div className="table-header-bar">
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Deployment Feed & Verification History</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Immutable release log tracking commit SHAs, test durations, and zero-downtime rollbacks</p>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            {deployments.length} releases
          </span>
        </div>

        {deployments.some((item) => ['queued', 'deploying'].includes(item.status)) && <div style={{ padding: '0.65rem 1.25rem', color: '#fbbf24', fontSize: '0.82rem' }}>
          Deployment in progress · refreshing status from GitHub every 8 seconds
        </div>}

        <table className="custom-table">
          <thead>
            <tr>
              <th>Release #</th>
              <th>Commit SHA</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Deployed At</th>
              <th>Workflow</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  Loading deployments...
                </td>
              </tr>
            ) : deployments.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No deployment history found. Trigger your first release above!
                </td>
              </tr>
            ) : (
              deployments.map((d, idx) => (
                <tr key={d.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                    #{String(deployments.length - idx).padStart(2, '0')}
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', background: 'rgba(255,255,255,0.06)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem', color: '#c7d2fe' }}>
                      {d.commit_sha ? d.commit_sha.substring(0, 8) : 'unknown'}
                    </span>
                  </td>
                  <td>{getStatusBadge(d.status)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {d.duration_seconds ? `${d.duration_seconds}s` : '—'}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {d.created_at ? new Date(d.created_at).toLocaleTimeString() : 'Recent'}
                  </td>
                  <td>
                    {d.workflow_run_id && (() => {
                      const project = projects.find((item) => item.id === d.project_id);
                      return project ? <a href={`https://github.com/${project.repo_name}/actions/runs/${d.workflow_run_id}`} target="_blank" rel="noreferrer">View Actions run</a> : 'GitHub Actions';
                    })()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <details style={{ textAlign: 'left', marginBottom: d.status === 'success' ? '0.4rem' : 0 }}>
                      <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.75rem' }}>Activity</summary>
                      <pre style={{ whiteSpace: 'pre-wrap', maxWidth: '340px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>{d.logs_summary || 'No activity details recorded yet.'}</pre>
                    </details>
                    {d.status === 'success' && (
                      <button
                        onClick={() => handleRollback(d.commit_sha)}
                        className="btn-secondary"
                        style={{ padding: '0.28rem 0.65rem', fontSize: '0.75rem', borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24' }}
                      >
                        ⏪ Rollback
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Git Commit Diff Tool (Section B) */}
      <div className="telemetry-card" style={{ marginTop: '1.5rem' }}>
        <div className="telemetry-header">
          <div className="telemetry-title">
            <span>🔀</span> Git Commit Diff & Change Inspector
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Compare any two releases to audit introduced code and changed files
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1rem', alignItems: 'flex-end', marginBottom: '1.25rem' }}>
          <div>
            <label className="form-label">Base Commit SHA (Previous)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. 7384668..."
              value={baseSha}
              onChange={(e) => setBaseSha(e.target.value)}
            />
          </div>
          <div>
            <label className="form-label">Head Commit SHA (New / Target)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. f1996ee..."
              value={headSha}
              onChange={(e) => setHeadSha(e.target.value)}
            />
          </div>
          <button
            onClick={handleCompareDiff}
            disabled={diffLoading || !baseSha || !headSha}
            className="btn-primary"
            style={{ padding: '0.65rem 1.25rem', height: '40px' }}
          >
            {diffLoading ? 'Analyzing...' : 'Compare Commits'}
          </button>
        </div>

        {diffResult && (
          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: '10px', padding: '1rem', marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 700, color: '#34d399' }}>
                {diffResult.diff_summary} · {diffResult.status}
              </span>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {diffResult.trigger_type} · duration change {diffResult.duration_difference}s
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Previous {diffResult.previous_sha} → Current {diffResult.current_sha}</div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
