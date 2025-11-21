import { apiRequest } from './api';

export async function sendControlAction(action) {
  if (!action || !action.type) {
    throw new Error('Action payload requires a type');
  }

  return apiRequest('/control/action', {
    method: 'POST',
    body: action,
  });
}
