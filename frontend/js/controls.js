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