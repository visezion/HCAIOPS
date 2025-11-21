const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '';

// FastAPI is mounted at root ("/"); allow overriding through Vite env when bundled.
const baseUrl = API_BASE || '';

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
export const getMetricsSummary = () => get('/analytics/summary');
export const getRecentEvents = (minutes = 180) => get(`/analytics/timeseries?minutes=${minutes}`);
export const getLogAnomalies = () => get('/analytics/anomalies');
export const getCorrelations = () => get('/analytics/correlations');

export const getIntelligenceOverview = () => get('/intelligence/overview');
export const getIntelligenceRisk = () => get('/intelligence/risk');
export const getIntelligenceIncidents = () => get('/intelligence/incidents');
export const getIntelligenceRecommendations = () => get('/intelligence/recommendations');

export const getControlPlan = () => get('/control/plan');
export const sendControlAction = (payload = {}) => post('/control/execute', payload);

// Automation: leverage control plan/actions as playbooks
export const getAutomationJobs = () => getControlPlan();
export const triggerAutomationJob = (payload = { dry_run: false }) => post('/control/execute', payload);

// Agents derived from intelligence risk map
export const getAgentsStatus = () => get('/intelligence/risk');
