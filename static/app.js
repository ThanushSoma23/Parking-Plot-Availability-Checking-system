// ParkPulse AI — Client Application & Booking Engine

document.addEventListener('DOMContentLoaded', () => {
    // Shared State
    let selectedSlot = null;      // { id, slotNumber }
    let selectedVehicle = null;   // { id, vehicleNumber, vehicleType }
    let vehiclesList = [];
    let currentFilter = 'all';
    let isPlaying = true;

    // --- DOM ELEMENTS ---
    const timeDisplay = document.getElementById('timeDisplay');
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    // Tab 1 Elements
    const kpiAvailable = document.getElementById('kpiAvailable');
    const kpiOccupied = document.getElementById('kpiOccupied');
    const kpiTotal = document.getElementById('kpiTotal');
    const kpiRate = document.getElementById('kpiRate');
    const kpiProgress = document.getElementById('kpiProgress');

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

    // Screen 2 Elements
    const detailTotal = document.getElementById('detailTotal');
    const detailAvailable = document.getElementById('detailAvailable');
    const detailOccupied = document.getElementById('detailOccupied');
    const detailOccupancyPct = document.getElementById('detailOccupancyPct');
    const btnViewAvailableSlots = document.getElementById('btnViewAvailableSlots');
    const btnGetDirections = document.getElementById('btnGetDirections');

    // Screen 3 Elements
    const slotsInteractiveGrid = document.getElementById('slotsInteractiveGrid');
    const selectedSlotLabel = document.getElementById('selectedSlotLabel');
    const btnSlotContinue = document.getElementById('btnSlotContinue');

    // Screen 4 Elements
    const vehiclesListEl = document.getElementById('vehiclesList');
    const btnSlotVehicleContinue = document.getElementById('btnVehicleContinue');
    const btnOpenAddVehicle = document.getElementById('btnOpenAddVehicle');
    const addVehicleModal = document.getElementById('addVehicleModal');
    const btnCloseAddVehicle = document.getElementById('btnCloseAddVehicle');
    const btnCancelAddVehicle = document.getElementById('btnCancelAddVehicle');
    const formAddVehicle = document.getElementById('formAddVehicle');

    // Screen 5 Elements
    const summaryCard = document.getElementById('summaryCard');
    const sumSlotNumber = document.getElementById('sumSlotNumber');
    const sumVehicleNumber = document.getElementById('sumVehicleNumber');
    const sumParkingFee = document.getElementById('sumParkingFee');
    const btnConfirmBooking = document.getElementById('btnConfirmBooking');

    // Ticket Elements
    const confirmedTicket = document.getElementById('confirmedTicket');
    const ticketId = document.getElementById('ticketId');
    const ticketSlot = document.getElementById('ticketSlot');
    const ticketVehicle = document.getElementById('ticketVehicle');
    const ticketAmount = document.getElementById('ticketAmount');
    const ticketStatusBadge = document.getElementById('ticketStatusBadge');
    const btnNewBooking = document.getElementById('btnNewBooking');

    // 1. Clock Updates
    function updateClock() {
        const now = new Date();
        timeDisplay.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Navigation Tab Switcher
    function switchTab(targetTabId) {
        navTabs.forEach(tab => {
            if (tab.getAttribute('data-tab') === targetTabId) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        tabContents.forEach(content => {
            if (content.id === targetTabId) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        // Trigger screen specific data loads
        if (targetTabId === 'tab-area-details') fetchAreaDetails();
        if (targetTabId === 'tab-slot-selection') fetchInteractiveSlots();
        if (targetTabId === 'tab-vehicle-selection') fetchVehicles();
        if (targetTabId === 'tab-booking-summary') updateSummaryView();
    }

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.getAttribute('data-tab'));
        });
    });

    // 3. Fetch Live Telemetry Stats (Tab 1 & Background)
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

            // Also update Screen 2 detail values if active
            if (detailTotal) detailTotal.textContent = data.total_slots;
            if (detailAvailable) detailAvailable.textContent = data.available_slots;
            if (detailOccupied) detailOccupied.textContent = data.occupied_slots;
            if (detailOccupancyPct) detailOccupancyPct.textContent = `${Math.round(data.occupancy_rate)}%`;
        } catch (err) {
            console.error('Telemetry fetch error:', err);
        }
    }

    setInterval(fetchStats, 1000);
    fetchStats();

    // 4. SCREEN 2: PARKING AREA DETAILS API
    async function fetchAreaDetails() {
        try {
            const res = await fetch('/api/parking-areas/1');
            if (!res.ok) return;
            const data = await res.json();

            detailTotal.textContent = data.totalSlots;
            detailAvailable.textContent = data.availableSlots;
            detailOccupied.textContent = data.occupiedSlots;
            detailOccupancyPct.textContent = `${data.occupancyPercentage}%`;
        } catch (err) {
            console.error('Area details fetch error:', err);
        }
    }

    btnViewAvailableSlots.addEventListener('click', () => {
        switchTab('tab-slot-selection');
    });

    btnGetDirections.addEventListener('click', () => {
        window.open('https://maps.google.com/?q=City+Mall+Parking', '_blank');
    });

    // 5. SCREEN 3: INTERACTIVE SLOT SELECTION API
    async function fetchInteractiveSlots() {
        try {
            const res = await fetch('/api/parking-areas/1/slots');
            if (!res.ok) return;
            const data = await res.json();
            renderInteractiveSlots(data.slots || []);
        } catch (err) {
            console.error('Slots fetch error:', err);
        }
    }

    function renderInteractiveSlots(slots) {
        slotsInteractiveGrid.innerHTML = slots.map(slot => {
            const status = slot.status || 'AVAILABLE';
            const isSelected = selectedSlot && selectedSlot.id === slot.id;

            let statusClass = 'available';
            if (status === 'OCCUPIED') statusClass = 'occupied';
            if (status === 'RESERVED') statusClass = 'reserved';
            if (isSelected) statusClass += ' selected';

            return `
                <div class="slot-card ${statusClass}" data-id="${slot.id}" data-number="${slot.slotNumber}" data-status="${status}">
                    <span class="slot-card-number">${slot.slotNumber}</span>
                    <span class="slot-card-status">${status}</span>
                </div>
            `;
        }).join('');

        // Attach click listeners to available slots
        document.querySelectorAll('.slot-card').forEach(card => {
            card.addEventListener('click', () => {
                const status = card.getAttribute('data-status');
                if (status !== 'AVAILABLE') return;

                const id = parseInt(card.getAttribute('data-id'));
                const slotNumber = card.getAttribute('data-number');

                selectedSlot = { id, slotNumber };
                selectedSlotLabel.textContent = slotNumber;
                btnSlotContinue.disabled = false;

                // Refresh visual selections
                renderInteractiveSlots(slots);
            });
        });
    }

    btnSlotContinue.addEventListener('click', () => {
        if (!selectedSlot) return;
        switchTab('tab-vehicle-selection');
    });

    // 6. SCREEN 4: VEHICLE SELECTION API
    async function fetchVehicles() {
        try {
            const res = await fetch('/api/vehicles');
            if (!res.ok) return;
            vehiclesList = await res.json();
            renderVehicles();
        } catch (err) {
            console.error('Vehicles fetch error:', err);
        }
    }

    function renderVehicles() {
        if (vehiclesList.length === 0) {
            vehiclesListEl.innerHTML = '<p class="text-muted">No registered vehicles found. Click "+ Add Vehicle" to add one.</p>';
            return;
        }

        // Default select first vehicle if none selected
        if (!selectedVehicle && vehiclesList.length > 0) {
            selectedVehicle = vehiclesList[0];
            btnSlotVehicleContinue.disabled = false;
        }

        vehiclesListEl.innerHTML = vehiclesList.map(v => {
            const isSelected = selectedVehicle && selectedVehicle.id === v.id;
            return `
                <div class="vehicle-card ${isSelected ? 'selected' : ''}" data-id="${v.id}">
                    <div class="vehicle-info">
                        <div class="radio-dot"></div>
                        <div>
                            <div class="vehicle-num">${v.vehicleNumber}</div>
                            <div class="vehicle-type-tag">${v.vehicleType}</div>
                        </div>
                    </div>
                    <i data-lucide="car" style="color: var(--text-muted);"></i>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();

        document.querySelectorAll('.vehicle-card').forEach(card => {
            card.addEventListener('click', () => {
                const vId = parseInt(card.getAttribute('data-id'));
                selectedVehicle = vehiclesList.find(v => v.id === vId);
                btnSlotVehicleContinue.disabled = false;
                renderVehicles();
            });
        });
    }

    btnSlotVehicleContinue.addEventListener('click', () => {
        if (!selectedVehicle) return;
        switchTab('tab-booking-summary');
    });

    // Add Vehicle Modal Handlers
    btnOpenAddVehicle.addEventListener('click', () => {
        addVehicleModal.style.display = 'flex';
    });

    function closeModal() {
        addVehicleModal.style.display = 'none';
        formAddVehicle.reset();
    }

    btnCloseAddVehicle.addEventListener('click', closeModal);
    btnCancelAddVehicle.addEventListener('click', closeModal);

    formAddVehicle.addEventListener('submit', async (e) => {
        e.preventDefault();
        const vNum = document.getElementById('vehicleNumberInput').value.trim();
        const vType = document.getElementById('vehicleTypeInput').value;

        if (!vNum) return;

        try {
            const res = await fetch('/api/vehicles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicleNumber: vNum, vehicleType: vType })
            });

            if (res.ok) {
                const newV = await res.json();
                selectedVehicle = newV;
                btnSlotVehicleContinue.disabled = false;
                closeModal();
                fetchVehicles();
            }
        } catch (err) {
            console.error('Save vehicle error:', err);
        }
    });

    // 7. SCREEN 5: BOOKING CONFIRMATION API
    function updateSummaryView() {
        if (selectedSlot) {
            sumSlotNumber.textContent = selectedSlot.slotNumber;
        } else {
            sumSlotNumber.textContent = 'None';
        }

        if (selectedVehicle) {
            sumVehicleNumber.textContent = `${selectedVehicle.vehicleNumber} (${selectedVehicle.vehicleType})`;
        } else {
            sumVehicleNumber.textContent = 'None';
        }

        sumParkingFee.textContent = '₹50';
    }

    btnConfirmBooking.addEventListener('click', async () => {
        if (!selectedSlot || !selectedVehicle) {
            alert('Please select a parking slot and vehicle first.');
            return;
        }

        const payload = {
            parkingAreaId: 1,
            parkingSlotId: selectedSlot.id,
            vehicleId: selectedVehicle.id,
            durationHours: 1
        };

        try {
            const res = await fetch('/api/bookings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const booking = await res.json();
                
                // Render Confirmed Ticket
                ticketId.textContent = `#${booking.bookingId}`;
                ticketSlot.textContent = selectedSlot.slotNumber;
                ticketVehicle.textContent = selectedVehicle.vehicleNumber;
                ticketAmount.textContent = `₹${booking.amount}`;
                ticketStatusBadge.textContent = booking.status || 'PENDING_PAYMENT';

                summaryCard.style.display = 'none';
                confirmedTicket.style.display = 'flex';
                
                if (window.lucide) lucide.createIcons();
            }
        } catch (err) {
            console.error('Create booking error:', err);
        }
    });

    btnNewBooking.addEventListener('click', () => {
        selectedSlot = null;
        selectedSlotLabel.textContent = 'None';
        btnSlotContinue.disabled = true;
        summaryCard.style.display = 'flex';
        confirmedTicket.style.display = 'none';
        switchTab('tab-slot-selection');
    });

    // 8. Config Sliders Handling (Tab 1 Monitor)
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

    btnResetConfig.addEventListener('click', () => {
        playbackSpeedInput.value = 1.5;
        pixelThresholdInput.value = 900;
        blurKernelInput.value = 3;
        blockSizeInput.value = 25;
        cValInput.value = 16;
        sendConfig();
    });

    // 9. Video Stream Play/Pause Toggle
    btnTogglePlay.addEventListener('click', () => {
        isPlaying = !isPlaying;
        if (isPlaying) {
            videoStream.src = '/video_feed';
        } else {
            videoStream.src = '';
        }
    });

    // 10. Fullscreen Toggle
    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            videoContainer.requestFullscreen().catch(err => console.error(err));
        } else {
            document.exitFullscreen();
        }
    });
});

