async function loadEvacuation() {
    try {
        console.log("Asking Python server for evacuation routes...");
        
        // Fetch the data from Python
        const response = await fetch(`${API_BASE_URL}/evacuation/`);
        const data = await response.json();
        
        // Draw the GeoJSON on the map
        L.geoJSON(data, {
            
            // Style the escape routes
            style: function (feature) {
                if (feature.properties.type === "route") {
                    return {
                        color: "#00ff00", // Bright green
                        weight: 4,        // Thick line
                        dashArray: '10, 10' // Dashed line effect
                    };
                }
            },
            
            // Style the Points (The safe assembly camps)
            pointToLayer: function (feature, latlng) {
                if (feature.properties.type === "assembly") {
                    return L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: "#ffffff", // Solid white dot inside
                        color: "#00ff00",     // Green border outside
                        weight: 3,
                        fillOpacity: 1
                    });
                }
            },
            
            // Add popup labels when clicked
            onEachFeature: function(feature, layer) {
                if (feature.properties.type === "route") {
                    layer.bindPopup(`<b>Evacuation Route:</b> ${feature.properties.name}`);
                } else if (feature.properties.type === "assembly") {
                    layer.bindPopup(`<b>Safe Zone:</b> ${feature.properties.name}`);
                }
            }
            
        }).addTo(map);
        
        console.log("Evacuation routes successfully drawn.");
        
    } catch (error) {
        console.error("Could not load evacuation data:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadEvacuation();
});