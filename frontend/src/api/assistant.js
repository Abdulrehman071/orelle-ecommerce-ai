import axios from 'axios';

// The AI assistant is a SEPARATE service (FastAPI). It receives the same login token as the shop API.
export const ASSISTANT_URL = import.meta.env.VITE_ASSISTANT_URL || 'http://localhost:8001';

const client = axios.create({ baseURL: ASSISTANT_URL, timeout: 60000 });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

export const assistantApi = {
  me: () => client.get('/me'),
  chat: (message, history = []) => client.post('/chat', { message, history }),
  history: (limit = 30) => client.get('/history', { params: { limit } }),
  drafts: (params = {}) => client.get('/drafts', { params }),
  editDraft: (id, body) => client.patch(`/drafts/${id}`, body),
  approveDraft: (id, acknowledge_warnings = false) => client.post(`/drafts/${id}/approve`, { acknowledge_warnings }),
  rejectDraft: (id, note = '') => client.post(`/drafts/${id}/reject`, { note }),
};

export function assistantError(err) {
  const s = err?.response?.status;
  if (!err?.response) return 'Cannot reach the assistant service. Please check that it is running and try again.';
  if (s === 401) return 'Your login session is no longer valid. Please log in again.';
  if (s === 403) return 'You do not have access to this.';
  if (s === 429) return 'Too many requests - please wait a moment and try again.';
  const d = err.response.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return 'Something went wrong. Please try again.';
}
