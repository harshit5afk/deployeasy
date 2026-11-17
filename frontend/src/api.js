// DeployEasy Centralized API Client

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
  return match ? decodeURIComponent(match[3]) : null;
}

export function getCsrfToken() {
  return getCookie('csrf_token') || '';
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
  getOverview: () => apiFetch('/api/system/overview'),
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

  // Deployments & Rollback
  getDeployments: (projectId) => apiFetch(`/api/projects/${projectId}/deployments`),
  triggerDeploy: (projectId) => apiFetch(`/api/projects/${projectId}/deploy`, { method: 'POST' }),
  triggerRollback: (projectId, targetSha) => apiFetch(`/api/projects/${projectId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ target_sha: targetSha })
  }),
  getGitDiff: (projectId, baseSha, headSha) =>
    apiFetch(`/api/projects/${projectId}/diff?base_sha=${encodeURIComponent(baseSha)}&head_sha=${encodeURIComponent(headSha)}`),

  // Health Probing
  probeHealth: (projectId) => apiFetch(`/api/projects/${projectId}/health-check`, { method: 'POST' }),
  getHealthHistory: (projectId) => apiFetch(`/api/projects/${projectId}/health-history`),

  // Security
  getSecurityScans: (projectId) => apiFetch(`/api/projects/${projectId}/security-scans`),

  // Readiness
  getReadinessScore: (projectId) => apiFetch(`/api/projects/${projectId}/readiness-score`),

  // Env Validator
  validateEnv: (envText) => apiFetch('/api/tools/validate-env', {
    method: 'POST',
    body: JSON.stringify({ env_text: envText })
  }),

  // FinOps Cost Estimator
  getCostEstimate: (projectId) => apiFetch(`/api/projects/${projectId}/costs`),

  // Failure Diagnostics & Incidents
  analyzeLogs: (logText) => apiFetch('/api/tools/analyze-logs', {
    method: 'POST',
    body: JSON.stringify({ log_text: logText })
  }),
  generateIncidentReport: (projectId, data) => apiFetch(`/api/projects/${projectId}/incident-report`, {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  // Webhooks
  testWebhook: (webhookUrl, eventType, payload) => apiFetch('/api/tools/test-webhook', {
    method: 'POST',
    body: JSON.stringify({ webhook_url: webhookUrl, event_type: eventType, payload })
  })
};
