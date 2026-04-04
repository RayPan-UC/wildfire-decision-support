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
            const mapCorners = [
                [bbox[1], bbox[0]], 
                [bbox[3], bbox[2]]  
            ];
            
            map.fitBounds(mapCorners);
            console.log("4. Map zoom complete.");
        } else {
            // If the database is empty, it will print this warning.
            console.warn("WARNING: The database is empty. No events were found.");
        }
        
    } catch (error) {
        console.error("Could not connect to the Python server:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadFireEvents();
});