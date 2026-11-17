// DeployEasy Centralized API Client

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
  return match ? decodeURIComponent(match[3]) : null;
}

export function getCsrfToken() {
  return getCookie('deployeasy_csrf') || '';
}

export function getAuthHeaders(includeJson = true) {
  const headers = {};
  if (includeJson) {
    headers['Content-Type'] = 'application/json';
  }
  const csrf = getCsrfToken();
  if (csrf) {
    headers['X-CSRF-Token'] = csrf;
  }
  return headers;
}

export async function apiFetch(url, options = {}) {
  const opts = {
    credentials: 'include',
    ...options,
    headers: {
      ...getAuthHeaders(options.body && typeof options.body === 'string'),
      ...(options.headers || {})
    }
  };

  const res = await fetch(url, opts);
  if (!res.ok) {
    let errorDetail = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch (_) {}
    const err = new Error(errorDetail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  // Auth
  getCurrentUser: () => apiFetch('/api/auth/me'),
  login: (username, password) => apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),
  register: (username, email, password) => apiFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password })
  }),
  demoLogin: () => apiFetch('/api/auth/demo-login', { method: 'POST' }),
  logout: () => apiFetch('/api/auth/logout', { method: 'POST' }),

  // System & Telemetry
  getOverview: () => apiFetch('/api/overview'),
  getSystemMode: () => apiFetch('/api/system/mode'),
  setSystemMode: (mode) => apiFetch('/api/system/mode', {
    method: 'POST',
    body: JSON.stringify({ mode })
  }),
  getMetrics: () => apiFetch('/metrics'),
  getVersion: () => apiFetch('/version'),
  getRuns: () => apiFetch('/api/runs'),

  // Projects
  getProjects: () => apiFetch('/api/projects'),
  createProject: (data) => apiFetch('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getProject: (id) => apiFetch(`/api/projects/${id}`),
  checkGithubRepository: (repoUrl) => apiFetch('/api/github/repository-check', {
    method: 'POST', body: JSON.stringify({ repo_url: repoUrl })
  }),

  // Deployments & Rollback
  getDeployments: (projectId) => apiFetch(`/api/projects/${projectId}/deployments`),
  triggerDeploy: (projectId, data) => apiFetch('/api/deployments/trigger', {
    method: 'POST', body: JSON.stringify({ project_id: projectId, ...data })
  }),
  triggerRollback: (projectId, targetSha, reason) => apiFetch('/api/deployments/rollback', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, target_sha: targetSha, reason })
  }),
  getGitDiff: (deploymentId) => apiFetch(`/api/deployments/${deploymentId}/diff`),

  // Health Probing
  probeHealth: (projectId) => apiFetch(`/api/projects/${projectId}/check-health`, { method: 'POST' }),
  getHealthHistory: (projectId) => apiFetch(`/api/projects/${projectId}/health-history`),

  // Security
  getSecurityScans: (projectId) => apiFetch(`/api/projects/${projectId}/security`),

  // Readiness
  getReadinessScore: (projectId) => apiFetch(`/api/projects/${projectId}/readiness`),

  // Env Validator
  validateEnv: (envText) => {
    const lines = (envText || '').split(/\r?\n/);
    const parsed = {};
    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;
      const idx = line.indexOf('=');
      if (idx > 0) {
        const key = line.slice(0, idx).trim();
        const val = line.slice(idx + 1).trim();
        if (key) parsed[key] = val;
      }
    }
    return apiFetch('/api/validate-env', {
      method: 'POST',
      body: JSON.stringify({ env_vars: parsed })
    });
  },

  // FinOps Cost Estimator
  getCostEstimate: (projectId) => apiFetch(`/api/projects/${projectId}/costs`),

  // Failure Diagnostics & Incidents
  analyzeLogs: (logText) => apiFetch('/api/analyze-logs', {
    method: 'POST',
    body: JSON.stringify({ logs: logText })
  }),
  generateIncidentReport: (projectId, data) => apiFetch(`/api/projects/${projectId}/incidents/generate`, {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  // Webhooks
  testWebhook: (projectId, webhookUrl, platform) => apiFetch(`/api/projects/${projectId}/webhook-test`, {
    method: 'POST',
    body: JSON.stringify({ webhook_url: webhookUrl, platform })
  })
};
