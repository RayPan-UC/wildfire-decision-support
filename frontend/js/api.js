/**
 * api.js — Wildfire Decision Support API client (no ES modules)
 * Exposes: window.API
 */
(function() {
  const API_BASE = 'http://localhost:5000';

  function _headers() {
    const token = localStorage.getItem('wf_token');
    const h = { 'Content-Type': 'application/json' };
    if (token) h['Authorization'] = 'Bearer ' + token;
    return h;
  }

  async function apiFetch(path, opts = {}) {
    const res = await fetch(API_BASE + path, { headers: _headers(), ...opts });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || 'HTTP ' + res.status);
    }
    return res.json();
  }

  window.API = {
    BASE: API_BASE,

    async login(username, password) {
      const data = await apiFetch('/api/auth/login', {
        method: 'POST', body: JSON.stringify({ username, password }),
      });
      if (data.token) localStorage.setItem('wf_token', data.token);
      return data;
    },

    async register(username, password) {
      return apiFetch('/api/auth/register', {
        method: 'POST', body: JSON.stringify({ username, password }),
      });
    },

    async verifyToken() { return apiFetch('/api/auth/verify'); },
    logout() { localStorage.removeItem('wf_token'); },

    async getEvents()        { return apiFetch('/api/events/'); },
    async getAoi(eid)        { return apiFetch('/api/events/' + eid + '/layers/aoi'); },
    async getRealtimeFirms(hours) { return apiFetch('/api/firms/realtime' + (hours ? '?hours=' + hours : '')); },
    async getEvent(id)       { return apiFetch('/api/events/' + id); },
    async getTimesteps(id)   { return apiFetch('/api/events/' + id + '/timesteps'); },

    async getPerimeter(eid, tsid)  { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/perimeter'); },
    async getHotspots(eid, tsid)   { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/hotspots'); },
    async getRiskZones(eid, tsid)  { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/risk-zones'); },
    async getRoads(eid, tsid)      { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/roads'); },
    async getAnalysis(eid, tsid)   { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/population'); },
    async getFireContext(eid, tsid){ return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/fire-context'); },
    async getWeather(eid, tsid)   { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/weather'); },
    async getWindField(eid, tsid) { return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/wind-field'); },

    async getSatelliteScene(eid, date) {
      return apiFetch('/api/satellite/scene?event_id=' + eid + '&date=' + date);
    },

    async generateReport(eid, tsid) {
      return apiFetch('/api/events/' + eid + '/timesteps/' + tsid + '/report', { method: 'POST' });
    },

    streamChat(eventId, payload, onChunk, onDone, onError) {
      const controller = new AbortController();
      fetch(API_BASE + '/api/events/' + eventId + '/chat', {
        method: 'POST', headers: _headers(),
        body: JSON.stringify(payload), signal: controller.signal,
      }).then(async res => {
        if (!res.ok) {
          const e = await res.json().catch(() => ({ error: res.statusText }));
          onError(e.error || 'HTTP ' + res.status);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let done = false;
        while (!done) {
          const { value, done: d } = await reader.read();
          done = d;
          if (value) onChunk(decoder.decode(value));
        }
        onDone();
      }).catch(err => { if (err.name !== 'AbortError') onError(err.message); });
      return controller;
    },
  };
})();
