// Setup variables to track
let isPlaying = false;
let playbackInterval;

// Get the HTML elements for the slider and time display
const timeSlider = document.getElementById('time-slider');
const timeDisplay = document.getElementById('time-display');
const playBtn = document.getElementById('btn-play');
const dateInput = document.getElementById('date-input');
const mapDateStatus = document.getElementById('dyn-map-date');

// Helper function to turn a number like 14 into "14:00"
function formatTime(value) {
    return value.toString().padStart(2, '0') + ":00";
}

// Function to update the time across the whole dashboard
function updateTime(newValue) {
    // Keep the number between 0 and 24
    if (newValue < 0) newValue = 0;
    if (newValue > 24) newValue = 24;
    
    // Update the slider position
    timeSlider.value = newValue;
    
    // Update the large time text above the slider
    timeDisplay.textContent = formatTime(newValue);
    
    // Update the small date/time in the bar under the map
    if (mapDateStatus) {
        mapDateStatus.textContent = `${dateInput.value} ${formatTime(newValue)} UTC`;
    }

    // In the future, this is where we will tell the map to show different fire data
    console.log("Time changed to:", formatTime(newValue));
}

// Connect the slider to the update function 
timeSlider.addEventListener('input', (e) => {
    updateTime(e.target.value);
});

// Connect the Play/Pause button logic
playBtn.addEventListener('click', () => {
    if (isPlaying) {
        // Stop the timer
        isPlaying = false;
        playBtn.textContent = '▶';
        clearInterval(playbackInterval);
    } else {
        // Start a timer to move forward 1 hour every 1 second
        isPlaying = true;
        playBtn.textContent = '⏸';
        
        playbackInterval = setInterval(() => {
            let nextHour = parseInt(timeSlider.value) + 1;
            
            // Loop back to the start of the day if we reach 24:00
            if (nextHour > 24) nextHour = 0;
            
            updateTime(nextHour);
        }, 1000);
    }
});

// Connect the jump and step buttons
document.getElementById('btn-start').onclick = () => updateTime(0);
document.getElementById('btn-end').onclick = () => updateTime(24);
document.getElementById('btn-back').onclick = () => updateTime(parseInt(timeSlider.value) - 1);
document.getElementById('btn-ff').onclick = () => updateTime(parseInt(timeSlider.value) + 1);

// Create a function to update all the text on the dashboard
function updateDashboardStats() {
    console.log("Updating dashboard statistics...");

    // Update the Quick Geo Analysis panel
    document.getElementById('dyn-fire-area').innerHTML = '12,847 ha <span style="color:#ef4444; font-size:10px;">▲ +23%</span>';
    document.getElementById('dyn-hotspots').textContent = '342';
    document.getElementById('dyn-wind').innerHTML = 'NE at 28 km/h <span style="color:#f59e0b">⚠️</span>';
    document.getElementById('dyn-pop').textContent = '~8,200';

    // Create small colored badges for the At Risk communities
    const tagsHtml = `
        <span style="background:#ef4444; color:white; padding:2px 6px; border-radius:4px; font-size:10px; margin-right:4px;">Abasand</span>
        <span style="background:#f59e0b; color:white; padding:2px 6px; border-radius:4px; font-size:10px; margin-right:4px;">Beacon Hill</span>
    `;
    document.getElementById('dyn-risk-tags').innerHTML = tagsHtml;

    // Update the tiny status bar directly under the map
    document.getElementById('dyn-map-date').textContent = '2016-05-05 14:00 UTC';
    document.getElementById('dyn-next-update').textContent = '2h 47m';
    document.getElementById('dyn-source').textContent = 'Alberta Wildfire Official';

    // Update the large critical numbers on the bottom bar
    document.getElementById('burned-area').textContent = '14,200 ha';
    document.getElementById('time-to-reach').textContent = '1h 28m';
}

document.addEventListener('DOMContentLoaded', () => {
    // We use setTimeout to wait 800 milliseconds before filling the text.
    // This gives the map time to load first
    setTimeout(() => {
        updateDashboardStats();
    }, 800);
});