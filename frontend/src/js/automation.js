import { apiRequest } from './api';

export async function runAutomationJob(payload) {
  return apiRequest('/automation/run-job', {
    method: 'POST',
    body: payload,
  });
}

export async function fetchAutomationJobs() {
  const data = await apiRequest('/automation/jobs');
  return Array.isArray(data) ? data : data?.jobs || [];
}
