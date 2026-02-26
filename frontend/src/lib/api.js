const API_BASE = 'http://localhost:8000';

export const api = {
  base: API_BASE,
  upload: `${API_BASE}/upload-video`,
  meetings: `${API_BASE}/meetings`,
  transcribe: (id) => `${API_BASE}/transcribe/${id}`,
  meeting: (id) => `${API_BASE}/meeting/${id}`,
  summarize: (id) => `${API_BASE}/summarize/${id}`,
  speakerMap: (id) => `${API_BASE}/meeting/${id}/speaker-map`,
  actionItems: (id) => `${API_BASE}/meeting/${id}/action-items`,
  autoTitle: (id) => `${API_BASE}/meeting/${id}/auto-title`,
  followupEmail: (id) => `${API_BASE}/meeting/${id}/followup-email`,
  requirements: (id) => `${API_BASE}/meeting/${id}/requirements`,
  documentation: (id) => `${API_BASE}/meeting/${id}/documentation`,
  sentiment: (id) => `${API_BASE}/meeting/${id}/sentiment`,
  speakerAnalytics: (id) => `${API_BASE}/meeting/${id}/speaker-analytics`,
  keywords: (id) => `${API_BASE}/meeting/${id}/keywords`,
  topics: (id) => `${API_BASE}/meeting/${id}/topics`,
  stats: `${API_BASE}/stats`,
  cultureScore: `${API_BASE}/stats/culture-score`,
  search: (q) => `${API_BASE}/search?q=${encodeURIComponent(q)}`,
  jiraStatus: `${API_BASE}/jira/status`,
  jiraPush: (id) => `${API_BASE}/meeting/${id}/jira/push`,
  jiraSync: (id) => `${API_BASE}/meeting/${id}/jira/sync`,
  jiraUpdate: (id) => `${API_BASE}/meeting/${id}/jira/update`,
  publish: (id) => `${API_BASE}/publish/${id}`,
  publishPdf: (id) => `${API_BASE}/publish/${id}/pdf`,
  fullReport: (id) => `${API_BASE}/publish/${id}/full-report`,
  chat: {
    ask: `${API_BASE}/chat/ask/stream`,
    meetings: `${API_BASE}/chat/meetings`,
    index: (id) => `${API_BASE}/chat/index/${id}`,
    clear: (id) => `${API_BASE}/chat/clear/${id}`,
  },
};

/** Helper for GET requests */
export async function get(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw new Error(`GET ${url}: ${res.status}`);
  return res.json();
}

/** Helper for POST requests */
export async function post(url, body = null, timeout = 60000) {
  const opts = {
    method: 'POST',
    signal: AbortSignal.timeout(timeout),
  };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `POST ${url}: ${res.status}`);
  }
  return res.json();
}

/** Helper for PUT requests */
export async function put(url, body) {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `PUT ${url}: ${res.status}`);
  }
  return res.json();
}
