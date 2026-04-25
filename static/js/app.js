/**
 * App entry point — wires modules together, initializes the application.
 */
(function () {
    'use strict';

    let benchData = [];

    async function fetchBenches() {
        const resp = await fetch('/api/benches');
        if (!resp.ok) throw new Error(`Failed to fetch benches: ${resp.status}`);
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        return data.benches;
    }

    async function submitBench(benchInfo) {
        const resp = await fetch('/api/benches/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(benchInfo),
        });
        if (!resp.ok) throw new Error(`Failed to submit bench: ${resp.status}`);
        return resp.json();
    }

    async function init() {
        // Initialize map
        const map = MapModule.init('map');

        // Initialize mobile drawer
        UI.initMobileDrawer();

        // Initialize search
        UI.initSearch((result) => {
            map.setView([result.lat, result.lon], 16, { animate: true });
        });

        // Show loading state
        UI.showLoading();

        // Fetch bench data
        try {
            benchData = await fetchBenches();
            MapModule.addBenches(benchData);
            UI.updateStats(benchData);
            UI.hideLoading();
            UI.showLocationHint();
        } catch (err) {
            console.error('Error loading benches:', err);
            UI.hideLoading();
            document.getElementById('bench-list').innerHTML = `
                <li class="bench-list__item" style="opacity:1; text-align:center; cursor:default;">
                    <p style="color: var(--color-text-secondary); font-size: var(--font-size-sm);">
                        Failed to load bench data. Please try refreshing the page.
                    </p>
                </li>
            `;
            document.getElementById('nearest-section').style.display = 'block';
            document.getElementById('stats-section').style.display = 'block';
        }

        // ------------------------------------------------------------------
        // Locate Me button
        // ------------------------------------------------------------------
        const locateBtn = document.getElementById('locate-btn');
        locateBtn.addEventListener('click', async () => {
            locateBtn.classList.add('is-active');
            try {
                const pos = await Geolocation.locate();
                Geolocation.showOnMap(map, pos.lat, pos.lon);

                UI.renderNearestBenches(pos.lat, pos.lon, (bench) => {
                    MapModule.focusBench(bench);
                    if (window.innerWidth <= 768) {
                        document.getElementById('sidebar').classList.remove('is-open');
                    }
                });

                Geolocation.watch(map, (newPos) => {
                    UI.renderNearestBenches(newPos.lat, newPos.lon, (bench) => {
                        MapModule.focusBench(bench);
                    });
                });
            } catch (err) {
                console.error('Geolocation error:', err);
                locateBtn.classList.remove('is-active');
                alert('Could not determine your location. Please enable location services and try again.');
            }
        });

        // ------------------------------------------------------------------
        // Add Bench flow (2-step: place pin first, then show form)
        // ------------------------------------------------------------------
        const addBenchBtn = document.getElementById('add-bench-btn');

        function cancelPlacement() {
            addBenchBtn.classList.remove('is-active');
            MapModule.disablePlacement();
            UI.hideBenchModal();
            UI.hideMapHint();
        }

        addBenchBtn.addEventListener('click', () => {
            // Toggle off if already active
            if (addBenchBtn.classList.contains('is-active')) {
                cancelPlacement();
                return;
            }

            // Step 1: Enter placement mode — show hint banner, crosshair cursor
            addBenchBtn.classList.add('is-active');
            UI.showMapHint();

            let pinPlaced = false;

            MapModule.enablePlacement((pos) => {
                if (!pinPlaced) {
                    // Step 2: First click — pin placed, now show the modal form
                    pinPlaced = true;
                    UI.showBenchModal(async (benchInfo) => {
                        try {
                            await submitBench(benchInfo);
                            UI.hideBenchModal();
                            MapModule.disablePlacement();
                            addBenchBtn.classList.remove('is-active');
                            UI.hideMapHint();

                            benchData = await fetchBenches();
                            MapModule.addBenches(benchData);
                            UI.updateStats(benchData);

                            const userPos = Geolocation.getPosition();
                            if (userPos) {
                                UI.renderNearestBenches(userPos.lat, userPos.lon, (bench) => {
                                    MapModule.focusBench(bench);
                                });
                            }
                        } catch (err) {
                            console.error('Submit error:', err);
                            alert('Failed to submit bench. Please try again.');
                        }
                    });
                }
                // Update position in the modal (works for first click and subsequent drags)
                UI.updateModalPosition(pos.lat, pos.lon);
            });
        });

        // Cancel buttons in modal also cancel placement
        document.getElementById('modal-cancel').addEventListener('click', cancelPlacement);
        document.getElementById('modal-close').addEventListener('click', cancelPlacement);
        document.getElementById('map-hint-cancel').addEventListener('click', cancelPlacement);
    }

    // Start the app
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
