//requireAuth();

const map = L.map('map', { zoomControl: true }).setView([51.0, -114.0], 7);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap contributors, © CARTO',
  maxZoom: 19
}).addTo(map);

setTimeout(() => { map.invalidateSize(); }, 100);