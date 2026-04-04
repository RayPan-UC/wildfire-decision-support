// wildfire.js 
const API_BASE_URL = 'http://localhost:5000/api';

async function loadFireEvents() {
    try {
        console.log("1. Asking Python server for events...");
        const response = await fetch(`${API_BASE_URL}/events/`);
        
        const events = await response.json();
        console.log("2. Python server replied with this data:", events); // This will show us the exact data!
        
        if (events.length > 0) {
            const latestEvent = events[0];
            console.log("3. Moving map to:", latestEvent.name);
            
            document.querySelector('.header-event').textContent = latestEvent.name;
            
            const bbox = latestEvent.bbox;
            // Calculate the exact center of the bounding box
            const centerLat = (bbox[1] + bbox[3]) / 2;
            const centerLng = (bbox[0] + bbox[2]) / 2;
            
            // Set the map to look exactly at the center. 
            map.setView([centerLat, centerLng], 10);
            console.log("4. Map zoom complete.");
        } else {
            // If the database is empty, it will print this warning.
            console.warn("WARNING: The database is empty. No events were found.");
        }
        
    } catch (error) {
        console.error("Could not connect to the Python server:", error);
    }
}

async function loadHotspots() {
    try {
        console.log("Asking Python server for hotspots...");
        
        const response = await fetch(`${API_BASE_URL}/hotspots/`);
        const data = await response.json();
        
        const hotspotsLayer = L.geoJSON(data, {
            pointToLayer: function (feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 6, fillColor: "#ff0000", color: "#ffffff",
                    weight: 1, opacity: 1, fillOpacity: 0.8
                });
            }
        });
        
        const checkbox = document.getElementById('lyr-hotspots');
        if (checkbox.checked) {
            hotspotsLayer.addTo(map);
        }
        
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                map.addLayer(hotspotsLayer);
            } else {
                map.removeLayer(hotspotsLayer);
            }
        });
        
    } catch (error) {
        console.error("Could not load hotspots:", error);
    }
}

async function loadPerimeter() {
    try {
        console.log("Asking Python server for fire perimeter...");
        
        const response = await fetch(`${API_BASE_URL}/perimeter/`);
        const data = await response.json();
        
        // Save the polygon into a variable
        const perimeterLayer = L.geoJSON(data, {
            style: function (feature) {
                return {
                    color: "#8b4513", 
                    weight: 3,        
                    fillColor: "#8b4513", 
                    fillOpacity: 0.2  
                };
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`<b>${feature.properties.name}</b>`);
            }
        });
        
        // Find the HTML checkbox for Fire Perimeter
        const checkbox = document.getElementById('lyr-perimeter');
        
        // Put data on the map ONLY if the box is ticked
        if (checkbox.checked) {
            perimeterLayer.addTo(map);
        }
        
        // Listen for changes. Add or remove the variable from the map.
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                map.addLayer(perimeterLayer);
            } else {
                map.removeLayer(perimeterLayer);
            }
        });
        
    } catch (error) {
        console.error("Could not load perimeter:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadFireEvents();
    loadHotspots();
    loadPerimeter(); 
});