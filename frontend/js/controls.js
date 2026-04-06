// controls.js — playback controls + select-all toggle
// Scrubber init (date/time) is handled in wildfire.js::initScrubber().

let isPlaying = false;
let playbackInterval = null;

const timeSlider  = document.getElementById('time-slider');
const timeDisplay = document.getElementById('time-display');
const playBtn     = document.getElementById('btn-play');

function formatHour(value) {
    return String(parseInt(value)).padStart(2, '0') + ':00';
}

// Sync time display when slider moves (wildfire.js also updates this on loadTimestep)
timeSlider.addEventListener('input', e => {
    timeDisplay.textContent = formatHour(e.target.value);
});

// Play / Pause — steps through timesteps every 1.5 seconds
playBtn.addEventListener('click', () => {
    if (isPlaying) {
        isPlaying = false;
        playBtn.textContent = '▶';
        clearInterval(playbackInterval);
    } else {
        isPlaying = true;
        playBtn.textContent = '⏸';
        playbackInterval = setInterval(() => {
            if (typeof stepTimestep === 'function') stepTimestep(1);
        }, 1500);
    }
});

// Step / jump buttons — delegate to wildfire.js functions
document.getElementById('btn-start').onclick = () => { if (typeof jumpToStart === 'function') jumpToStart(); };
document.getElementById('btn-end').onclick   = () => { if (typeof jumpToEnd   === 'function') jumpToEnd();   };
document.getElementById('btn-back').onclick  = () => { if (typeof stepTimestep === 'function') stepTimestep(-1); };
document.getElementById('btn-ff').onclick    = () => { if (typeof stepTimestep === 'function') stepTimestep(1);  };

// Select All / Deselect All toggle
const selectAllBtn    = document.getElementById('select-all');
const layerCheckboxes = document.querySelectorAll('#layer-panel input[type="checkbox"]');

selectAllBtn.addEventListener('click', () => {
    const allChecked = Array.from(layerCheckboxes).every(cb => cb.checked);
    const newState   = !allChecked;
    layerCheckboxes.forEach(cb => {
        cb.checked = newState;
        cb.dispatchEvent(new Event('change'));
    });
    selectAllBtn.textContent = newState ? 'Deselect All' : 'Select All';
});
