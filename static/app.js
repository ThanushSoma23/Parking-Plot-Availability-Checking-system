// ParkPulse AI — Client Application Engine

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const timeDisplay = document.getElementById('timeDisplay');
    const kpiAvailable = document.getElementById('kpiAvailable');
    const kpiOccupied = document.getElementById('kpiOccupied');
    const kpiTotal = document.getElementById('kpiTotal');
    const kpiRate = document.getElementById('kpiRate');
    const kpiProgress = document.getElementById('kpiProgress');
    const slotsMatrix = document.getElementById('slotsMatrix');
    
    // Config Sliders
    const playbackSpeedInput = document.getElementById('playbackSpeed');
    const pixelThresholdInput = document.getElementById('pixelThreshold');
    const blurKernelInput = document.getElementById('blurKernel');
    const blockSizeInput = document.getElementById('blockSize');
    const cValInput = document.getElementById('cVal');

    const valPlaybackSpeed = document.getElementById('valPlaybackSpeed');
    const valPixelThreshold = document.getElementById('valPixelThreshold');
    const valBlurKernel = document.getElementById('valBlurKernel');
    const valBlockSize = document.getElementById('valBlockSize');
    const valCVal = document.getElementById('valCVal');

    const btnResetConfig = document.getElementById('btnResetConfig');
    const btnTogglePlay = document.getElementById('btnTogglePlay');
    const playIcon = document.getElementById('playIcon');
    const btnFullscreen = document.getElementById('btnFullscreen');
    const videoContainer = document.getElementById('videoContainer');
    const videoStream = document.getElementById('videoStream');

    let currentFilter = 'all';
    let isPlaying = true;

    // 1. Clock Updates
    function updateClock() {
        const now = new Date();
        timeDisplay.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Fetch Telemetry Stats
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();

            // Update KPI Values
            kpiAvailable.textContent = data.available_slots;
            kpiOccupied.textContent = data.occupied_slots;
            kpiTotal.textContent = data.total_slots;
            kpiRate.textContent = `${data.occupancy_rate}%`;
            kpiProgress.style.width = `${data.occupancy_rate}%`;

            // Render Slot Matrix
            renderSlotsMatrix(data.slots);
        } catch (err) {
            console.error('Telemetry fetch error:', err);
        }
    }

    // Poll stats every 1 second
    setInterval(fetchStats, 1000);
    fetchStats();

    // 3. Render Slot Grid
    function renderSlotsMatrix(slots) {
        if (!slots || !slotsMatrix) return;

        let filteredSlots = slots;
        if (currentFilter === 'available') {
            filteredSlots = slots.filter(s => !s.occupied);
        } else if (currentFilter === 'occupied') {
            filteredSlots = slots.filter(s => s.occupied);
        }

        slotsMatrix.innerHTML = filteredSlots.map(slot => {
            const statusClass = slot.occupied ? 'occupied' : 'available';
            const statusLabel = slot.occupied ? 'BUSY' : 'FREE';
            return `
                <div class="slot-item ${statusClass}">
                    <span class="slot-id">P${slot.id}</span>
                    <span class="slot-badge">${statusLabel}</span>
                </div>
            `;
        }).join('');
    }

    // 4. Matrix Filter Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.getAttribute('data-filter');
            fetchStats();
        });
    });

    // 5. Config Sliders Handling
    async function sendConfig() {
        const payload = {
            playback_speed: parseFloat(playbackSpeedInput.value),
            pixel_threshold: parseInt(pixelThresholdInput.value),
            blur_kernel: parseInt(blurKernelInput.value),
            block_size: parseInt(blockSizeInput.value),
            c_val: parseInt(cValInput.value)
        };

        valPlaybackSpeed.textContent = `${payload.playback_speed}x`;
        valPixelThreshold.textContent = payload.pixel_threshold;
        valBlurKernel.textContent = payload.blur_kernel;
        valBlockSize.textContent = payload.block_size;
        valCVal.textContent = payload.c_val;

        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (err) {
            console.error('Config update error:', err);
        }
    }

    [playbackSpeedInput, pixelThresholdInput, blurKernelInput, blockSizeInput, cValInput].forEach(slider => {
        slider.addEventListener('input', sendConfig);
    });

    // 6. Reset Defaults
    btnResetConfig.addEventListener('click', () => {
        playbackSpeedInput.value = 1.5;
        pixelThresholdInput.value = 900;
        blurKernelInput.value = 3;
        blockSizeInput.value = 25;
        cValInput.value = 16;
        sendConfig();
    });

    // 7. Video Stream Play/Pause Toggle
    btnTogglePlay.addEventListener('click', () => {
        isPlaying = !isPlaying;
        if (isPlaying) {
            videoStream.src = '/video_feed';
            playIcon.setAttribute('data-lucide', 'pause');
        } else {
            videoStream.src = '';
            playIcon.setAttribute('data-lucide', 'play');
        }
        if (window.lucide) lucide.createIcons();
    });

    // 8. Fullscreen Toggle
    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            videoContainer.requestFullscreen().catch(err => console.error(err));
        } else {
            document.exitFullscreen();
        }
    });
});
