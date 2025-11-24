const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '';
const RUNTIME_BASE =
  (typeof window !== 'undefined' && window && (window.HCAI_API_BASE || window.__HCAI_API_BASE__)) || '';

const normalizeBase = (url) => {
  if (!url) return '';
  return url.endsWith('/') ? url.slice(0, -1) : url;
};

const deriveBaseFromLocation = () => {
  if (typeof window === 'undefined' || !window.location) return '';
  const { origin, port, hostname } = window.location;
  if (port === '5173') return 'http://localhost:8000';
  if (origin && origin !== 'null' && !origin.startsWith('file://')) return origin;
  if (hostname === 'hcaiops.vicezion.com') return 'https://hcaiops.vicezion.com';
  return '';
};

// FastAPI is mounted at root ("/"); allow overriding through Vite env, a global at runtime, or location.
const baseUrl = normalizeBase(API_BASE || RUNTIME_BASE || deriveBaseFromLocation() || 'https://hcaiops.vicezion.com');

async function request(method, path, { body, headers, ...options } = {}) {
  const url = `${baseUrl}${path}`;
  const init = {
    method,
    headers: {
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    ...options,
  };

  const res = await fetch(url, init);
  const text = await res.text();
  const payload = text ? safeJson(text, path) : null;

  if (!res.ok) {
    const message = payload?.detail || payload?.message || payload?.error || res.statusText || 'Request failed';
    const error = new Error(message);
    error.status = res.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function safeJson(text, path) {
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`Invalid JSON from ${path}: ${text}`);
  }
}

export const get = (path, options) => request('GET', path, options);
export const post = (path, body, options) => request('POST', path, { ...options, body });

// Real endpoint helpers based on FastAPI routers
export const getMetricsSummary = () => get('/api/analytics/metrics/summary');
export const getRecentEvents = (minutes = 180) => get(`/api/events/recent?limit=${minutes}`);
export const getRecentLogs = (limit = 200) => get(`/api/logs/recent?limit=${limit}`);
export const getLogAnomalies = () => get('/api/analytics/anomalies');
export const getCorrelations = () => get('/api/analytics/correlations');

export const getIntelligenceOverview = () => get('/api/intelligence/overview');
export const getIntelligenceRisk = () => get('/api/intelligence/risk');
export const getIntelligenceIncidents = () => get('/api/intelligence/incidents');
export const getIntelligenceRecommendations = () => get('/api/intelligence/recommendations');

export const getControlPlan = () => get('/api/control/plan');
export const sendControlAction = (payload = {}) => post('/api/control/execute', payload);
export const submitFeedback = (payload = {}) => post('/api/feedback', payload);

// Automation: leverage control plan/actions as playbooks
export const getAutomationJobs = () => getControlPlan();
export const triggerAutomationJob = (payload = { dry_run: false }) => post('/control/execute', payload);

// Agents derived from intelligence risk map
export const getAgentsStatus = () => get('/api/agents');
