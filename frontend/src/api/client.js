const BASE = '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    return
  }

  const data = res.status === 204 ? null : await res.json()
  if (!res.ok) throw new Error(data?.detail || 'Request failed')
  return data
}

export const api = {
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/auth/me'),

  getCandidates: (params = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) qs.set(k, v) })
    return request(`/candidates?${qs}`)
  },
  getCandidate: (id) => request(`/candidates/${id}`),
  createCandidate: (data) =>
    request('/candidates', { method: 'POST', body: JSON.stringify(data) }),
  updateCandidate: (id, data) =>
    request(`/candidates/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCandidate: (id) =>
    request(`/candidates/${id}`, { method: 'DELETE' }),

  submitScore: (candidateId, data) =>
    request(`/candidates/${candidateId}/scores`, { method: 'POST', body: JSON.stringify(data) }),

  triggerSummary: (candidateId, category = 'default') =>
    request(`/candidates/${candidateId}/summary?category=${encodeURIComponent(category)}`, { method: 'POST' }),

  getAllSummaries: (candidateId) =>
    request(`/candidates/${candidateId}/summaries`),
}
