import { apiRequest } from './api';

export async function fetchEvents() {
  const data = await apiRequest('/ingest/events');
  return Array.isArray(data) ? data : data?.events || [];
}
