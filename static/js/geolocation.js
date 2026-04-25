/**
 * Geolocation module — browser location handling.
 */
const Geolocation = (() => {
    let userMarker = null;
    let pulseMarker = null;
    let userPosition = null;
    let watchId = null;

    /**
     * Request the user's location.
     * Returns a Promise that resolves with { lat, lon }.
     */
    function locate() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported by your browser.'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    userPosition = {
                        lat: pos.coords.latitude,
                        lon: pos.coords.longitude,
                    };
                    resolve(userPosition);
                },
                (err) => {
                    reject(err);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000,
                }
            );
        });
    }

    /**
     * Show user location on the map.
     */
    function showOnMap(map, lat, lon) {
        const latlng = [lat, lon];

        // Remove existing markers
        if (userMarker) map.removeLayer(userMarker);
        if (pulseMarker) map.removeLayer(pulseMarker);

        // Pulse ring
        pulseMarker = L.marker(latlng, {
            icon: L.divIcon({
                className: 'user-location-pulse',
                iconSize: [40, 40],
                iconAnchor: [20, 20],
            }),
            interactive: false,
        }).addTo(map);

        // Solid dot
        userMarker = L.marker(latlng, {
            icon: L.divIcon({
                className: 'user-location-marker',
                iconSize: [16, 16],
                iconAnchor: [8, 8],
            }),
            interactive: false,
            zIndexOffset: 1000,
        }).addTo(map);

        map.setView(latlng, 15, { animate: true });
    }

    /**
     * Start watching position for updates.
     */
    function watch(map, onUpdate) {
        if (!navigator.geolocation) return;

        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
        }

        watchId = navigator.geolocation.watchPosition(
            (pos) => {
                userPosition = {
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                };
                showOnMap(map, userPosition.lat, userPosition.lon);
                if (onUpdate) onUpdate(userPosition);
            },
            () => {},
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 30000,
            }
        );
    }

    function getPosition() {
        return userPosition;
    }

    return { locate, showOnMap, watch, getPosition };
})();
