// home.js

const HOME_API = 'http://localhost:5000/api';

// Static metadata per event ID 
const EVENT_META = {
    1: {
        subtitle:   'Horse River Fire · May 1\u2013May 31, 2016 · Alberta, Canada',
        areaBurned: '589,552 ha',
        evacuees:   '~88,000',
        damage:     '$9.9B',
    }
};

let activeEventId = null;

// Map setup

const homeMap = L.map('home-map', { zoomControl: true }).setView([60.0, -96.0], 4);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap contributors, © CARTO',
    maxZoom: 19
}).addTo(homeMap);

// Marker

function makeFireIcon(label) {
    return L.divIcon({
        html: `
            <div class="fire-marker-wrap">
                <div class="fire-marker-icon">🔥</div>
                <div class="fire-marker-label">${label}</div>
            </div>`,
        className: '',
        iconSize:    [120, 60],
        iconAnchor:  [60, 38],
        popupAnchor: [0, -40],
    });
}

// Event card

function openCard(event) {
    const meta = EVENT_META[event.id] || {
        subtitle:   `${event.year} · Canada`,
        areaBurned: '—',
        evacuees:   '—',
        damage:     '—',
    };

    document.getElementById('card-title').textContent    = event.name;
    document.getElementById('card-subtitle').textContent = meta.subtitle;
    document.getElementById('card-area').textContent     = meta.areaBurned;
    document.getElementById('card-evacuees').textContent = meta.evacuees;
    document.getElementById('card-damage').textContent   = meta.damage;

    activeEventId = event.id;
    document.getElementById('event-card').classList.remove('hidden');
}

function closeCard() {
    document.getElementById('event-card').classList.add('hidden');
    activeEventId = null;
}

document.getElementById('btn-explore').addEventListener('click', () => {
    if (!getToken()) {
        window.location.href = '/login';
        return;
    }
    window.location.href = '/explore';
});

// Show map view (hide grid, reveal map, zoom to Fort McMurray)
function showMapView() {
    document.getElementById('home-grid').classList.add('hidden');
    document.getElementById('home-map').classList.add('visible');
    homeMap.invalidateSize();
    homeMap.setView([56.726, -111.379], 9);
}

// Holds Fort McMurray event data once loaded
let fortMcMurrayEvent = null;

// Fort McMurray card click
document.getElementById('card-fortmcmurray').addEventListener('click', () => {
    showMapView();
    const event = fortMcMurrayEvent || { id: 1, name: 'Fort McMurray Wildfire', year: 2016 };
    openCard(event);
});

// Load events from API

async function loadHomeEvents() {
    try {
        const events = await fetch(`${HOME_API}/events/`).then(r => r.json());

        events.forEach(event => {
            const b   = event.bbox;
            const lat = (b[1] + b[3]) / 2;
            const lng = (b[0] + b[2]) / 2;
            const label = `${event.name.replace(' Wildfire', '')}`;

            L.marker([lat, lng], { icon: makeFireIcon(label) })
                .addTo(homeMap)
                .on('click', () => openCard(event));

            if (event.id === 1) fortMcMurrayEvent = event;
        });

    } catch (err) {
        console.error("Could not load events:", err);
    }
}

loadHomeEvents();
