//requireAuth();

const map = L.map('map', { zoomControl: true }).setView([51.0, -114.0], 7);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

setTimeout(() => { map.invalidateSize(); }, 100);