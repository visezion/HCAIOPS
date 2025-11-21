import { apiRequest } from './api';

export async function fetchMetricSummary() {
  const data = await apiRequest('/analytics/summary');
  const metrics = Array.isArray(data) ? data : data?.metrics;
  return metrics || [];
}
