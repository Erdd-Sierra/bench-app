/**
 * UI module — sidebar, search, modal, nearest bench list, responsive behavior.
 */
const UI = (() => {
    const NEAREST_COUNT = 15;
    let allBenches = [];

    // -----------------------------------------------------------------------
    // Loading
    // -----------------------------------------------------------------------
    function showLoading() {
        const el = document.getElementById('sidebar-loading');
        if (el) el.style.display = 'flex';
        document.getElementById('nearest-section').style.display = 'none';
        document.getElementById('stats-section').style.display = 'none';
    }

    function hideLoading() {
        const el = document.getElementById('sidebar-loading');
        if (el) el.style.display = 'none';
        document.getElementById('nearest-section').style.display = 'block';
        document.getElementById('stats-section').style.display = 'block';
    }

    // -----------------------------------------------------------------------
    // Stats
    // -----------------------------------------------------------------------
    function updateStats(benches) {
        allBenches = benches;
        document.getElementById('stat-total').textContent = benches.length.toLocaleString();
        const covered = benches.filter((b) => b.tags && b.tags.covered === 'yes').length;
        document.getElementById('stat-covered').textContent = covered.toLocaleString();
        const backrest = benches.filter((b) => b.tags && b.tags.backrest === 'yes').length;
        document.getElementById('stat-backrest').textContent = backrest.toLocaleString();
    }

    // -----------------------------------------------------------------------
    // Nearest Bench List
    // -----------------------------------------------------------------------
    function renderNearestBenches(userLat, userLon, onBenchClick) {
        const list = document.getElementById('bench-list');
        list.innerHTML = '';

        const sorted = allBenches
            .map((bench) => ({
                ...bench,
                distance: Utils.haversine(userLat, userLon, bench.lat, bench.lon),
            }))
            .sort((a, b) => a.distance - b.distance)
            .slice(0, NEAREST_COUNT);

        sorted.forEach((bench, i) => {
            const li = document.createElement('li');
            li.className = 'bench-list__item';
            li.style.animationDelay = `${i * 0.05}s`;

            const tags = bench.tags || {};
            const details = [];
            if (tags.covered === 'yes') details.push('Covered');
            if (tags.backrest === 'yes') details.push('Backrest');
            if (tags.material) details.push(Utils.capitalize(tags.material));
            if (bench.source === 'user') details.push('User');

            li.innerHTML = `
                <div class="bench-list__item-header">
                    <span class="bench-list__item-name">${Utils.benchLabel(tags)}</span>
                    <span class="bench-list__item-distance">${Utils.formatDistance(bench.distance)}</span>
                </div>
                ${details.length > 0
                    ? `<div class="bench-list__item-details">
                        ${details.map((d) => `<span class="bench-list__item-tag">${d}</span>`).join('')}
                       </div>`
                    : ''}
            `;

            li.addEventListener('click', () => {
                if (onBenchClick) onBenchClick(bench);
            });

            list.appendChild(li);
        });
    }

    function showLocationHint() {
        const list = document.getElementById('bench-list');
        list.innerHTML = `
            <li class="bench-list__item" style="opacity:1; text-align:center; cursor:default;">
                <p style="color: var(--color-text-secondary); font-size: var(--font-size-sm);">
                    Tap <strong>Locate Me</strong> to see nearby benches sorted by distance.
                </p>
            </li>
        `;
    }

    // -----------------------------------------------------------------------
    // Mobile Drawer
    // -----------------------------------------------------------------------
    function initMobileDrawer() {
        const sidebar = document.getElementById('sidebar');
        const handle = document.getElementById('sidebar-handle');
        if (!handle || !sidebar) return;

        handle.addEventListener('click', () => {
            sidebar.classList.toggle('is-open');
        });

        let startY = 0;
        handle.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        }, { passive: true });

        handle.addEventListener('touchend', (e) => {
            const endY = e.changedTouches[0].clientY;
            const diff = startY - endY;
            if (diff > 30) {
                sidebar.classList.add('is-open');
            } else if (diff < -30) {
                sidebar.classList.remove('is-open');
            }
        }, { passive: true });
    }

    // -----------------------------------------------------------------------
    // Search
    // -----------------------------------------------------------------------
    function initSearch(onSelect) {
        const input = document.getElementById('search-input');
        const resultsList = document.getElementById('search-results');
        if (!input || !resultsList) return;

        const doSearch = Utils.debounce(async (query) => {
            if (query.length < 2) {
                resultsList.style.display = 'none';
                return;
            }
            try {
                const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const results = await resp.json();
                renderSearchResults(results, onSelect);
            } catch (err) {
                resultsList.style.display = 'none';
            }
        }, 350);

        input.addEventListener('input', () => {
            doSearch(input.value.trim());
        });

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#search-container')) {
                resultsList.style.display = 'none';
            }
        });

        // Close on Escape
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                resultsList.style.display = 'none';
                input.blur();
            }
        });
    }

    function renderSearchResults(results, onSelect) {
        const resultsList = document.getElementById('search-results');
        const input = document.getElementById('search-input');
        resultsList.innerHTML = '';

        if (results.length === 0) {
            resultsList.style.display = 'none';
            return;
        }

        results.forEach((r) => {
            const li = document.createElement('li');
            li.className = 'search-results__item';
            // Shorten name: take first 2 segments
            const parts = r.name.split(', ');
            li.textContent = parts.slice(0, 2).join(', ');
            li.addEventListener('click', () => {
                if (onSelect) onSelect(r);
                resultsList.style.display = 'none';
                input.value = parts.slice(0, 2).join(', ');
            });
            resultsList.appendChild(li);
        });

        resultsList.style.display = 'block';
    }

    function clearSearch() {
        const input = document.getElementById('search-input');
        const resultsList = document.getElementById('search-results');
        if (input) input.value = '';
        if (resultsList) resultsList.style.display = 'none';
    }

    // -----------------------------------------------------------------------
    // Map Hint Banner
    // -----------------------------------------------------------------------
    function showMapHint() {
        const el = document.getElementById('map-hint');
        if (el) el.style.display = 'flex';
    }

    function hideMapHint() {
        const el = document.getElementById('map-hint');
        if (el) el.style.display = 'none';
    }

    // -----------------------------------------------------------------------
    // Bench Submission Modal
    // -----------------------------------------------------------------------
    let modalSubmitHandler = null;

    function showBenchModal(onSubmit) {
        const modal = document.getElementById('bench-modal');
        const submitBtn = document.getElementById('modal-submit');
        const cancelBtn = document.getElementById('modal-cancel');
        const closeBtn = document.getElementById('modal-close');
        const form = document.getElementById('bench-form');

        // Reset form
        form.reset();
        document.getElementById('bench-lat').value = '';
        document.getElementById('bench-lon').value = '';
        submitBtn.disabled = true;
        document.getElementById('modal-hint').textContent = 'Click on the map to place the bench, then fill in the details.';

        modal.style.display = 'flex';

        // Clean up old handler
        if (modalSubmitHandler) {
            submitBtn.removeEventListener('click', modalSubmitHandler);
        }

        modalSubmitHandler = () => {
            const lat = parseFloat(document.getElementById('bench-lat').value);
            const lon = parseFloat(document.getElementById('bench-lon').value);
            if (isNaN(lat) || isNaN(lon)) return;

            const tags = {};
            const name = document.getElementById('bench-name').value.trim();
            if (name) tags.name = name;

            const material = document.getElementById('bench-material').value;
            if (material) tags.material = material;

            const seats = document.getElementById('bench-seats').value;
            if (seats) tags.seats = seats;

            if (document.getElementById('bench-backrest').checked) tags.backrest = 'yes';
            if (document.getElementById('bench-covered').checked) tags.covered = 'yes';

            const notes = document.getElementById('bench-notes').value.trim();
            if (notes) tags.notes = notes;

            if (onSubmit) onSubmit({ lat, lon, tags });
        };

        submitBtn.addEventListener('click', modalSubmitHandler);

        const closeModal = () => {
            hideBenchModal();
        };
        cancelBtn.onclick = closeModal;
        closeBtn.onclick = closeModal;
    }

    function updateModalPosition(lat, lon) {
        document.getElementById('bench-lat').value = lat;
        document.getElementById('bench-lon').value = lon;
        document.getElementById('modal-submit').disabled = false;
        document.getElementById('modal-hint').textContent =
            `Location: ${lat.toFixed(5)}, ${lon.toFixed(5)} — drag the marker to adjust.`;
    }

    function hideBenchModal() {
        document.getElementById('bench-modal').style.display = 'none';
    }

    return {
        showLoading,
        hideLoading,
        updateStats,
        renderNearestBenches,
        showLocationHint,
        initMobileDrawer,
        initSearch,
        clearSearch,
        showMapHint,
        hideMapHint,
        showBenchModal,
        updateModalPosition,
        hideBenchModal,
    };
})();
