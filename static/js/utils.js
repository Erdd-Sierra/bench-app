/**
 * Utility functions for Bench Map Tokyo.
 */
const Utils = (() => {
    const R = 6371e3; // Earth radius in meters

    /**
     * Calculate distance between two lat/lon points using Haversine formula.
     * Returns distance in meters.
     */
    function haversine(lat1, lon1, lat2, lon2) {
        const toRad = (deg) => (deg * Math.PI) / 180;
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * Format distance for display.
     */
    function formatDistance(meters) {
        if (meters < 1000) {
            return `${Math.round(meters)} m`;
        }
        return `${(meters / 1000).toFixed(1)} km`;
    }

    /**
     * Build a descriptive label for a bench from its tags.
     */
    function benchLabel(tags) {
        if (tags.name) return tags.name;
        const parts = [];
        if (tags.covered === 'yes') parts.push('Covered');
        if (tags.backrest === 'yes') parts.push('Backrest');
        if (tags.material) parts.push(capitalize(tags.material));
        return parts.length > 0 ? parts.join(', ') : 'Bench';
    }

    /**
     * Capitalize first letter.
     */
    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Debounce a function.
     */
    function debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    return { haversine, formatDistance, benchLabel, capitalize, debounce };
})();
