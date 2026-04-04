async function loadEvacuation() {
    try {
        const response = await fetch(`${API_BASE_URL}/evacuation/`);
        const data = await response.json();
        
        // --- EVACUATION ROUTES ---
        const routesLayer = L.geoJSON(data, {
            filter: function(feature) { return feature.properties.type === "route"; },
            style: function (feature) {
                return { color: "#00ff00", weight: 4, dashArray: '10, 10' };
            },
            onEachFeature: function(feature, layer) {
                layer.bindPopup(`<b>Evacuation Route:</b> ${feature.properties.name}`);
            }
        });
        
        const routesBox = document.getElementById('lyr-routes');
        if (routesBox.checked) routesLayer.addTo(map);
        
        routesBox.addEventListener('change', (e) => {
            if (e.target.checked) map.addLayer(routesLayer);
            else map.removeLayer(routesLayer);
        });

        // --- ASSEMBLY POINTS ---
        const assemblyLayer = L.geoJSON(data, {
            filter: function(feature) { return feature.properties.type === "assembly"; },
            pointToLayer: function (feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 8, fillColor: "#ffffff", color: "#00ff00", weight: 3, fillOpacity: 1
                });
            },
            onEachFeature: function(feature, layer) {
                layer.bindPopup(`<b>Safe Zone:</b> ${feature.properties.name}`);
            }
        });
        
        const assemblyBox = document.getElementById('lyr-assembly');
        if (assemblyBox.checked) assemblyLayer.addTo(map);
        
        assemblyBox.addEventListener('change', (e) => {
            if (e.target.checked) map.addLayer(assemblyLayer);
            else map.removeLayer(assemblyLayer);
        });
        
    } catch (error) {
        console.error("Could not load evacuation data:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadEvacuation();
});