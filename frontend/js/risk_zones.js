// Function to fetch and draw the risk zones
async function loadRiskZones() {
    try {
        console.log("Asking Python server for risk zones...");
        
        // Fetch data from the API
        const response = await fetch(`${API_BASE_URL}/risk-zones/`);
        const data = await response.json();
        
        // Draw the GeoJSON data on the Leaflet map
        L.geoJSON(data, {
            // decide how each polygon looks
            style: function (feature) {
                let polyColor = "#ffff00"; // Default yellow for Low risk
                
                if (feature.properties.level === "High") {
                    polyColor = "#ff0000"; // Red
                } else if (feature.properties.level === "Medium") {
                    polyColor = "#ff9900"; // Orange
                }

                return {
                    color: polyColor,       
                    weight: 2,             
                    fillColor: polyColor,  
                    fillOpacity: 0.3,      
                    dashArray: '5, 5'     
                };
            },
            // Add a popup when the user clicks the shape
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`<b>Risk Level:</b> ${feature.properties.level}<br><b>Details:</b> ${feature.properties.description}`);
            }
        }).addTo(map);
        
        console.log("Risk zones successfully drawn.");
        
    } catch (error) {
        console.error("Could not load risk zones:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadRiskZones();
});