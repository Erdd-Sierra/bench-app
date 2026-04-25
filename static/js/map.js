/**
 * Map module — Leaflet initialization, tile layer, markers, popups, placement mode.
 */
const MapModule = (() => {
    let map;
    let clusterGroup;
    let benchMarkers = [];
    let tempMarker = null;
    let placementCallback = null;
    let placementActive = false;

    const TOKYO_CENTER = [35.6762, 139.6503];
    const DEFAULT_ZOOM = 12;
    const TOKYO_BOUNDS = L.latLngBounds(
        [35.518, 139.560],  // Southwest
        [35.818, 139.920]   // Northeast
    );

    const benchIcon = L.icon({
        iconUrl: '/static/icons/bench.svg',
        iconSize: [28, 35],
        iconAnchor: [14, 35],
        popupAnchor: [0, -36],
        className: 'bench-marker',
    });

    const userBenchIcon = L.icon({
        iconUrl: '/static/icons/bench-user.svg',
        iconSize: [28, 35],
        iconAnchor: [14, 35],
        popupAnchor: [0, -36],
        className: 'bench-marker bench-marker--user',
    });

    /**
     * Initialize the Leaflet map.
     */
    function init(containerId) {
        map = L.map(containerId, {
            center: TOKYO_CENTER,
            zoom: DEFAULT_ZOOM,
            minZoom: 11,
            maxBounds: TOKYO_BOUNDS,
            maxBoundsViscosity: 1.0,
            zoomControl: true,
            attributionControl: true,
        });

        // CartoDB Voyager tiles
        L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 19,
            }
        ).addTo(map);

        // Initialize marker cluster group
        clusterGroup = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            iconCreateFunction: function (cluster) {
                const count = cluster.getChildCount();
                let size = 'small';
                if (count >= 50) size = 'large';
                else if (count >= 20) size = 'medium';
                return L.divIcon({
                    html: `<div>${count}</div>`,
                    className: `marker-cluster marker-cluster-${size}`,
                    iconSize: L.point(46, 46),
                });
            },
        });
        map.addLayer(clusterGroup);

        // Placement mode click handler
        map.on('click', function (e) {
            if (!placementActive) return;
            const latlng = e.latlng;

            // Remove previous temp marker
            if (tempMarker) {
                map.removeLayer(tempMarker);
            }

            tempMarker = L.marker([latlng.lat, latlng.lng], {
                icon: userBenchIcon,
                draggable: true,
            }).addTo(map);

            if (placementCallback) {
                placementCallback({ lat: latlng.lat, lon: latlng.lng });
            }

            // Update callback on drag
            tempMarker.on('dragend', function () {
                const pos = tempMarker.getLatLng();
                if (placementCallback) {
                    placementCallback({ lat: pos.lat, lon: pos.lng });
                }
            });
        });

        return map;
    }

    /**
     * Add bench markers to the map.
     */
    function addBenches(benches) {
        clusterGroup.clearLayers();
        benchMarkers = [];

        benches.forEach((bench) => {
            const icon = bench.source === 'user' ? userBenchIcon : benchIcon;
            const marker = L.marker([bench.lat, bench.lon], { icon: icon });
            marker.benchData = bench;

            marker.bindPopup(() => buildPopupContent(bench), {
                maxWidth: 260,
                className: 'bench-popup-wrapper',
            });

            marker.on('click', () => {
                map.setView([bench.lat, bench.lon], Math.max(map.getZoom(), 16), {
                    animate: true,
                });
            });

            benchMarkers.push(marker);
            clusterGroup.addLayer(marker);
        });
    }

    /**
     * Build HTML content for a bench popup.
     */
    function buildPopupContent(bench) {
        const tags = bench.tags || {};
        const isUser = bench.source === 'user';
        const displayTags = [
            'material', 'backrest', 'covered', 'colour', 'seats',
            'surface', 'direction', 'operator',
        ];

        let tagsHtml = '';
        displayTags.forEach((key) => {
            if (tags[key]) {
                tagsHtml += `
                    <div class="bench-popup__tag">
                        <span class="bench-popup__tag-key">${Utils.capitalize(key)}</span>
                        <span class="bench-popup__tag-value">${Utils.capitalize(tags[key])}</span>
                    </div>`;
            }
        });

        if (tags.notes) {
            tagsHtml += `
                <div class="bench-popup__tag">
                    <span class="bench-popup__tag-key">Notes</span>
                    <span class="bench-popup__tag-value">${tags.notes}</span>
                </div>`;
        }

        if (!tagsHtml) {
            tagsHtml = '<div class="bench-popup__tag"><span class="bench-popup__tag-key" style="color:var(--color-text-muted)">No additional details</span></div>';
        }

        const sourceTag = isUser
            ? '<div class="bench-popup__source">User-submitted</div>'
            : '';

        return `
            <div class="bench-popup">
                <div class="bench-popup__title">${Utils.benchLabel(tags)}</div>
                ${sourceTag}
                <div class="bench-popup__tags">${tagsHtml}</div>
            </div>`;
    }

    /**
     * Pan to a specific bench and open its popup.
     */
    function focusBench(bench) {
        const marker = benchMarkers.find(
            (m) => m.benchData.id === bench.id
        );
        if (marker) {
            clusterGroup.zoomToShowLayer(marker, () => {
                marker.openPopup();
            });
        }
    }

    /**
     * Enable placement mode — next map click places a temp marker.
     */
    function enablePlacement(callback) {
        placementActive = true;
        placementCallback = callback;
        map.getContainer().classList.add('placement-active');
    }

    /**
     * Disable placement mode.
     */
    function disablePlacement() {
        placementActive = false;
        placementCallback = null;
        map.getContainer().classList.remove('placement-active');
        removeTempMarker();
    }

    /**
     * Remove the temporary placement marker.
     */
    function removeTempMarker() {
        if (tempMarker) {
            map.removeLayer(tempMarker);
            tempMarker = null;
        }
    }

    function getMap() {
        return map;
    }

    function getMarkers() {
        return benchMarkers;
    }

    return {
        init, addBenches, focusBench, getMap, getMarkers,
        enablePlacement, disablePlacement, removeTempMarker,
    };
})();
