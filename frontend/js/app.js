/**
 * app.js — Two-view SPA (Home → Event)
 * Depends on: window.API, window.HomeMap, window.EventMap,
 *             window.Dashboard, window.AIModal
 */
(function() {
  let homeMap  = null;
  let eventMap = null;
  let darkMode = true;
  let allEvents = [];
  let currentEvent = null;
  let currentWeather = [];   // [{hour, temp_c, rh, wind_speed_kmh, wind_dir}]

  // ── Boot ─────────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', async function() {
    initTheme();
    initAuth();

    homeMap  = new window.HomeMap('home-map', openEvent);
    eventMap = new window.EventMap('event-map');

    // Forecast slider wiring
    document.addEventListener('input', function(e) {
      if (e.target.id === 'fcast-slider') {
        _setForecastHour(+e.target.value);
      }
    });

    window.AIModal.init();
    window.Dashboard.clearDashboard();

    document.getElementById('nav-home-btn').addEventListener('click', goHome);

    allEvents = await loadEvents();
    window.API.getRealtimeFirms().then(function(fc) {
      homeMap.renderFirms(fc);
    }).catch(function() {});
    showView('home');
  });

  // ── Views ─────────────────────────────────────────────────────────────────────

  function showView(name, afterResize) {
    document.getElementById('home-view').classList.toggle('hidden', name !== 'home');
    document.getElementById('event-view').classList.toggle('hidden', name !== 'event');
    document.getElementById('breadcrumb').classList.toggle('hidden', name !== 'event');
    setTimeout(function() {
      if (name === 'home')  homeMap  && homeMap.map.invalidateSize();
      else                  eventMap && eventMap.map.invalidateSize();
      if (afterResize) afterResize();
    }, 60);
  }

  function goHome() {
    currentEvent = null;
    window.Dashboard.clearDashboard();
    window.AIModal.setContext(null, null);
    window.AIModal.close();
    showView('home');
  }

  // ── Events ────────────────────────────────────────────────────────────────────

  async function loadEvents() {
    try {
      const events = await window.API.getEvents();
      homeMap.renderEvents(events);
      renderHomeSidebar(events);
      return events;
    } catch(e) {
      showToast('Failed to load events: ' + e.message);
      return [];
    }
  }

  function renderHomeSidebar(events) {
    const el = document.getElementById('home-event-list');
    if (!el) return;
    if (!events.length) { el.innerHTML = '<div class="empty-msg">No events</div>'; return; }
    el.innerHTML = events.map(function(ev) {
      return '<div class="hs-event-item" data-id="' + ev.id + '">' +
        '<div class="hs-event-name">' + escHtml(ev.name) + '</div>' +
        '<div class="hs-event-meta">' + ev.year + ' · Click to open</div>' +
        '</div>';
    }).join('');
    el.querySelectorAll('.hs-event-item').forEach(function(item) {
      item.addEventListener('click', function() {
        const ev = events.find(function(e) { return String(e.id) === item.dataset.id; });
        if (ev) openEvent(ev);
      });
    });
  }

  async function openEvent(ev) {
    currentEvent = ev;

    document.getElementById('breadcrumb').textContent = ev.name + ' · ' + ev.year;
    document.getElementById('lp-event-name').textContent = ev.name;
    document.getElementById('lp-event-meta').textContent =
      ev.year + ' · ' + fmtDate(ev.start_date) + ' – ' + fmtDate(ev.end_date);

    eventMap.clearLayers();
    showView('event', function() {
      if (ev.bbox) eventMap.fitToBbox(ev.bbox);
      window.API.getAoi(ev.id).then(function(aoi) {
        eventMap.fitToAoi(aoi);
      }).catch(function() {});
    });
    window.Dashboard.clearDashboard();
    window.AIModal.setContext(ev.id, null);

    await loadTimesteps(ev.id);
  }

  // ── Timesteps ─────────────────────────────────────────────────────────────────

  async function loadTimesteps(eventId) {
    const container = document.getElementById('timestep-slider-section');
    container.innerHTML = '<div class="empty-msg">Loading…</div>';

    let timesteps;
    try {
      timesteps = await window.API.getTimesteps(eventId);
    } catch(e) {
      container.innerHTML = '<div class="empty-msg">Failed to load timesteps</div>';
      return;
    }

    const done = timesteps.filter(function(ts) { return ts.prediction_status === 'done'; });
    if (!done.length) {
      container.innerHTML = '<div class="empty-msg">No completed timesteps yet</div>';
      return;
    }

    const tickBar = done.map(function(ts) {
      let cls = ts.spatial_analysis_status === 'done' ? 'full' : 'partial';
      if (ts.data_gap_warn) cls += ' gap';
      return '<div class="ts-tick ' + cls + '" title="' + fmtDateTime(ts.slot_time) + '"></div>';
    }).join('');

    container.innerHTML =
      '<div class="ts-slider-wrap">' +
        '<div class="ts-status-bar">' + tickBar + '</div>' +
        '<input type="range" id="ts-slider" min="0" max="' + (done.length - 1) + '" value="0" step="1">' +
        '<div class="ts-label-row">' +
          '<span id="ts-label">' + fmtDateTime(done[0].slot_time) + '</span>' +
          '<span id="ts-gap-badge" class="ts-gap"></span>' +
        '</div>' +
        '<div class="ts-meta-row">' +
          '<div class="ts-meta-item">' +
            '<span class="ts-meta-lbl">T1 hotspot</span>' +
            '<span class="ts-meta-val" id="ts-t1-label">—</span>' +
          '</div>' +
          '<div class="ts-meta-item">' +
            '<span class="ts-meta-lbl">Sentinel-2</span>' +
            '<span class="ts-meta-val" id="ts-sat-label">—</span>' +
          '</div>' +
        '</div>' +
      '</div>';

    setGapBadge(done[0]);

    var slider = document.getElementById('ts-slider');
    var _tsDebounce = null;
    slider.addEventListener('input', function() {
      const ts = done[+slider.value];
      document.getElementById('ts-label').textContent = fmtDateTime(ts.slot_time);
      setGapBadge(ts);
      clearTimeout(_tsDebounce);
      _tsDebounce = setTimeout(function() { selectTimestep(ts); }, 200);
    });

    selectTimestep(done[0]);
  }

  function setGapBadge(ts) {
    const el = document.getElementById('ts-gap-badge');
    if (el) {
      if (ts.data_gap_warn) {
        el.textContent = '⚠ Gap ' + (ts.gap_hours != null ? ts.gap_hours.toFixed(1) : '?') + 'h';
        el.className   = 'ts-gap warn';
      } else {
        el.textContent = '±' + (ts.gap_hours != null ? ts.gap_hours.toFixed(1) : '?') + 'h';
        el.className   = 'ts-gap ok';
      }
    }
    const t1El = document.getElementById('ts-t1-label');
    if (t1El) t1El.textContent = ts.nearest_t1 ? fmtDateTime(ts.nearest_t1) : '—';
  }

  // ── Forecast Slider ───────────────────────────────────────────────────────────

  function _windArrow(deg) {
    if (deg == null) return '';
    return '<svg width="18" height="18" viewBox="-9 -9 18 18" style="vertical-align:middle;flex-shrink:0">' +
      '<g transform="rotate(' + (deg + 180) + ')">' +
      '<polygon points="0,-6 2.5,3 0,2 -2.5,3" fill="#ff8c00"/>' +
      '</g></svg>';
  }

  function _windDirLabel(deg) {
    if (deg == null) return '';
    return ['N','NE','E','SE','S','SW','W','NW'][Math.round(deg / 45) % 8];
  }

  function _renderFcastWeather(wx) {
    var el = document.getElementById('fcast-weather');
    if (!el) return;
    if (!wx) { el.innerHTML = '<span style="opacity:.4;font-size:10px">No data</span>'; return; }
    el.innerHTML =
      '<div class="fcast-wx-wind">' +
        _windArrow(wx.wind_dir) +
        '<span class="fcast-wx-speed">' + (wx.wind_speed_kmh != null ? wx.wind_speed_kmh.toFixed(0) : '—') + '</span>' +
        '<span class="fcast-wx-unit"> km/h</span>' +
        '<span class="fcast-wx-dir"> ' + _windDirLabel(wx.wind_dir) + '</span>' +
      '</div>' +
      '<div class="fcast-wx-row">' +
        '<span class="fcast-wx-label">Temp</span><span class="fcast-wx-val">' + (wx.temp_c != null ? wx.temp_c.toFixed(1) + ' °C' : '—') + '</span>' +
        '<span class="fcast-wx-label" style="margin-left:8px">RH</span><span class="fcast-wx-val">' + (wx.rh != null ? wx.rh.toFixed(0) + '%' : '—') + '</span>' +
      '</div>';
  }

  function _setForecastHour(h) {
    var badge = document.getElementById('fcast-badge');
    var hlabel = document.getElementById('fcast-h-label');
    if (hlabel) hlabel.textContent = '+' + h + 'h';

    if (badge) {
      if (h <= 2) {
        badge.textContent = 'NOW';
        badge.className = 'fcast-badge now';
      } else if (h <= 5) {
        badge.textContent = '+3h';
        badge.className = 'fcast-badge h3';
      } else if (h <= 11) {
        badge.textContent = '+6h';
        badge.className = 'fcast-badge h6';
      } else {
        badge.textContent = '+12h';
        badge.className = 'fcast-badge h12';
      }
    }

    // Risk zone visibility
    if (eventMap) {
      eventMap.setRiskVisible('3h',  h >= 3  && h <= 5);
      eventMap.setRiskVisible('6h',  h >= 6  && h <= 11);
      eventMap.setRiskVisible('12h', h >= 12);
      eventMap.setWeatherGridHour(h);
    }

    // Weather mini panel
    if (currentWeather && currentWeather.length) {
      var wx = currentWeather.find(function(r) { return r.hour === h; });
      if (!wx) wx = currentWeather.reduce(function(a, b) {
        return Math.abs(b.hour - h) < Math.abs(a.hour - h) ? b : a;
      });
      _renderFcastWeather(wx);
    }
  }

  function _initForecastSlider(weatherData) {
    currentWeather = weatherData || [];
    var section = document.getElementById('fcast-section');
    var titleEl = document.getElementById('fcast-section-title');
    if (section) section.style.display = '';
    if (titleEl) titleEl.style.display = '';
    var slider = document.getElementById('fcast-slider');
    if (slider) { slider.value = 0; }
    _setForecastHour(0);
  }

  function _hideForecastSlider() {
    var section = document.getElementById('fcast-section');
    var titleEl = document.getElementById('fcast-section-title');
    if (section) section.style.display = 'none';
    if (titleEl) titleEl.style.display = 'none';
    currentWeather = [];
  }

  async function selectTimestep(ts) {
    if (!currentEvent) return;
    const eid  = currentEvent.id;
    const tsid = ts.id;

    eventMap.clearLayers();
    _hideForecastSlider();

    // Sentinel-2: find nearest scene, then update tile URL with actual acquired date
    const satEl = document.getElementById('ts-sat-label');
    if (satEl) satEl.textContent = '…';
    if (ts.slot_time) {
      const satDate = ts.slot_time.split('T')[0];
      window.API.getSatelliteScene(eid, satDate).then(function(scene) {
        eventMap.setSatelliteDate(scene.acquired.slice(0, 10));   // date-only for tile URL
        if (satEl) satEl.textContent = scene.acquired
          + (scene.cloud_cover != null ? '  ☁ ' + Math.round(scene.cloud_cover * 100) + '%' : '');
      }).catch(function() {
        eventMap.setSatelliteDate(satDate);          // fallback to slot date
        if (satEl) satEl.textContent = 'N/A';
      });
    }

    // Update AI context (does NOT open modal or load report yet)
    window.AIModal.setContext(eid, tsid);

    // Map layers (non-blocking)
    Promise.allSettled([
      window.API.getPerimeter(eid, tsid),
      window.API.getHotspots(eid, tsid),
      window.API.getRiskZones(eid, tsid),
      window.API.getRoads(eid, tsid),
    ]).then(function(r) {
      if (r[0].status === 'fulfilled') eventMap.renderPerimeter(r[0].value);
      if (r[1].status === 'fulfilled') eventMap.renderHotspots(r[1].value);
      if (r[2].status === 'fulfilled') eventMap.renderRiskZones(r[2].value);
      if (r[3].status === 'fulfilled') eventMap.renderRoads(r[3].value);
    });

    // Dashboard (non-blocking)
    Promise.allSettled([
      window.API.getAnalysis(eid, tsid),
      window.API.getFireContext(eid, tsid),
    ]).then(function(r) {
      window.Dashboard.renderDashboard(
        r[0].status === 'fulfilled' ? r[0].value : null,
        r[1].status === 'fulfilled' ? r[1].value : null,
      );
      window.AIModal.renderCard();
    });

    // Weather forecast + wind field (non-blocking)
    Promise.allSettled([
      window.API.getWeather(eid, tsid),
      window.API.getWindField(eid, tsid),
    ]).then(function(r) {
      var forecast   = r[0].status === 'fulfilled' ? r[0].value : [];
      var windHours  = r[1].status === 'fulfilled' ? r[1].value : [];
      eventMap && eventMap.loadWindField(windHours);
      _initForecastSlider(forecast);
      window.Dashboard.updateWeather(forecast);
    });
  }

  // ── Theme ─────────────────────────────────────────────────────────────────────

  function initTheme() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function() {
      darkMode = !darkMode;
      document.body.classList.toggle('light', !darkMode);
      document.body.classList.toggle('dark',   darkMode);
      btn.innerHTML = darkMode
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
      homeMap  && homeMap.setTheme(darkMode);
      eventMap && eventMap.setTheme(darkMode);
    });
  }

  // ── Auth ──────────────────────────────────────────────────────────────────────

  var authIsLogin = true;

  function initAuth() {
    document.getElementById('auth-login-btn')?.addEventListener('click', function() { showAuthModal(true); });
    document.getElementById('auth-logout-btn')?.addEventListener('click', function() {
      window.API.logout(); updateAuthUI(null); showAuthModal(false);
    });
    document.getElementById('auth-form')?.addEventListener('submit', handleAuth);
    document.getElementById('auth-modal-close')?.addEventListener('click', closeAuthModal);
    document.getElementById('auth-toggle-mode')?.addEventListener('click', function() {
      authIsLogin = !authIsLogin;
      document.getElementById('auth-modal-title').textContent  = authIsLogin ? 'Sign In' : 'Register';
      document.getElementById('auth-submit-btn').textContent    = authIsLogin ? 'Login'   : 'Register';
      document.getElementById('auth-toggle-mode').textContent   = authIsLogin
        ? "Don't have an account? Register" : 'Already have an account? Login';
      document.getElementById('auth-error').textContent = '';
    });
    const token = localStorage.getItem('wf_token');
    if (token) {
      window.API.verifyToken()
        .then(function(d) { updateAuthUI(d.username); })
        .catch(function() { updateAuthUI(null); showAuthModal(false); });
    } else {
      showAuthModal(false);
    }
  }

  // dismissable=true: user clicked Sign In (can close); false: forced on startup (no close btn)
  function showAuthModal(dismissable) {
    const closeBtn = document.getElementById('auth-modal-close');
    if (closeBtn) closeBtn.style.display = dismissable ? '' : 'none';
    document.getElementById('auth-modal-overlay').classList.add('visible');
  }
  function closeAuthModal() { document.getElementById('auth-modal-overlay').classList.remove('visible'); }

  async function handleAuth(e) {
    e.preventDefault();
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    const errEl    = document.getElementById('auth-error');
    errEl.textContent = '';
    try {
      if (authIsLogin) {
        const d = await window.API.login(username, password);
        updateAuthUI(d.username);
      } else {
        await window.API.register(username, password);
        await window.API.login(username, password);
        updateAuthUI(username);
      }
      closeAuthModal();
      // Reload events with new token (firms hotspots also need auth)
      allEvents = await loadEvents();
    } catch(err) {
      errEl.textContent = err.message;
    }
  }

  function updateAuthUI(username) {
    const loginBtn  = document.getElementById('auth-login-btn');
    const logoutBtn = document.getElementById('auth-logout-btn');
    const userLabel = document.getElementById('auth-user-label');
    if (username) {
      loginBtn?.classList.add('hidden');
      logoutBtn?.classList.remove('hidden');
      if (userLabel) userLabel.textContent = username;
    } else {
      loginBtn?.classList.remove('hidden');
      logoutBtn?.classList.add('hidden');
      if (userLabel) userLabel.textContent = '';
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────────

  function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function fmtDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-CA');
  }

  function fmtDateTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-CA') + ' ' +
           d.toLocaleTimeString('en-CA', { hour: '2-digit', minute: '2-digit' });
  }

  function showToast(msg, type) {
    const t = document.createElement('div');
    t.className = 'toast ' + (type || 'error');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function() { t.remove(); }, 4000);
  }
})();
