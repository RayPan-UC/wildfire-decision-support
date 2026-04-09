/**
 * chat.js — AI Copilot modal (report + chat)
 * Exposes: window.AIModal
 *
 * Flow:
 *   app.js calls AIModal.setContext(eid, tsid) on every timestep select.
 *   User clicks "🤖 AI Analysis" button → AIModal.open():
 *     - if cached report exists  → renders immediately
 *     - if not               → calls POST /report (generates + caches) then renders
 *   Chat is always live (streaming) inside the same modal.
 */
(function() {
  let _eid = null;
  let _tsid = null;
  let _history = [];
  let _streaming = false;
  let _reportLoaded = false;  // has the current tsid been rendered?
  let _cardState = 'idle';    // 'idle' | 'loading' | 'done'
  let _genId = 0;             // generation counter to discard stale responses

  const INITIAL_QUESTIONS = [
    'What are the immediate evacuation priorities?',
    'Which roads are at highest risk in the next 6 hours?',
    'How many people are in the current risk zone?',
    'What weather conditions are driving fire spread?',
    'What is the overall fire danger level right now?',
  ];

  // ── Public API ───────────────────────────────────────────────────────────────

  function init() {
    document.getElementById('ai-modal-close').addEventListener('click', close);
    document.getElementById('ai-modal-overlay').addEventListener('click', function(e) {
      if (e.target === document.getElementById('ai-modal-overlay')) close();
    });
    document.getElementById('chat-send-btn').addEventListener('click', _send);
    document.getElementById('chat-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _send(); }
    });
  }

  /** Called by app.js whenever a new timestep is selected. */
  function setContext(eid, tsid) {
    const changed = (eid !== _eid || tsid !== _tsid);
    _eid  = eid;
    _tsid = tsid;
    if (changed) {
      _reportLoaded = false;
      _cardState = 'idle';
      _history = [];
      _clearChat();
    }
    // Update badge whether modal is open or not
    const badge = document.getElementById('ai-modal-badge');
    if (badge) badge.textContent = (eid && tsid) ? 'Event ' + eid + ' · TS ' + tsid : '';
  }

  /** Open the modal. Only opens when a report has already been generated. */
  function open() {
    if (!_eid || !_tsid || !_reportLoaded) return;
    document.getElementById('ai-modal-overlay').classList.add('visible');
  }

  // ── AI Analysis card ─────────────────────────────────────────────────────────

  /** Append AI Analysis card to #dashboard-content (call after renderDashboard). */
  function renderCard() {
    const content = document.getElementById('dashboard-content');
    if (!content || !_eid || !_tsid) return;
    const existing = document.getElementById('dash-ai-card');
    if (existing) existing.remove();

    const card = document.createElement('div');
    card.className = 'dash-card dash-card-ai';
    card.id = 'dash-ai-card';
    card.innerHTML =
      '<div class="dash-card-title">AI Analysis</div>' +
      '<div class="ai-card-body" id="ai-card-body"></div>';
    content.appendChild(card);
    _updateCard();
    card.addEventListener('click', _onCardClick);
  }

  function _updateCard() {
    const body = document.getElementById('ai-card-body');
    if (!body) return;
    if (_cardState === 'idle') {
      body.className = 'ai-card-body idle';
      body.innerHTML = '<div class="ai-card-prompt">Generate AI report</div>';
    } else if (_cardState === 'loading') {
      body.className = 'ai-card-body loading';
      body.innerHTML = '<div class="spinner-sm"></div><div class="ai-card-status">Generating…</div>';
    } else if (_cardState === 'done') {
      body.className = 'ai-card-body done';
      body.innerHTML = '<div class="ai-card-ready">Report ready</div><div class="ai-card-view">Click to view →</div>';
    }
  }

  function _onCardClick() {
    if (_cardState === 'idle') _startGenerate();
    else if (_cardState === 'done') open();
    // loading: ignore
  }

  async function _startGenerate() {
    if (!_eid || !_tsid) return;
    _cardState = 'loading';
    _updateCard();
    const myGenId = ++_genId;
    try {
      const report = await window.API.generateReport(_eid, _tsid);
      if (myGenId !== _genId) return;
      _renderReport(report);
      _reportLoaded = true;
      _renderInitialSuggestions();
      _cardState = 'done';
      _updateCard();
      _showAIToast();
    } catch(e) {
      if (myGenId !== _genId) return;
      _cardState = 'idle';
      _updateCard();
      const t = document.createElement('div');
      t.className = 'toast error';
      t.textContent = 'AI analysis failed: ' + _escHtml(e.message);
      document.body.appendChild(t);
      setTimeout(function() { t.remove(); }, 4000);
    }
  }

  function _showAIToast() {
    const existing = document.getElementById('ai-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'ai-toast';
    toast.id = 'ai-toast';
    toast.innerHTML = '<span class="ai-toast-msg">AI Analysis ready</span><span class="ai-toast-action">View →</span>';
    toast.addEventListener('click', function() {
      open();
      toast.remove();
    });
    document.body.appendChild(toast);
    setTimeout(function() {
      toast.classList.add('dismissing');
      setTimeout(function() { if (toast.parentNode) toast.remove(); }, 400);
    }, 6000);
  }

  function close() {
    document.getElementById('ai-modal-overlay').classList.remove('visible');
  }

  // ── Report ───────────────────────────────────────────────────────────────────

  async function _loadReport() {
    _showLoading(true);
    try {
      const report = await window.API.generateReport(_eid, _tsid);
      _renderReport(report);
      _reportLoaded = true;
      _renderInitialSuggestions();
    } catch(e) {
      _showLoading(false);
      document.getElementById('ai-report-loading').innerHTML =
        '<div style="padding:20px;color:var(--danger);font-size:12px">Failed: ' + _escHtml(e.message) + '</div>';
    }
  }

  function _showLoading(on) {
    document.getElementById('ai-report-loading').classList.toggle('hidden', !on);
    document.getElementById('ai-report-ready').classList.toggle('hidden', on);
  }

  function _renderReport(report) {
    const tabs = [
      { id: 'overview',   label: 'Overview',   key: 'situation_overview' },
      { id: 'risk',       label: 'Risk',       key: 'risk_analysis' },
      { id: 'impact',     label: 'Impact',     key: 'impact_analysis' },
      { id: 'evacuation', label: 'Evacuation', key: 'evacuation_analysis' },
    ];

    const tabsEl   = document.getElementById('ai-report-tabs');
    const panelsEl = document.getElementById('ai-report-panels');

    tabsEl.innerHTML = tabs.map(function(t, i) {
      return '<button class="report-tab' + (i === 0 ? ' active' : '') + '" data-tab="' + t.id + '">' + t.label + '</button>';
    }).join('');

    panelsEl.innerHTML = tabs.map(function(t, i) {
      let content;
      if (t.id === 'overview') {
        content = _renderOverviewPanel(report);
      } else {
        content = report[t.key]
          ? '<div class="report-section-card"><div class="report-text">' + _fmt(report[t.key]) + '</div></div>'
          : '<div class="report-na">Not available</div>';
      }
      return '<div class="report-panel' + (i === 0 ? ' active' : '') + '" id="panel-' + t.id + '">' + content + '</div>';
    }).join('');

    tabsEl.querySelectorAll('.report-tab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        tabsEl.querySelectorAll('.report-tab').forEach(function(b) { b.classList.remove('active'); });
        panelsEl.querySelectorAll('.report-panel').forEach(function(p) { p.classList.remove('active'); });
        btn.classList.add('active');
        document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
      });
    });

    _showLoading(false);
  }

  function _renderOverviewPanel(report) {
    let html = '';

    // Risk level badge
    if (report.risk_level && report.risk_level !== 'Unknown') {
      const lvlMap = { critical: 'critical', high: 'high', moderate: 'moderate', low: 'low' };
      const cls = lvlMap[report.risk_level.toLowerCase()] || 'high';
      html += '<div class="risk-badge ' + cls + '">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0">' +
        '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>' +
        _escHtml(report.risk_level) + ' Risk' +
        '</div>';
    }

    // Key points cards
    if (report.key_points && report.key_points.length) {
      html += '<div class="report-key-points">' +
        '<div class="kp-title">Key Points</div>' +
        '<ul class="kp-list">' +
        report.key_points.map(function(p) {
          return '<li>' + _escHtml(p) + '</li>';
        }).join('') +
        '</ul></div>';
    }

    // Briefing text
    const text = report.situation_overview;
    if (text) {
      if (report.key_points && report.key_points.length) {
        html += '<div class="report-briefing-label">Full Briefing</div>';
      }
      html += '<div class="report-section-card"><div class="report-text">' + _fmt(text) + '</div></div>';
    }

    return html || '<div class="report-na">Not available</div>';
  }

  // ── Chat ─────────────────────────────────────────────────────────────────────

  function _clearChat() {
    const msgs = document.getElementById('chat-messages');
    if (msgs) msgs.innerHTML = '<div class="chat-welcome">Ask anything about this fire event and the AI analysis above.</div>';
  }

  function _renderInitialSuggestions() {
    const msgs = document.getElementById('chat-messages');
    if (!msgs) return;
    const div = document.createElement('div');
    div.className = 'suggested-qs initial-qs';
    div.innerHTML = '<div class="sq-label">Suggested questions</div>' +
      INITIAL_QUESTIONS.map(function(q) {
        return '<button class="sq-btn" onclick="window.__askQ(this)">' + _escHtml(q) + '</button>';
      }).join('');
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function _escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function _fmt(text) {
    return _escHtml(text)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  function _renderMsg(text) {
    const parts = text.split(/\n+Suggested questions:\s*/i);
    let html = '<div class="msg-body">' + _fmt(parts[0]) + '</div>';
    if (parts[1]) {
      const qs = parts[1].split('\n').map(function(l) { return l.replace(/^\d+\.\s*/, '').trim(); }).filter(Boolean);
      if (qs.length) {
        html += '<div class="suggested-qs"><div class="sq-label">Suggested questions</div>' +
          qs.map(function(q) { return '<button class="sq-btn" onclick="window.__askQ(this)">' + _escHtml(q) + '</button>'; }).join('') +
          '</div>';
      }
    }
    return html;
  }

  window.__askQ = function(btn) {
    document.getElementById('chat-input').value = btn.textContent;
    _send();
  };

  function _appendMsg(role, content, id) {
    const msgs = document.getElementById('chat-messages');
    const div  = document.createElement('div');
    div.className = 'chat-msg-' + role;
    if (id) div.id = id;
    div.innerHTML = _renderMsg(content);
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function _send() {
    if (_streaming || !_eid) return;
    const input = document.getElementById('chat-input');
    const msg   = input.value.trim();
    if (!msg) return;
    input.value = '';

    _appendMsg('user', msg);
    _history.push({ role: 'user', content: msg });

    const aId  = 'amsg-' + Date.now();
    const aDiv = _appendMsg('assistant', '…', aId);

    _streaming = true;
    document.getElementById('chat-send-btn').style.opacity = '.4';

    let full = '';
    const prevHistory = _history.slice(0, -1);

    window.API.streamChat(
      _eid,
      { message: msg, timestep_id: _tsid, history: prevHistory },
      function(chunk) {
        full += chunk;
        aDiv.innerHTML = _renderMsg(full + '▌');
        document.getElementById('chat-messages').scrollTop = 999999;
      },
      function() {
        aDiv.innerHTML = _renderMsg(full);
        _history.push({ role: 'assistant', content: full });
        _streaming = false;
        document.getElementById('chat-send-btn').style.opacity = '';
        document.getElementById('chat-messages').scrollTop = 999999;
      },
      function(err) {
        aDiv.innerHTML = '<div class="msg-body error-msg">Error: ' + _escHtml(err) + '</div>';
        _streaming = false;
        document.getElementById('chat-send-btn').style.opacity = '';
      }
    );
  }

  window.AIModal = { init, setContext, open, close, renderCard };
})();
