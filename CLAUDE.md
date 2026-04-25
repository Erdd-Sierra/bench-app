# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Bench Map Tokyo — a web app helping foreign tourists find public benches in Tokyo's 23 wards. English-only UI. Data from OpenStreetMap via the Overpass API, supplemented by user submissions.

## Running the App

```bash
pip install -r requirements.txt
python app.py
```

Serves at http://localhost:5000. No build step, no bundler, no test framework.

## Architecture

**Backend**: Single-file Flask server (`app.py`) with four routes:
- `GET /` — renders the Jinja2 template
- `GET /api/benches` — proxies Overpass API, merges with user-submitted benches, returns JSON. Caches Overpass results in `_cache` dict (1-hour TTL). Falls back to `FALLBACK_BENCHES` (~200 hardcoded locations) if Overpass fails or returns empty.
- `GET /api/search?q=...` — proxies Nominatim geocoding, bounded to Tokyo 23 wards
- `POST /api/benches/submit` — stores user-submitted benches in `data/user_benches.json`

**Frontend**: Vanilla JS, no build system. Five IIFE modules loaded via `<script>` tags in strict dependency order — globals: `Utils`, `MapModule`, `Geolocation`, `UI`. Entry point `app.js` is an anonymous IIFE.

Script load order matters (`templates/index.html`): `utils.js` → `map.js` → `geolocation.js` → `ui.js` → `app.js`.

**External dependencies** (all CDN, no npm):
- Leaflet 1.9.4, Leaflet.markercluster 1.5.3, CartoDB Voyager tiles, Inter font

## Key Design Decisions

- **No frameworks/bundlers**: IIFE revealing module pattern. Adding ES module imports would require a bundler.
- **Server-side proxies**: Browser never calls Overpass or Nominatim directly — `app.py` proxies and caches to avoid rate-limiting and CORS issues.
- **BEM-ish CSS**: Split into `main.css` (variables/reset/layout), `map.css` (Leaflet overrides), `components.css` (sidebar, modal, buttons, mobile drawer).
- **Mobile responsive**: Sidebar becomes bottom drawer at ≤768px via `.is-open` class and swipe gestures on `#sidebar-handle`.

## Map Bounds

The Leaflet map is restricted to Tokyo 23 wards via `maxBounds` in `MapModule.init()` (SW: `35.518,139.560` / NE: `35.818,139.920`), `minZoom: 11`, `maxBoundsViscosity: 1.0`.

## Bench Data Flow

1. Overpass query fetches `amenity=bench` nodes within `東京都区部`. On failure → `FALLBACK_BENCHES` (~200 hardcoded locations across all 23 wards).
2. User-submitted benches stored in `data/user_benches.json` with `"source": "user"` field.
3. `GET /api/benches` merges both sources. Frontend uses `bench.source === 'user'` to select the orange marker icon (`bench-user.svg`) vs teal (`bench.svg`).

## Bench Registration (2-Step Placement Flow)

The add-bench flow is split into two steps to avoid the modal blocking map interaction:

1. **Step 1**: User clicks "Add Bench" button → `UI.showMapHint()` displays instruction banner on map, `MapModule.enablePlacement()` sets crosshair cursor. Modal is NOT shown yet.
2. **Step 2**: User clicks on map → orange pin placed (draggable), `UI.showBenchModal()` opens the form. `UI.updateModalPosition()` updates lat/lon on pin drag.
3. Submit → `POST /api/benches/submit` → re-fetch all benches → update map and stats.

Cancel via: hint banner ✕, Add Bench button toggle, or modal Cancel/✕.

## CSS Variables

Design system lives in `:root` in `static/css/main.css`. Primary accent: `--color-primary: #2A9D8F`. User-submitted bench accent: `#E76F51`.
