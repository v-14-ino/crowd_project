const rawApiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.replace(/\/+$/, '');

export function getAuthToken() {
  return localStorage.getItem('token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export async function loginUser(email, password) {
  const url = `${API_BASE_URL}/api/auth/login`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  
  const body = await response.json().catch(() => null);
  if (!response.ok) throw body || new Error(`API responded with ${response.status}`);
  
  setAuthToken(body.access_token);
  return body;
}

export async function fetchHealthStatus() {
  const url = `${API_BASE_URL}/health`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API responded with ${response.status}`);
  }

  return response.json();
}

export async function postReport(reportData) {
  const url = `${API_BASE_URL}/api/reports`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(reportData),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchIncidentStats() {
  const url = `${API_BASE_URL}/api/incidents/stats`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchIncidents(params = {}) {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page);
  if (params.pageSize) query.append('page_size', params.pageSize);
  if (params.category && params.category !== 'All') query.append('category', params.category);
  if (params.status && params.status !== 'All') query.append('status', params.status);
  if (params.priorityLevel && params.priorityLevel !== 'All') query.append('priority_level', params.priorityLevel);
  if (params.confidenceLevel && params.confidenceLevel !== 'All') query.append('confidence_level', params.confidenceLevel);
  if (params.freshness && params.freshness !== 'All') query.append('freshness', params.freshness);
  if (params.zone && params.zone !== 'All') query.append('zone', params.zone);
  if (params.search && params.search.trim()) query.append('search', params.search.trim());

  const queryString = query.toString();
  const url = `${API_BASE_URL}/api/incidents${queryString ? `?${queryString}` : ''}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchIncident(incidentId) {
  const url = `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchIncidentReports(incidentId) {
  const url = `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/reports`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function uploadEvidence(incidentId, data) {
  const url = `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/evidence`;
  let options = {};

  if (data instanceof FormData) {
    options = {
      method: 'POST',
      body: data,
    };
  } else {
    options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    };
  }

  const response = await fetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchIncidentEvidence(incidentId) {
  const url = `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/evidence`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function deleteEvidence(evidenceId) {
  const url = `${API_BASE_URL}/api/evidence/${encodeURIComponent(evidenceId)}`;
  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchReport(reportId) {
  const url = `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function fetchRecentReports(limit = 10) {
  const url = `${API_BASE_URL}/api/reports/recent?limit=${encodeURIComponent(limit)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}

export async function submitResponderVerification(incidentId, decisionData) {
  const url = `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/verification`;
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(decisionData),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw body || new Error(`API responded with ${response.status}`);
  }
  return body;
}