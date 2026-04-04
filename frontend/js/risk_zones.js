async function loadRiskZones() {
    try {
        const response = await fetch(`${API_BASE_URL}/risk-zones/`);
        const data = await response.json();
        
        const riskLayer = L.geoJSON(data, {
            style: function (feature) {
                let polyColor = feature.properties.level === "High" ? "#ff0000" : "#ff9900";
                return { color: polyColor, weight: 2, fillColor: polyColor, fillOpacity: 0.3, dashArray: '5, 5' };
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`<b>Risk Level:</b> ${feature.properties.level}<br><b>Details:</b> ${feature.properties.description}`);
            }
        });
        
        const checkbox = document.getElementById('lyr-risk');
        if (checkbox.checked) {
            riskLayer.addTo(map);
        }
        
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                map.addLayer(riskLayer);
            } else {
                map.removeLayer(riskLayer);
            }
        });
        
    } catch (error) {
        console.error("Could not load risk zones:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadRiskZones();
});