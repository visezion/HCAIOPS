import { apiRequest } from './api';

export async function fetchAnomalies() {
  const data = await apiRequest('/intelligence/anomalies');
  return Array.isArray(data) ? data : data?.anomalies || [];
}
