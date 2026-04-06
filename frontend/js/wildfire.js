// wildfire.js — main data controller
// Loads event + timesteps, manages all map layers, drives the scrubber.

const API = 'http://localhost:5000/api';

// ── State ─────────────────────────────────────────────────────────────────────
let currentEvent    = null;
let allTimesteps    = [];   // sorted by slot_time asc
let currentTs       = null;
let currentHorizon  = '6h';

// ── Leaflet layer handles ─────────────────────────────────────────────────────
const layers = { perimeter: null, hotspots: null, riskZones: null };

// ── Boot ──────────────────────────────────────────────────────────────────────
async function initDashboard() {
    // 1. Load event list
    let events = [];
    try { events = await fetch(`${API}/events/`).then(r => r.json()); }
    catch (e) { console.error('[wildfire] Could not fetch events:', e); return; }
    if (!events.length) { console.warn('[wildfire] No events in DB'); return; }

    currentEvent = events[0];
    document.querySelector('.header-event').textContent = currentEvent.name;

    // Fit map to bounding box
    const b = currentEvent.bbox;
    map.fitBounds([[b[1], b[0]], [b[3], b[2]]]);

    // 2. Load timesteps
    try {
        allTimesteps = await fetch(`${API}/events/${currentEvent.id}/timesteps`).then(r => r.json());
    } catch (e) {
        console.warn('[wildfire] Could not fetch timesteps:', e);
        allTimesteps = [];
    }

    // 3. Wire scrubber now that we have dates
    initScrubber();

    // 4. Load middle-ish timestep as default
    if (allTimesteps.length) {
        const mid = allTimesteps[Math.floor(allTimesteps.length / 2)];
        loadTimestep(mid);
    }
}

// ── Scrubber ──────────────────────────────────────────────────────────────────
function initScrubber() {
    if (!allTimesteps.length) return;

    const dateInput  = document.getElementById('date-input');
    const timeSlider = document.getElementById('time-slider');

    // Date range from timesteps
    const dates = allTimesteps.map(ts => ts.slot_time.slice(0, 10));
    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];
    dateInput.min = minDate;
    dateInput.max = maxDate;
    dateInput.value = minDate;

    // Slot hours available (0,3,6,9,12,15,18,21)
    timeSlider.min  = 0;
    timeSlider.max  = 21;
    timeSlider.step = 3;
    timeSlider.value = 12;

    function onScrubberChange() {
        const ts = findNearestTimestep(dateInput.value, parseInt(timeSlider.value));
        if (ts && ts !== currentTs) loadTimestep(ts);
    }

    dateInput.addEventListener('change', onScrubberChange);
    timeSlider.addEventListener('input',  onScrubberChange);
}

function findNearestTimestep(dateStr, hour) {
    const target = new Date(`${dateStr}T${String(hour).padStart(2,'0')}:00:00Z`).getTime();
    let best = null, bestDiff = Infinity;
    for (const ts of allTimesteps) {
        const diff = Math.abs(new Date(ts.slot_time).getTime() - target);
        if (diff < bestDiff) { bestDiff = diff; best = ts; }
    }
    return best;
}

// ── Load one timestep ─────────────────────────────────────────────────────────
async function loadTimestep(ts) {
    currentTs = ts;
    const eId = currentEvent.id;
    const tsId = ts.id;

    // Update status bar date/time
    const slot = new Date(ts.slot_time);
    const slotStr = slot.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
    const mapDate = document.getElementById('dyn-map-date');
    if (mapDate) mapDate.textContent = slotStr;

    // Sync scrubber (date picker + slider + time label) to match loaded timestep
    const dateInput  = document.getElementById('date-input');
    const timeSlider = document.getElementById('time-slider');
    const timeDisplay = document.getElementById('time-display');
    const h = slot.getUTCHours();
    if (dateInput)   dateInput.value    = slot.toISOString().slice(0, 10);
    if (timeSlider)  timeSlider.value   = h;
    if (timeDisplay) timeDisplay.textContent = String(h).padStart(2, '0') + ':00';

    // Load all layer data in parallel
    const [perimeter, hotspots, riskZones] = await Promise.all([
        fetch(`${API}/events/${eId}/timesteps/${tsId}/perimeter`)
            .then(r => r.json()).catch(() => ({ type: 'FeatureCollection', features: [] })),
        fetch(`${API}/events/${eId}/timesteps/${tsId}/hotspots`)
            .then(r => r.json()).catch(() => ({ type: 'FeatureCollection', features: [] })),
        fetch(`${API}/events/${eId}/timesteps/${tsId}/risk-zones`)
            .then(r => r.json()).catch(() => ({ type: 'FeatureCollection', features: [] })),
    ]);

    renderPerimeter(perimeter);
    renderHotspots(hotspots);
    renderRiskZones(riskZones, currentHorizon);

    // Reset stats to — immediately so stale "Loading..." never lingers
    clearAnalysisPanel();
    clearFireContext();

    // Load stats (non-blocking)
    fetch(`${API}/events/${eId}/timesteps/${tsId}/analysis`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d ? updateAnalysisPanel(d) : null)
        .catch(() => {});
    fetch(`${API}/events/${eId}/timesteps/${tsId}/fire-context`)
        .then(r => r.ok ? r.json() : null)
        .then(d => updateFireContext(d))
        .catch(() => clearFireContext());
}

// ── Layer renderers ───────────────────────────────────────────────────────────
function renderPerimeter(geojson) {
    if (layers.perimeter) map.removeLayer(layers.perimeter);
    layers.perimeter = L.geoJSON(geojson, {
        style: { color: '#c0392b', weight: 2, fillColor: '#c0392b', fillOpacity: 0.2 },
        onEachFeature(f, l) {
            const p = f.properties || {};
            l.bindPopup(
                `<b>Fire Perimeter</b><br/>` +
                `Area: ${p.area_km2 != null ? p.area_km2 + ' km²' : '—'}<br/>` +
                `T1: ${p.t1 || '—'}`
            );
        }
    });
    if (document.getElementById('lyr-perimeter')?.checked) layers.perimeter.addTo(map);
}

function renderHotspots(geojson) {
    if (layers.hotspots) map.removeLayer(layers.hotspots);
    layers.hotspots = L.geoJSON(geojson, {
        pointToLayer(f, latlng) {
            const frp = f.properties?.frp || 10;
            return L.circleMarker(latlng, {
                radius:      Math.max(4, Math.min(14, frp / 15)),
                fillColor:   '#ff4500',
                color:       '#fff',
                weight:      1,
                fillOpacity: 0.85,
            });
        },
        onEachFeature(f, l) {
            const p = f.properties || {};
            l.bindPopup(
                `<b>Hotspot</b><br/>` +
                `FRP: ${p.frp != null ? p.frp + ' MW' : '—'}<br/>` +
                `Confidence: ${p.confidence || '—'}`
            );
        }
    });
    if (document.getElementById('lyr-hotspots')?.checked) layers.hotspots.addTo(map);
}

function renderRiskZones(geojson, horizon) {
    if (layers.riskZones) map.removeLayer(layers.riskZones);
    const COLORS = { high: '#ef4444', medium: '#f97316', low: '#eab308' };
    const filtered = {
        ...geojson,
        features: geojson.features.filter(f => f.properties?.horizon === horizon),
    };
    layers.riskZones = L.geoJSON(filtered, {
        style(f) {
            const c = COLORS[f.properties?.risk_level] || '#888';
            return { color: c, weight: 1, fillColor: c, fillOpacity: 0.35, dashArray: '4,4' };
        },
        onEachFeature(f, l) {
            const p = f.properties || {};
            l.bindPopup(
                `<b>Risk Zone — ${p.risk_level || '?'}</b><br/>` +
                `Horizon: ${p.horizon || '—'}<br/>` +
                `Prob max: ${p.prob_max != null ? (p.prob_max * 100).toFixed(1) + '%' : '—'}<br/>` +
                `Cells: ${p.cell_count ?? '—'}`
            );
        }
    });
    if (document.getElementById('lyr-risk')?.checked) layers.riskZones.addTo(map);
}

// ── Stats panel updaters ──────────────────────────────────────────────────────
function clearAnalysisPanel() {
    const $ = id => document.getElementById(id);
    if ($('dyn-pop'))       $('dyn-pop').textContent = '—';
    if ($('dyn-risk-tags')) $('dyn-risk-tags').innerHTML = '—';
}

function updateAnalysisPanel(data) {
    const $ = id => document.getElementById(id);
    if ($('dyn-pop')) {
        $('dyn-pop').textContent = data.affected_population != null
            ? '~' + data.affected_population.toLocaleString()
            : '—';
    }
    if ($('dyn-risk-tags')) {
        const tags = [];
        const badge = (label, color, val) =>
            `<span style="background:${color};color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;">${label}: ${val.toLocaleString()}</span>`;
        if (data.at_risk_3h)  tags.push(badge('3h',  '#ef4444', data.at_risk_3h));
        if (data.at_risk_6h)  tags.push(badge('6h',  '#f97316', data.at_risk_6h));
        if (data.at_risk_12h) tags.push(badge('12h', '#eab308', data.at_risk_12h));
        $('dyn-risk-tags').innerHTML = tags.join(' ') || '—';
    }
}

function clearFireContext() {
    const $ = id => document.getElementById(id);
    if ($('dyn-fire-area'))   $('dyn-fire-area').textContent   = '—';
    if ($('dyn-hotspots'))    $('dyn-hotspots').textContent    = '—';
    if ($('dyn-wind'))        $('dyn-wind').textContent        = '—';
    if ($('burned-area'))     $('burned-area').textContent     = '—';
    if ($('time-to-reach'))   $('time-to-reach').textContent   = '—';
    if ($('dyn-source'))      $('dyn-source').textContent      = 'NASA FIRMS / ERA5';
    if ($('dyn-next-update')) $('dyn-next-update').textContent = '3h slot';
}

function updateFireContext(ctx) {
    if (!ctx) { clearFireContext(); return; }
    const $ = id => document.getElementById(id);
    const fire = ctx.fire || {};
    const wx   = ctx.weather_t1 || {};

    if ($('dyn-fire-area'))
        $('dyn-fire-area').textContent = fire.burned_area_km2 != null
            ? (fire.burned_area_km2 * 100).toFixed(0) + ' ha' : '—';

    if ($('dyn-hotspots'))
        $('dyn-hotspots').textContent = fire.n_hotspots != null ? fire.n_hotspots : '—';

    if ($('dyn-wind')) {
        if (wx.wind_speed_kmh != null) {
            const dirs = ['N','NE','E','SE','S','SW','W','NW'];
            const dir  = dirs[Math.round(((wx.wind_dir || 0) % 360) / 45) % 8];
            $('dyn-wind').textContent = `${dir} at ${wx.wind_speed_kmh.toFixed(0)} km/h`;
        } else {
            $('dyn-wind').textContent = '—';
        }
    }

    // Bottom bar — burned area from current perimeter; time-to-reach from risk zones
    if ($('burned-area'))
        $('burned-area').textContent = fire.burned_area_km2 != null
            ? (fire.burned_area_km2 * 100).toFixed(0) + ' ha (current)' : '—';

    if ($('time-to-reach'))
        $('time-to-reach').textContent = ctx.time_to_nearest_community != null
            ? ctx.time_to_nearest_community : '—';

    if ($('dyn-source')) $('dyn-source').textContent = 'NASA FIRMS / ERA5';
    if ($('dyn-next-update')) $('dyn-next-update').textContent = '3h slot';
}

// ── Layer checkbox wiring ─────────────────────────────────────────────────────
function wireCheckbox(cbId, layerKey) {
    const cb = document.getElementById(cbId);
    if (!cb) return;
    cb.addEventListener('change', () => {
        const lyr = layers[layerKey];
        if (!lyr) return;
        cb.checked ? lyr.addTo(map) : map.removeLayer(lyr);
    });
}

// ── Horizon button wiring ─────────────────────────────────────────────────────
function wireHorizonButtons() {
    document.querySelectorAll('.horizon-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.horizon-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentHorizon = btn.getAttribute('data-h') + 'h';
            if (!currentTs || !currentEvent) return;
            fetch(`${API}/events/${currentEvent.id}/timesteps/${currentTs.id}/risk-zones`)
                .then(r => r.json())
                .then(gz => renderRiskZones(gz, currentHorizon))
                .catch(() => {});
        });
    });
}

// ── Expose for controls.js (play/step buttons) ────────────────────────────────
function stepTimestep(delta) {
    if (!allTimesteps.length || !currentTs) return;
    const idx = allTimesteps.findIndex(ts => ts.id === currentTs.id);
    const next = allTimesteps[Math.max(0, Math.min(allTimesteps.length - 1, idx + delta))];
    if (next && next.id !== currentTs.id) loadTimestep(next);
}

function jumpToStart() { if (allTimesteps.length) loadTimestep(allTimesteps[0]); }
function jumpToEnd()   { if (allTimesteps.length) loadTimestep(allTimesteps[allTimesteps.length - 1]); }

// ── DOMContentLoaded ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    wireCheckbox('lyr-perimeter', 'perimeter');
    wireCheckbox('lyr-hotspots',  'hotspots');
    wireCheckbox('lyr-risk',      'riskZones');
    wireHorizonButtons();
    initDashboard();
});
