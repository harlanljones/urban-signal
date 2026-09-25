"""Interactive Geospatial Web Visualization Dashboard HTML/JS/CSS generator for Urban Signal."""

from src.spatial.city_registry import REGISTRY


def get_favicon_svg() -> str:
    """Brand favicon: layered-map mark in the dashboard's accent palette."""
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        "<rect width='64' height='64' rx='14' fill='#0f172a'/>"
        "<path d='M32 12L12 22l20 10 20-10-20-10zM12 42l20 10 20-10M12 32l20 10 20-10' "
        "fill='none' stroke='#38bdf8' stroke-width='4' "
        "stroke-linecap='round' stroke-linejoin='round'/>"
        "</svg>"
    )

def _favicon_data_uri() -> str:
    return "data:image/svg+xml," + (
        get_favicon_svg()
        .replace("#", "%23")
        .replace(" ", "%20")
    )

def _metro_meta_js() -> str:
    """Render the METRO_META entries straight from REGISTRY (US-427).

    Single source of truth: a city registered in REGISTRY appears on the map
    with its registry display name; an unregistered city cannot. Entries keep
    the ``<id>: { name: '...' },`` JS shape the CI/CD pre-flight parser
    (scripts/verify_cicd_preflight.py) and the interlock gate read.
    """
    lines = []
    for cid, reg in REGISTRY.items():
        name = reg.name.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"      {cid.value}: {{ name: '{name}' }},")
    return "\n".join(lines)

def get_dashboard_html() -> str:
    favicon_link = (
        f'  <link rel="icon" type="image/svg+xml" href="{_favicon_data_uri()}">'
    )
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="description" content="Urban Signal — Real-Time Geospatial Intelligence & Commercial Catalyst Forecasting Engine">
  <title>Urban Signal — Real-Time Geospatial Intelligence & Catalyst Forecaster</title>
  __FAVICON_LINK__
  <link rel="ai-catalog" href="/.well-known/ai-catalog.json">
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  
  <!-- Third-party libraries are pinned by version AND by Subresource Integrity
       hash (sha384 of the published npm file), so a compromised or tampered CDN
       response is refused by the browser instead of executing. Bumping a version
       means recomputing its hash:
         npm pack <pkg>@<ver> && openssl dgst -sha384 -binary <file> | base64 -->
  <!-- MapLibre GL JS -->
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" integrity="sha384-p5cy4wHtKSqjnLUNjQ+8ffCwUp0vlLS+6lg1lc3qqXax2E1EmVCMCAimU+R0MOZH" crossorigin="anonymous" />
  <script defer src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js" integrity="sha384-3WUbXI7T+/GIrWP/5MDMjhzLyHQ+0utF3PnJ7ozD7UeN1/bbZ96Hk+Vvd024VYfW" crossorigin="anonymous"></script>
  
  <!-- Chart.js (chart.umd.js ships minified; the .min.js name is a jsDelivr
       on-the-fly minification whose bytes are not stable enough to hash) -->
  <script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js" integrity="sha384-dug+JxfBvklEQdJ4AYuBBAIScUz0bVN73xpy273gcAwHjb3qI0fXmuYNaNfdyYJG" crossorigin="anonymous"></script>
  
  <!-- H3 JS -->
  <script defer src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js" integrity="sha384-nKUDlg+fT0U/eEt4KWP9n034kLe/eVj6k7CVjbu6qfRhJdEyinlGajS9+9AU+UZ5" crossorigin="anonymous"></script>

  <style>
    :root {
      --bg-base: #080d17;
      --bg-surface: #0d1626;
      --bg-surface-elevated: #17253a;
      --bg-glass: rgba(13, 22, 38, 0.92);
      
      --border-subtle: rgba(148, 163, 184, 0.14);
      --border-focus: rgba(56, 189, 248, 0.65);
      --border-active: rgba(56, 189, 248, 0.42);
      
      --accent-primary: #38bdf8;
      --accent-primary-dim: rgba(56, 189, 248, 0.12);
      --accent-success: #34d399;
      --accent-success-dim: rgba(52, 211, 153, 0.12);
      --accent-warning: #fbbf24;
      --accent-warning-dim: rgba(251, 191, 36, 0.12);
      --accent-danger: #f43f5e;
      --accent-danger-dim: rgba(244, 63, 94, 0.12);
      --accent-purple: #c084fc;
      --accent-purple-dim: rgba(192, 132, 252, 0.12);
      --accent-emerald: #34d399;
      --accent-amber: #fbbf24;
      /* Top stop of the map ramp: "high signal" is an opportunity, not an error. */
      --signal-high: #e8a050;
      --accent-crimson: #f43f5e;
      
      --borough-manhattan: #38bdf8;
      --borough-brooklyn: #34d399;
      --borough-queens: #fbbf24;
      --borough-bronx: #f43f5e;
      --borough-staten: #c084fc;
      
      --division-sf-core: #38bdf8;
      --division-east-bay: #34d399;
      --division-peninsula: #fbbf24;
      --division-silicon-valley: #c084fc;
      --division-marin: #f43f5e;
      --division-wine-country: #e879f9;
      --division-solano: #22d3ee;
      --division-outer-contra-costa: #fb923c;
      
      --text-main: #f8fafc;
      --text-secondary: #a7b5c9;
      --text-muted: #8190a6;
      
      --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'IBM Plex Mono', monospace;
      
      --glass-blur: blur(12px);
      --radius-sm: 5px;
      --radius-md: 7px;
      --radius-lg: 10px;
      --shadow-dropdown: 0 18px 42px rgba(0, 0, 0, 0.48), 0 4px 12px rgba(0, 0, 0, 0.28);
      /* Surface overlays and tints (white / slate at fixed alphas). */
      --overlay-faint: rgba(255, 255, 255, 0.03);
      --overlay-soft: rgba(255, 255, 255, 0.05);
      --overlay-medium: rgba(255, 255, 255, 0.1);
      --overlay-strong: rgba(255, 255, 255, 0.15);
      --overlay-bold: rgba(255, 255, 255, 0.24);
      --neutral-tint-soft: rgba(148, 163, 184, 0.07);
      --neutral-tint: rgba(148, 163, 184, 0.1);
      --success-edge: rgba(52, 211, 153, 0.24);
      --no-data-fill: rgba(113, 129, 152, 0.18);
      --no-data-edge: rgba(113, 129, 152, 0.35);
      --baseline-hatch: rgba(113, 129, 152, 0.5);
      --scale-rule-edge: rgba(167, 181, 201, 0.7);
      --scale-rule-fill: rgba(167, 181, 201, 0.25);
      --toast-error-bg: rgba(30, 20, 28, 0.95);
      --toast-error-text: #fecdd3;
      --toast-warning-bg: rgba(30, 26, 18, 0.95);
      --toast-warning-text: #fef08a;
      --toast-success-bg: rgba(18, 30, 24, 0.95);
      --toast-success-text: #a7f3d0;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* Visually hidden, still announced by screen readers. */
    .sr-only {
      position: absolute;
      width: 1px; height: 1px;
      padding: 0; margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    ::selection {
      background: var(--accent-primary-dim);
      color: var(--accent-primary);
    }
    
    :focus-visible {
      outline: 2px solid var(--accent-primary);
      outline-offset: 2px;
    }

    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      caret-color: var(--accent-primary);
    }

    .num, .q-num, .catalyst-lims-tag, .score-hero-val, .horizon-mini-val, .telemetry-table .val {
      font-variant-numeric: tabular-nums;
    }

    /* Global Alert Toast / Notification Banner */
    #status-toast-container {
      position: fixed;
      top: 60px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1000;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
      width: 90%;
      max-width: 460px;
    }

    .toast-banner {
      pointer-events: auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 14px;
      border-radius: var(--radius-md);
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-dropdown);
      font-size: 12px;
      line-height: 1.4;
      animation: toastIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .toast-banner.error {
      border-color: var(--accent-danger);
      background: var(--toast-error-bg);
      color: var(--toast-error-text);
    }

    .toast-banner.warning {
      border-color: var(--accent-warning);
      background: var(--toast-warning-bg);
      color: var(--toast-warning-text);
    }

    .toast-banner.success {
      border-color: var(--accent-success);
      background: var(--toast-success-bg);
      color: var(--toast-success-text);
    }

    .toast-btn {
      background: var(--overlay-medium);
      border: 1px solid var(--overlay-bold);
      color: #fff;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s ease;
    }

    .toast-btn:hover {
      background: var(--overlay-bold);
    }

    @keyframes toastIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .toast-banner { animation: none; }
      /* Operate surface motion is restrained by design; under reduced-motion
         every hover/state transition and the zoom-hint fade go instant. */
      *,
      *::before,
      *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
      }
    }

    .pulse-dot.static { background: var(--text-muted); }

    .shap-empty {
      padding: 18px 14px;
      border: 1px dashed var(--border-subtle);
      border-radius: var(--radius-sm);
      color: var(--text-muted);
      font-size: 11px;
      text-align: center;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: var(--overlay-strong);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--overlay-bold);
    }

    /* Top Navigation Header */
    header {
      height: 56px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      z-index: 100;
      gap: 16px;
      flex-shrink: 0;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 11px;
      min-width: 0;
    }

    .brand-icon {
      width: 30px;
      height: 30px;
      background: var(--accent-primary-dim);
      border: 1px solid var(--border-active);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent-primary);
    }

    .brand-icon svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
    }

    .brand-title {
      font-size: 14px;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
    }

    .brand-badge {
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 500;
      padding: 1px 6px;
      background: var(--overlay-soft);
      color: var(--text-secondary);
      border-radius: 4px;
    }
    /* Metro chips are navigation only: they fly the camera and scope the
       catalyst feed list. Every metro's data stays rendered regardless. */
    #metro-chips {
      scrollbar-width: none;
    }
    #metro-chips::-webkit-scrollbar {
      display: none;
    }

    /* Shown when the camera sits below the lazy-load zoom floor. */
    .zoom-hint {
      position: absolute;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%);
      z-index: 10;
      padding: 7px 14px;
      background: rgba(8, 12, 20, 0.82);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      font-size: 11px;
      pointer-events: none;
      transition: opacity .25s ease;
    }
    .zoom-hint[hidden] { display: none; }

    /* Borough / Division Navigation Selector */
    .borough-nav {
      display: flex;
      align-items: center;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 2px;
      gap: 2px;
    }

    .borough-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 500;
      padding: 5px 10px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
    }

    .borough-btn:hover {
      color: var(--text-main);
      background: var(--overlay-soft);
    }

    .borough-btn.active {
      background: var(--bg-surface-elevated);
      color: var(--text-main);
      font-weight: 600;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }

    .borough-btn.active.Manhattan { color: var(--borough-manhattan); }
    .borough-btn.active.Brooklyn { color: var(--borough-brooklyn); }
    .borough-btn.active.Queens { color: var(--borough-queens); }
    .borough-btn.active.Bronx { color: var(--borough-bronx); }
    .borough-btn.active.StatenIsland { color: var(--borough-staten); }
    .borough-btn.active.CentralDowntown { color: var(--accent-primary); }
    .borough-btn.active.NorthSide { color: var(--accent-emerald); }
    .borough-btn.active.NorthwestSide { color: var(--accent-amber); }
    .borough-btn.active.SouthSide { color: var(--accent-crimson); }
    .borough-btn.active.FarNorthSide { color: var(--accent-purple); }
    .borough-btn.active.SouthwestSide { color: var(--accent-primary); }
    .borough-btn.active.SanFranciscoCore, .borough-btn.active.SAN_FRANCISCO_CORE, .borough-btn.active.SFCore { color: var(--division-sf-core); }
    .borough-btn.active.EastBay, .borough-btn.active.EAST_BAY { color: var(--division-east-bay); }
    .borough-btn.active.Peninsula, .borough-btn.active.PENINSULA { color: var(--division-peninsula); }
    .borough-btn.active.SiliconValleySouthBay, .borough-btn.active.SILICON_VALLEY_SOUTH_BAY, .borough-btn.active.SiliconValley { color: var(--division-silicon-valley); }
    .borough-btn.active.MarinNorthBay, .borough-btn.active.MARIN_NORTH_BAY, .borough-btn.active.Marin { color: var(--division-marin); }
    .borough-btn.active.NorthBayWineCountry, .borough-btn.active.NORTH_BAY_WINE_COUNTRY, .borough-btn.active.WineCountry { color: var(--division-wine-country); }
    .borough-btn.active.SolanoCorridor, .borough-btn.active.SOLANO_CORRIDOR, .borough-btn.active.Solano { color: var(--division-solano); }
    .borough-btn.active.OuterContraCosta, .borough-btn.active.OUTER_CONTRA_COSTA, .borough-btn.active.OuterCC { color: var(--division-outer-contra-costa); }
    .borough-btn.active.SeattleCore, .borough-btn.active.SEATTLE_CORE { color: var(--accent-primary); }
    .borough-btn.active.NorthKing, .borough-btn.active.NORTH_KING { color: var(--accent-success); }
    .borough-btn.active.Eastside, .borough-btn.active.EASTSIDE { color: var(--accent-purple); }
    .borough-btn.active.SouthKing, .borough-btn.active.SOUTH_KING { color: var(--accent-warning); }
    /* Los Angeles divisions */
    .borough-btn.active.CentralLA, .borough-btn.active.CENTRALLA { color: var(--accent-primary); }
    .borough-btn.active.Westside, .borough-btn.active.WESTSIDE { color: var(--accent-success); }
    .borough-btn.active.SanFernandoValley, .borough-btn.active.SANFERNANDOVALLEY { color: var(--accent-warning); }
    .borough-btn.active.HarborSouthBay, .borough-btn.active.HARBORSOUTHBAY { color: var(--accent-danger); }
    .borough-btn.active.SouthLA, .borough-btn.active.SOUTHLA { color: var(--accent-purple); }
    .borough-btn.active.EastsideSGV, .borough-btn.active.EASTSIDESGV { color: var(--accent-primary); }

    /* Header Actions */
    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* Unified Global Search & Jump */
    .search-wrapper {
      position: relative;
      width: 260px;
    }

    .search-input-box {
      display: flex;
      align-items: center;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 0 8px;
      height: 30px;
      transition: border-color 0.15s ease;
    }

    .search-input-box:focus-within {
      border-color: var(--accent-primary);
    }

    .search-input-box svg {
      width: 13px;
      height: 13px;
      stroke: var(--text-muted);
      flex-shrink: 0;
      margin-right: 6px;
    }

    .search-input-box input {
      background: transparent;
      border: none;
      color: var(--text-main);
      font-size: 12px;
      outline: none;
      width: 100%;
    }

    .search-input-box input::placeholder {
      color: var(--text-muted);
    }

    .search-dropdown {
      position: absolute;
      top: 36px;
      left: 0;
      right: 0;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-dropdown);
      max-height: 280px;
      overflow-y: auto;
      z-index: 110;
      display: none;
    }

    .search-dropdown.visible {
      display: block;
    }

    .search-result-item {
      padding: 8px 12px;
      font-size: 12px;
      color: var(--text-secondary);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
      border-bottom: 1px solid var(--overlay-faint);
      transition: background 0.1s ease;
    }

    .search-result-item:last-child {
      border-bottom: none;
    }

    .search-result-item:hover,
    .search-result-item[aria-selected="true"] {
      background: var(--overlay-soft);
      color: var(--text-main);
    }

    .search-empty {
      padding: 10px 12px;
      font-size: 11px;
      color: var(--text-muted);
    }

    .search-result-line {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      width: 100%;
    }

    .search-result-item .item-sub {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }

    /* Telemetry Live Badge */
    .telemetry-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 500;
      color: var(--accent-success);
      padding: 4px 8px;
      background: var(--accent-success-dim);
      border: 1px solid var(--success-edge);
      border-radius: var(--radius-sm);
      white-space: nowrap;
    }

    /* A published snapshot is not a live stream: neutral pill, static dot. */
    .telemetry-indicator.snapshot {
      color: var(--text-secondary);
      background: var(--neutral-tint-soft);
      border-color: var(--border-subtle);
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent-success);
    }

    /* Main Workspace Layout */
    .app-workspace {
      flex: 1;
      display: flex;
      position: relative;
      overflow: hidden;
    }

    /* Left Sidebar: Controls & Live Catalysts */
    .sidebar-left {
      width: 294px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      z-index: 80;
      flex-shrink: 0;
    }

    /* Right Sidebar: Parcel Inspector */
    .sidebar-right {
      width: 344px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      z-index: 80;
      flex-shrink: 0;
      overflow-y: auto;
    }

    /* Desktop: no selection, no inspector; the map takes the width. The
       inspector's drawer header doubles as its close control here. */
    @media (min-width: 861px) {
      body.inspector-empty .sidebar-right { display: none; }
      .sidebar-right .drawer-grip { display: flex; }
    }

    /* Tablet: the inspector overlays the map instead of squeezing it. */
    @media (min-width: 861px) and (max-width: 1024px) {
      .sidebar-right {
        position: absolute;
        top: 0; right: 0; bottom: 0;
        z-index: 90;
        box-shadow: var(--shadow-dropdown);
      }
      body:not(.inspector-empty) .map-controls-group { right: 316px; }
      body:not(.inspector-empty) .maplibregl-ctrl-bottom-right { right: 300px; }
      body:not(.inspector-empty) .map-readout { right: 364px; }
    }

    /* Main Map Viewport */
    .map-container {
      flex: 1;
      position: relative;
      background: var(--bg-base);
      overflow: hidden;
      border: 1px solid var(--neutral-tint-soft);
    }
    .map-container::after {
      content: '';
      position: absolute;
      inset: 0;
      z-index: 2;
      pointer-events: none;
      background: radial-gradient(ellipse 70% 60% at 50% 50%, transparent 35%, rgba(8, 13, 23, 0.65) 100%);
    }

    #map {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      width: 100%;
      height: 100%;
    }

    /* Left Panel Sections */
    .panel-section {
      padding: 16px 15px 14px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .panel-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }

    .section-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-secondary);
    }

    /* Controls Bar */
    .control-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .view-toggle {
      display: flex;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 2px;
      flex-shrink: 0;
    }

    .view-toggle button {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 500;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .view-toggle button.active {
      background: var(--bg-surface-elevated);
      color: var(--accent-primary);
      font-weight: 600;
    }

    .metric-select-dropdown {
      flex: 1;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      color: var(--text-main);
      font-size: 11px;
      padding: 5px 8px;
      outline: none;
      cursor: pointer;
      transition: border-color 0.15s ease;
    }

    .metric-select-dropdown:focus {
      border-color: var(--accent-primary);
    }

    /* Catalyst Stream List */
    .catalyst-feed-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      padding: 16px 15px 10px;
    }

    .feed-count-badge {
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-secondary);
      background: var(--neutral-tint);
      padding: 2px 6px;
      border-radius: 4px;
    }

    .catalyst-list-scroll {
      flex: 1;
      overflow-y: auto;
      margin-top: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding-right: 2px;
    }

    .catalyst-item {
      display: block;
      width: 100%;
      text-align: left;
      font: inherit;
      color: inherit;
      background: var(--overlay-faint);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 11px 12px;
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease;
    }

    .catalyst-empty {
      font-size: 11px;
      color: var(--text-muted);
      text-align: center;
      padding: 24px 0;
    }

    .catalyst-item:hover {
      background: var(--overlay-soft);
      border-color: var(--overlay-strong);
    }

    .catalyst-item.selected {
      background: var(--accent-primary-dim);
      border-color: var(--accent-primary);
    }

    .catalyst-item-top {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
    }

    .catalyst-name {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-main);
    }

    .catalyst-lims-tag {
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 600;
      color: var(--signal-high);
      flex-shrink: 0;
    }

    .catalyst-item-bottom {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 11px;
      color: var(--text-secondary);
    }

    .catalyst-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      min-width: 0;
    }

    .catalyst-item-bottom .delta-tag {
      flex-shrink: 0;
      white-space: nowrap;
    }

    .borough-tag {
      font-size: 11px;
      font-weight: 500;
      padding: 1px 5px;
      border-radius: 3px;
      background: var(--overlay-soft);
      color: var(--text-secondary);
    }

    .borough-tag.Manhattan { color: var(--borough-manhattan); }
    .borough-tag.Brooklyn { color: var(--borough-brooklyn); }
    .borough-tag.Queens { color: var(--borough-queens); }
    .borough-tag.Bronx { color: var(--borough-bronx); }
    .borough-tag.StatenIsland, .borough-tag.Staten_Island { color: var(--borough-staten); }
    .borough-tag.CentralDowntown { color: var(--accent-primary); }
    .borough-tag.NorthSide { color: var(--accent-emerald); }
    .borough-tag.NorthwestSide { color: var(--accent-amber); }
    .borough-tag.SouthSide { color: var(--accent-crimson); }
    .borough-tag.FarNorthSide { color: var(--accent-purple); }
    .borough-tag.SouthwestSide { color: var(--accent-primary); }
    .borough-tag.SanFranciscoCore, .borough-tag.SAN_FRANCISCO_CORE, .borough-tag.SFCore { color: var(--division-sf-core); }
    .borough-tag.EastBay, .borough-tag.EAST_BAY { color: var(--division-east-bay); }
    .borough-tag.Peninsula, .borough-tag.PENINSULA { color: var(--division-peninsula); }
    .borough-tag.SiliconValleySouthBay, .borough-tag.SILICON_VALLEY_SOUTH_BAY, .borough-tag.SiliconValley { color: var(--division-silicon-valley); }
    .borough-tag.MarinNorthBay, .borough-tag.MARIN_NORTH_BAY, .borough-tag.Marin { color: var(--division-marin); }
    .borough-tag.NorthBayWineCountry, .borough-tag.NORTH_BAY_WINE_COUNTRY, .borough-tag.WineCountry { color: var(--division-wine-country); }
    .borough-tag.SolanoCorridor, .borough-tag.SOLANO_CORRIDOR, .borough-tag.Solano { color: var(--division-solano); }
    .borough-tag.OuterContraCosta, .borough-tag.OUTER_CONTRA_COSTA, .borough-tag.OuterCC { color: var(--division-outer-contra-costa); }
    .borough-tag.SeattleCore, .borough-tag.SEATTLE_CORE { color: var(--accent-primary); }
    .borough-tag.NorthKing, .borough-tag.NORTH_KING { color: var(--accent-success); }
    .borough-tag.Eastside, .borough-tag.EASTSIDE { color: var(--accent-purple); }
    .borough-tag.SouthKing, .borough-tag.SOUTH_KING { color: var(--accent-warning); }
    .borough-tag.CentralLA, .borough-tag.CENTRALLA { color: var(--accent-primary); }
    .borough-tag.Westside, .borough-tag.WESTSIDE { color: var(--accent-success); }
    .borough-tag.SanFernandoValley, .borough-tag.SANFERNANDOVALLEY { color: var(--accent-warning); }
    .borough-tag.HarborSouthBay, .borough-tag.HARBORSOUTHBAY { color: var(--accent-danger); }
    .borough-tag.SouthLA, .borough-tag.SOUTHLA { color: var(--accent-purple); }
    .borough-tag.EastsideSGV, .borough-tag.EASTSIDESGV { color: var(--accent-primary); }

    .delta-tag {
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-secondary);
    }

    /* Floating Map Controls */
    .map-controls-group {
      position: absolute;
      top: 16px;
      right: 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 50;
    }

    .map-tool-btn {
      width: 36px;
      height: 36px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s ease;
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.32);
    }

    .map-tool-btn:hover {
      background: var(--bg-surface-elevated);
      color: var(--text-main);
      border-color: var(--overlay-strong);
    }

    .map-tool-btn svg {
      width: 15px;
      height: 15px;
      stroke: currentColor;
    }

    /* Sleek Map Legend */
    .map-legend-card {
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--bg-glass);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      z-index: 50;
      min-width: 200px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    .legend-header {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }

    .legend-bar {
      height: 6px;
      border-radius: 3px;
      /* Regenerated at runtime from HEX_RAMP (same stops as the map layers). */
      background: linear-gradient(to right, #0c1628, #1c3c5c 35%, #3a8688 60%, #7ab87a 80%, #c8b84c 92%, #e8a050);
      margin-bottom: 4px;
    }

    .legend-ticks {
      position: relative;
      height: 10px;
      margin-bottom: 4px;
    }

    .legend-tick {
      position: absolute;
      top: 0;
      transform: translateX(-50%);
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      line-height: 10px;
    }

    .legend-note {
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid var(--border-subtle);
      font-size: 11px;
      letter-spacing: 0.02em;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .legend-key-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .legend-key-swatch {
      width: 14px;
      height: 8px;
      border-radius: 2px;
      flex: none;
    }

    .legend-key-swatch.no-data {
      background: var(--no-data-fill);
      border: 1px solid var(--no-data-edge);
    }

    .legend-attribution {
      color: var(--text-muted);
      font-size: 11px;
      line-height: 1.35;
    }

    .legend-key-swatch.baseline {
      background: repeating-linear-gradient(
        45deg,
        var(--baseline-hatch) 0 3px,
        transparent 3px 6px
      );
      border: 1px solid var(--baseline-hatch);
    }

    /* Map orientation readout: scale bar + zoom/coordinate telemetry */
    .map-readout {
      position: absolute;
      right: 64px;
      bottom: 24px;
      z-index: 50;
      display: flex;
      align-items: flex-end;
      gap: 12px;
      pointer-events: none;
    }

    .map-scale-bar {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .map-scale-label {
      font-size: 11px;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      color: var(--text-secondary);
      text-align: center;
    }

    .map-scale-rule {
      height: 4px;
      border: 1px solid var(--scale-rule-edge);
      border-top: none;
      background: var(--scale-rule-fill);
    }

    .map-coords {
      font-size: 11px;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      color: var(--text-muted);
      background: var(--bg-glass);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 4px 8px;
    }

    /* Inspector Empty & Active States */
    .inspector-empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 24px;
      text-align: center;
      color: var(--text-muted);
      height: 100%;
    }

    .inspector-empty-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--overlay-faint);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
      color: var(--text-muted);
    }

    .inspector-empty-icon svg {
      width: 20px;
      height: 20px;
      stroke: currentColor;
    }

    .inspector-empty-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 4px;
    }

    .inspector-empty-desc {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.4;
    }

    /* Inspected Parcel Details */
    .inspector-content {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .parcel-header {
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 12px;
    }

    .parcel-title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .parcel-name {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }

    .parcel-meta-sub {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 2px 8px;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .parcel-meta-sub span { white-space: nowrap; }

    .parcel-description {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.4;
    }

    /* Hero Score Summary */
    .score-hero-block {
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .score-hero-left {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .score-hero-label {
      font-size: 11px;
      font-weight: 500;
      color: var(--text-secondary);
    }

    .score-status-pill {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .score-hero-val {
      font-size: 28px;
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--text-main);
    }
    .score-status-pill { color: var(--text-secondary); }
    .score-hero-val.catalyst, .score-status-pill.catalyst { color: var(--signal-high); }
    .score-hero-val.baseline { color: var(--text-secondary); }

    /* Signed deltas: green up, red down; everything else stays neutral. */
    .delta-pos, .popup-val.delta-pos { color: var(--accent-success); }
    .delta-neg, .popup-val.delta-neg { color: var(--accent-danger); }

    /* Forecast Metrics Grid */
    .forecast-section-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .quantiles-card {
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 10px 12px;
      margin-bottom: 8px;
    }

    .quantiles-header {
      font-size: 11px;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
    }

    .quantiles-spread-row {
      display: grid;
      grid-template-columns: 1fr 1.2fr 1fr;
      gap: 8px;
      text-align: center;
    }

    .q-box {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .q-lbl {
      font-size: 11px;
      color: var(--text-muted);
    }

    .q-num {
      font-size: 12px;
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-secondary);
    }

    .quantiles-model { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }
    .context-sources { margin-top: 6px; }

    .q-box.expected .q-num {
      font-size: 14px;
      color: var(--text-main);
    }

    .horizon-pairs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .horizon-mini-card {
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 10px 12px;
    }

    .horizon-mini-lbl {
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .horizon-mini-val {
      font-size: 14px;
      font-weight: 600;
      font-family: var(--font-mono);
      color: var(--text-main);
    }

    /* Chart Block */
    .chart-block {
      position: relative;
      height: 160px;
      width: 100%;
    }

    /* Feature Data Table */
    .telemetry-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }

    .telemetry-table tr {
      border-bottom: 1px solid var(--overlay-soft);
    }

    .telemetry-table tr:last-child {
      border-bottom: none;
    }

    .telemetry-table td {
      padding: 6px 0;
    }

    .telemetry-table td.lbl {
      color: var(--text-secondary);
    }

    .telemetry-table td.val {
      text-align: right;
      font-family: var(--font-mono);
      font-weight: 500;
      color: var(--text-main);
    }

    /* MapLibre Popup Overrides */
    .popup-card { font-size: 11px; min-width: 190px; line-height: 1.4; }
    .popup-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; }
    .popup-title { color: var(--text-main); font-size: 12px; }
    .popup-city { color: var(--text-muted); margin-bottom: 3px; }
    .popup-row { display: flex; justify-content: space-between; gap: 8px; margin-top: 2px; }
    .popup-lbl { color: var(--text-secondary); }
    .popup-val { font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text-main); }

    /* MapLibre's own controls and credit line, restyled for the dark chrome. */
    .maplibregl-ctrl.maplibregl-ctrl-group {
      background: var(--bg-glass);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.32);
    }
    .maplibregl-ctrl-group button + button { border-top: 1px solid var(--border-subtle); }
    .maplibregl-ctrl-group button .maplibregl-ctrl-icon { filter: invert(0.85); }
    .maplibregl-ctrl-group button:not(:disabled):hover { background-color: var(--overlay-soft); }
    .maplibregl-ctrl.maplibregl-ctrl-attrib {
      background: rgba(8, 13, 23, 0.72);
      color: var(--text-muted);
      font-size: 11px;
    }
    .maplibregl-ctrl-attrib a { color: var(--text-secondary); }
    .maplibregl-ctrl.maplibregl-ctrl-attrib.maplibregl-compact { background: var(--bg-glass); }

    .maplibregl-popup-content {
      background: var(--bg-surface) !important;
      border: 1px solid var(--border-subtle) !important;
      border-radius: var(--radius-md) !important;
      box-shadow: var(--shadow-dropdown) !important;
      color: var(--text-main) !important;
      padding: 10px 12px !important;
      font-family: var(--font-sans);
    }
    .maplibregl-popup-tip {
      border-top-color: var(--bg-surface) !important;
    }

    /* Tablet / small-desktop shrink — sidebars stay visible */
    @media (max-width: 1024px) {
      .sidebar-left { width: 260px; }
      .sidebar-right { width: 300px; }
      .search-wrapper { width: 180px; }
    }

    /* ---------------------------------------------------------------------------
       Mobile chrome — inert on desktop (<=860px activates it).
       The always-visible sidebars become off-canvas drawers; the header
       reflows to a brand row plus a horizontally-scrollable division strip;
       search collapses to a top sheet; a thumb-reachable toolbar toggles
       layers / search / inspector.
       --------------------------------------------------------------------------- */

    .drawer-scrim,
    .mobile-toolbar,
    .drawer-grip { display: none; }

    body.drawer-left-open .drawer-scrim,
    body.drawer-right-open .drawer-scrim,
    body.search-open .drawer-scrim { display: block; }

    .drawer-grip {
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-subtle);
      flex-shrink: 0;
    }
    .drawer-grip-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-secondary);
    }
    .drawer-close {
      width: 40px; height: 40px;
      display: flex; align-items: center; justify-content: center;
      background: transparent;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      font-size: 20px; line-height: 1;
      cursor: pointer;
      transition: background 0.15s ease, color 0.15s ease;
    }
    .drawer-close:hover, .drawer-close:focus-visible {
      background: var(--overlay-soft);
      color: var(--text-main);
    }

    .mobile-toolbar {
      position: absolute;
      bottom: max(12px, env(safe-area-inset-bottom));
      left: 50%;
      transform: translateX(-50%);
      gap: 4px;
      padding: 5px;
      background: var(--bg-glass);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-dropdown);
      z-index: 95;
    }
    .mt-btn {
      min-width: 44px; min-height: 44px;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
      padding: 6px 10px;
      background: transparent;
      border: none;
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      cursor: pointer;
      transition: background 0.15s ease, color 0.15s ease;
    }
    .mt-btn svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 2; }
    .mt-btn span { font-size: 11px; font-weight: 600; letter-spacing: 0.02em; }
    .mt-btn:hover, .mt-btn:focus-visible { background: var(--overlay-soft); color: var(--text-main); }
    .mt-btn.active { background: var(--accent-primary-dim); color: var(--accent-primary); }

    .drawer-scrim {
      position: absolute; inset: 0;
      background: rgba(4, 8, 16, 0.55);
      backdrop-filter: blur(2px);
      z-index: 85;
      animation: scrimIn 0.2s ease both;
    }
    @keyframes scrimIn { from { opacity: 0; } to { opacity: 1; } }

    @media (max-width: 860px) {
      /* Header: two rows — brand + city + stream above, division chips below */
      header {
        height: auto;
        flex-wrap: wrap;
        padding: max(8px, env(safe-area-inset-top)) 12px 0;
        gap: 8px;
      }
      .brand-section { flex: 0 0 auto; min-width: 0; gap: 8px; }
      .brand-icon { width: 28px; height: 28px; flex-shrink: 0; }
      .brand-title { font-size: 12px; }
      .brand-badge { display: none; }
      .borough-nav {
        flex: 1 1 100%;
        order: 5;
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        background: transparent;
        border: none; border-radius: 0;
        border-top: 1px solid var(--border-subtle);
        padding: 6px 4px calc(6px + env(safe-area-inset-bottom));
        gap: 6px;
      }
      .borough-nav::-webkit-scrollbar { display: none; }
      .borough-btn { padding: 8px 12px; min-height: 40px; font-size: 12px; flex-shrink: 0; }
      .header-actions { flex: 0 0 auto; gap: 8px; }
      .telemetry-indicator { padding: 5px 7px; font-size: 11px; }
      .telemetry-indicator #stream-status-text { display: none; }

      /* Workspace: sidebars leave flow as off-canvas drawers */
      .app-workspace { position: relative; }
      .sidebar-left, .sidebar-right {
        position: absolute;
        top: 0; bottom: 0;
        width: min(294px, 86vw);
        z-index: 90;
        transform: translateX(-100%);
        transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: var(--shadow-dropdown);
        padding-bottom: env(safe-area-inset-bottom);
      }
      .sidebar-left { left: 0; overflow: hidden; }
      .sidebar-right {
        right: 0;
        width: min(344px, 92vw);
        transform: translateX(100%);
      }
      body.drawer-left-open .sidebar-left { transform: translateX(0); }
      body.drawer-right-open .sidebar-right { transform: translateX(0); }
      .drawer-grip { display: flex; }
      #inspector-content { height: auto !important; flex: 1 1 auto; min-height: 0 !important; }
      .mobile-toolbar { display: flex; }

      /* Search collapses to a slide-down top sheet */
      .search-wrapper {
        position: fixed;
        top: var(--header-h, 56px);
        left: 0; right: 0; width: auto;
        z-index: 95;
        padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
        background: var(--bg-surface);
        border-bottom: 1px solid var(--border-subtle);
        /* Fully off-screen above the header, and hidden, so a stale
           --header-h can never leave a dead search box over the brand row. */
        transform: translateY(calc(-100% - var(--header-h, 56px)));
        visibility: hidden;
        transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), visibility 0s linear 0.26s;
        pointer-events: none;
      }
      body.search-open .search-wrapper {
        transform: translateY(0);
        visibility: visible;
        pointer-events: auto;
        transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), visibility 0s;
      }
      .search-input-box { height: 40px; }
      .search-dropdown { top: 50px; max-height: 50vh; }

      /* Map fills full width; floating tools enlarge; legend becomes a slim bar */
      .map-container { width: 100%; }
      .map-controls-group { top: max(12px, env(safe-area-inset-top)); right: 12px; gap: 8px; }
      .map-tool-btn { width: 44px; height: 44px; }
      .map-tool-btn svg { width: 18px; height: 18px; }
      .map-legend-card {
        left: 12px; right: 12px;
        /* Above the thumb toolbar (56px) and the map credit line (~24px). */
        bottom: calc(max(12px, env(safe-area-inset-bottom)) + 92px);
        min-width: 0; width: auto;
        padding: 8px 12px;
      }
      .map-legend-card .legend-bar { margin-bottom: 6px; }

      /* Phones pinch to zoom, so drop the +/- buttons; lift the required map
         credit above the thumb toolbar instead of under it. */
      .maplibregl-ctrl-bottom-right .maplibregl-ctrl-group { display: none; }
      .maplibregl-ctrl-bottom-right,
      .maplibregl-ctrl-bottom-left { bottom: calc(max(12px, env(safe-area-inset-bottom)) + 62px); }

      /* Orientation readout moves to the top-left above the thumb toolbar
         so the scale bar and telemetry never sit under the mobile toolbar
         or collide with the legend bar along the bottom edge. */
      .map-readout {
        top: max(12px, env(safe-area-inset-top));
        right: auto;
        bottom: auto;
        left: 12px;
        flex-direction: column-reverse;
        align-items: flex-start;
        gap: 6px;
      }

      .inspector-content { padding: 14px; }
      .inspector-empty-state { padding: 40px 18px; }
    }

    @media (max-width: 860px) and (prefers-reduced-motion: reduce) {
      .sidebar-left, .sidebar-right, .search-wrapper { transition: none; }
      .drawer-scrim { animation: none; }
    }
  </style>
</head>
<body class="inspector-empty">

  <!-- Toast Notification Container -->
  <div id="status-toast-container" role="status" aria-live="polite"></div>

  <!-- Clean Top Navigation Header -->
  <header role="banner">
    <!-- Brand -->
    <div class="brand-section">
      <div class="brand-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <div class="brand-title">
        <span>Urban Signal</span>
        <span class="sr-only">Geospatial Intelligence Dashboard</span>
        <span class="brand-badge">v2.0</span>
      </div>
    </div>

    <!-- Metro Chips: navigation only. All metros' data renders together; a
         chip flies the camera to its metro and scopes the catalyst feed. -->
    <nav class="borough-nav" id="metro-chips" role="navigation" aria-label="Metro navigation">
      <!-- Populated dynamically from the snapshot manifest -->
    </nav>

    <!-- Header Actions & Search -->
    <div class="header-actions">
      <!-- Search & Jump -->
      <div class="search-wrapper" role="search">
        <div class="search-input-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" id="global-search-input" placeholder="Search submarket, coords, H3..." autocomplete="off" aria-label="Search submarket or coordinate" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="search-dropdown" oninput="onGlobalSearch(this.value)" onkeydown="onSearchKeydown(event)">
        </div>
        <div class="search-dropdown" id="search-dropdown" role="listbox" aria-label="Search suggestions">
          <!-- Populated dynamically via JS -->
        </div>
      </div>

      <!-- Live Stream Status -->
      <div class="telemetry-indicator" id="stream-status-pill" title="Streaming real-time municipal telemetries">
        <span class="pulse-dot" id="stream-pulse-dot"></span>
        <span id="stream-status-text">Live</span>
      </div>
    </div>
  </header>

  <!-- Main Application Workspace -->
  <div class="app-workspace">

    <!-- Mobile drawer scrim + thumb-reachable toolbar (desktop-inert) -->
    <div class="drawer-scrim" aria-hidden="true"></div>
    <nav class="mobile-toolbar" role="navigation" aria-label="Map panels">
      <button class="mt-btn" type="button" data-drawer="left" aria-expanded="false" aria-label="Open layer controls and catalysts">
        <svg viewBox="0 0 24 24" aria-hidden="true"><polygon points="12 2 22 8 12 14 2 8"/><polyline points="2 12 12 18 22 12"/></svg>
        <span>Layers</span>
      </button>
      <button class="mt-btn" type="button" data-drawer="search" aria-expanded="false" aria-label="Open search">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span>Search</span>
      </button>
      <button class="mt-btn" type="button" data-drawer="right" aria-expanded="false" aria-label="Open parcel inspector">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="3" x2="12" y2="7"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="3" y1="12" x2="7" y2="12"/><line x1="17" y1="12" x2="21" y2="12"/></svg>
        <span>Inspect</span>
      </button>
    </nav>

    <!-- Left Sidebar: Layer Controls & Active Catalysts -->
    <aside class="sidebar-left">
      <!-- Mobile drawer header (desktop-inert) -->
      <div class="drawer-grip">
        <span class="drawer-grip-title">Layers &amp; Catalysts</span>
        <button class="drawer-close" type="button" data-close aria-label="Close layers panel">&times;</button>
      </div>
      <!-- Map Controls Panel -->
      <div class="panel-section">
        <div class="panel-header-row">
          <span class="section-title">Projection & Metric</span>
        </div>
        <div class="control-row">
          <div class="view-toggle">
            <button id="btn-3d" type="button" class="active" aria-pressed="true" onclick="setPerspective('3D')">3D</button>
            <button id="btn-2d" type="button" aria-pressed="false" onclick="setPerspective('2D')">2D</button>
          </div>
          <select id="metric-select" class="metric-select-dropdown" onchange="updateMetricVisuals()">
            <option value="lims_score">LIMS Momentum Score</option>
            <option value="delta_6m_p50">6M Expected Return (p50)</option>
            <option value="delta_12m_spillover">12M Spatial Spillover</option>
            <option value="prob_18m_macro_outperformance">18M Macro Outperformance</option>
          </select>
        </div>
      </div>

      <!-- Real-Time Catalyst Feed -->
      <div class="catalyst-feed-section">
        <div class="panel-header-row">
          <span class="section-title">Catalysts</span>
          <span class="feed-count-badge" id="stat-active-catalysts"></span>
        </div>
        <div class="catalyst-list-scroll" id="catalyst-feed-list">
          <!-- Populated dynamically via JS -->
        </div>
      </div>
    </aside>

    <!-- Center Map Viewport -->
    <main class="map-container">
      <div id="map"></div>
      <div class="zoom-hint" id="zoom-hint" hidden>Zoom in to load cell-level data</div>

      <!-- Floating Quick Tools -->
      <div class="map-controls-group">
        <!-- 3D/2D lives in the sidebar's segmented control, which shows the
             current mode; one control, not two. -->
        <button class="map-tool-btn" type="button" title="Reset view (all metros)" aria-label="Reset view to all metros" onclick="selectMetro(null)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
        </button>
      </div>

      <!-- Sleek Map Legend -->
      <div class="map-legend-card">
        <div class="legend-header">
          <span id="legend-metric-title">LIMS Momentum Score</span>
        </div>
        <div class="legend-bar"></div>
        <!-- One tick row under the bar: the ramp's stops. The 0–100 range is
             stated in the note below, so no second row of end labels. -->
        <div class="legend-ticks" id="legend-ticks" aria-hidden="true"></div>
        <div class="legend-note">
          <span class="legend-key-row">Height &prop; value (3D view) &middot; percentile 0&ndash;100</span>
          <span class="legend-key-row"><span class="legend-key-swatch baseline"></span><span>Registry baseline &mdash; no precomputed snapshot</span></span>
          <span class="legend-key-row" id="legend-no-data" hidden><span class="legend-key-swatch no-data"></span><span>No data &mdash; outside this layer&rsquo;s coverage</span></span>
          <span class="legend-attribution" id="legend-attribution" hidden></span>
        </div>
      </div>

      <!-- Map orientation readout: scale bar + zoom/coordinates -->
      <div class="map-readout" aria-hidden="true">
        <div class="map-scale-bar">
          <span class="map-scale-label" id="map-scale-label">1 km</span>
          <div class="map-scale-rule" id="map-scale-rule" style="width: 80px;"></div>
        </div>
        <div class="map-coords"><span id="map-zoom-readout">z0.0</span> &middot; <span id="map-coords-readout">&mdash;</span></div>
      </div>
    </main>

    <!-- Right Sidebar: Parcel & Submarket Inspector -->
    <aside class="sidebar-right" id="inspector-panel">
      <!-- Mobile drawer header (desktop-inert) -->
      <div class="drawer-grip">
        <span class="drawer-grip-title">Parcel Inspector</span>
        <button class="drawer-close" type="button" data-close aria-label="Close inspector">&times;</button>
      </div>
      <div id="inspector-content" style="height: 100%;">
        <div class="inspector-empty-state">
          <div class="inspector-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon>
            </svg>
          </div>
          <div class="inspector-empty-title">Select a Parcel or Catalyst</div>
          <div class="inspector-empty-desc">Click any hexagon on the map or select a catalyst alert to inspect multi-horizon forecasts & SHAP telemetry.</div>
        </div>
      </div>
    </aside>

  </div>

  <script>
    // Dynamic submarkets catalog loaded per active city via /api/v1/submarkets
    let SUBMARKETS = {};

    // Metro chip labels + ?city= deep-link validation, generated from the
    // live REGISTRY by get_dashboard_html() (US-427) — this comment is now
    // true. Camera geometry comes from the snapshot manifest's metro_index;
    // this map deliberately carries none so registration stays single-sourced:
    // register a city in REGISTRY and it appears here; it cannot fall off.
    const METRO_META = {
__METRO_META__
    };

    // National event sources surfaced by the dashboard's data contract. The
    // FDIC branch layer is point-native and carries annual SOD deposit context;
    // keeping the label here makes the source discoverable alongside the
    // national LOD view without pretending the raw Kafka topic is client data.
    const NATIONAL_CONTEXT_SOURCES = {
      bank_branch: { label: 'FDIC BankFind branches', topic: 'raw.federal.bank_branches' },
    };

    const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let map = null;
    let gridGeoJSON = null;
    let shapChart = null;
    let currentPerspective = '3D';
    let currentMetric = 'lims_score';
    // Bay Area context layers (US-439..443) published by the snapshot's
    // manifest.context_layers block: key -> {label, layer, unit, attribution}.
    // Empty when the snapshot carries no context table, so no dead options.
    let CONTEXT_METRICS = {};
    const NO_DATA_FILL = 'rgba(113, 129, 152, 0.18)';
    let selectedH3Index = null;
    let hoveredH3Index = null;
    let catalystAlerts = [];

    // ---- All-metros national view state ------------------------------------
    let snapshotManifest = null;
    let activeMetroChip = null;        // city_id or null (= all metros)
    const fetchedTiles = new Set();    // res-5 parents already merged into source
    const tileFeatures = new Map();    // h3_index -> GeoJSON feature
    const pendingTileParents = [];     // queued parents awaiting fetch
    const tilesInFlight = new Set();
    let tileFetchesActive = 0;
    let tileLoadGeneration = 0;
    let activeLodRes = 9; // LOD level whose parents are currently being fetched
    let gridDirty = false;
    let viewportDebounceTimer = 0;
    let nationalDebounceTimer = 0;
    const TILE_PARENTS_PER_REQUEST = 32;
    const TILE_FETCH_CONCURRENCY = 2;
    const ZOOM_FLOOR = 6; // below this: national layer only (LODES)
    // Metro LOD pyramid (US-411/413): select the display resolution based on
    // zoom level so the map never shows a dead zone between national and metro.
    const GRID_LOD_RESOLUTIONS = [7, 8, 9];
    const LOD_TO_PARENT_RES = { 7: 4, 8: 4, 9: 5 };
    const LOD_PARENT_STEP = { 7: 0.45, 8: 0.45, 9: 0.14 };
    const LOD_PARENT_SAMPLES = { 7: 800, 8: 800, 9: 4000 };
    function lodForZoom(z) {
      if (z >= 11) return 9;
      if (z >= 9) return 8;
      return 7;
    }

    // National overlay cache: per-resolution res-3-parent -> features[]
    const nationalCache = {
      4: new Map(),
      5: new Map(),
      6: new Map(),
    };
    // Active data shown on the overlay per resolution
    const nationalActive = {
      4: [],
      5: [],
      6: [],
    };
    let nationalActiveRes = null;

    function cityDisplayName(cityId) {
      return (METRO_META[cityId] || {}).name || String(cityId).replace(/_/g, ' ');
    }

    // Defensive String and Number Helpers
    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function safeNumber(val, fallback = 0.0) {
      const num = Number(val);
      return (isNaN(num) || !isFinite(num)) ? fallback : num;
    }

    function showToast(message, type = 'error', actionLabel = null, actionFn = null) {
      const container = document.getElementById('status-toast-container');
      if (!container) return;
      
      const toast = document.createElement('div');
      toast.className = `toast-banner ${type}`;
      toast.innerHTML = `
        <span>${escapeHtml(message)}</span>
        ${actionLabel ? `<button class="toast-btn" id="toast-action-btn">${escapeHtml(actionLabel)}</button>` : ''}
      `;
      
      if (actionLabel && actionFn) {
        const btn = toast.querySelector('#toast-action-btn');
        if (btn) {
          btn.onclick = () => {
            toast.remove();
            actionFn();
          };
        }
      }
      
      container.appendChild(toast);
      setTimeout(() => {
        if (toast.parentNode) {
          toast.style.opacity = '0';
          toast.style.transition = 'opacity 0.3s ease';
          setTimeout(() => toast.remove(), 300);
        }
      }, 5000);
    }

    function haversineDistance(lat1, lon1, lat2, lon2) {
      const R = 3958.8; // miles
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon / 2) * Math.sin(dLon / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      return R * c;
    }

    // ---- National LOD overlay (MapLibre geojson) ---------------------------
    // Renders res-4/5/6 all-metros hexes below z 12 as a blended fallback
    // geojson layers fed by /api/v1/national/{res}. Shares the metric
    // `_national_pct` ramp with the metro res-9 layers; flat fill in 2D,
    // fill-extrusion in 3D. (Deck.gl was removed — US-391: the UMD bundles
    // clobbered the global `deck` namespace and the overlay never rendered.)
    function nationalResForZoom(z) {
      if (z < 5) return 4;
      if (z < 8) return 5;
      return 6;
    }

    function res3ParentsCoveringBounds(bounds) {
      if (typeof h3 === 'undefined' || !bounds) return [];
      const west = bounds.getWest();
      const east = bounds.getEast();
      const south = bounds.getSouth();
      const north = bounds.getNorth();
      // Sample below a res-3 hex diameter so sampling cannot skip a parent
      const stepLat = 0.9;   // ~ lat height of res-3
      const stepLng = 0.9;   // ~ lng width of res-3 (rough)
      const parents = new Set();
      for (let lat = south; lat <= north; lat += stepLat) {
        for (let lng = west; lng <= east; lng += stepLng) {
          try {
            const cell = h3.latLngToCell(lat, lng, 3);
            if (cell) parents.add(cell);
          } catch (_) { /* ignore */ }
        }
      }
      return Array.from(parents);
    }

    function scheduleNationalLoad() {
      clearTimeout(nationalDebounceTimer);
      nationalDebounceTimer = setTimeout(updateNationalOverlay, 250);
    }

    async function updateNationalOverlay() {
      if (!map) return;
      const z = map.getZoom();
      const hint = document.getElementById('zoom-hint');
      // Retire the "Zoom in..." dead-zone message
      if (hint) hint.hidden = true;
      // Show/hide overlay by zoom; the LODES overlay owns zooms below ZOOM_FLOOR
      updateNationalLayerVisibilities();
      if (z >= ZOOM_FLOOR) return; // metro LOD owns every zoom at/above the floor

      const res = nationalResForZoom(z);
      nationalActiveRes = res;
      // Swap per-res data — never accumulate across res levels
      nationalActive[4] = [];
      nationalActive[5] = [];
      nationalActive[6] = [];

      // Determine res-3 parents to request for this viewport
      const parents = res3ParentsCoveringBounds(map.getBounds());
      const missing = parents.filter((p) => !nationalCache[res].has(p));
      // Batch-fetch missing parents; API mirrors gridtiles shape
      if (missing.length) {
        const batches = [];
        const BATCH = 24;
        for (let i = 0; i < missing.length; i += BATCH) {
          batches.push(missing.slice(i, i + BATCH));
        }
        await Promise.all(
          batches.map(async (chunk) => {
            const url = `/api/v1/national/${res}?parents=${chunk.join(',')}`;
            try {
              const resp = await fetch(url);
              if (!resp.ok) return;
              const payload = await resp.json();
              const feats = nationalRowsToFeatures(payload);
              // Cache by the reported parent when present; otherwise group by computed res-3 parent
              for (const feature of feats) {
                const cell = feature?.properties?.h3_index;
                if (!cell) continue;
                const p = (typeof h3 !== 'undefined' && h3.cellToParent) ? h3.cellToParent(cell, 3) : null;
                const key = (p && chunk.includes(p)) ? p : (p || chunk[0]);
                if (!nationalCache[res].has(key)) nationalCache[res].set(key, []);
                nationalCache[res].get(key).push(feature);
              }
            } catch (e) {
              console.debug('national fetch error:', e);
            }
          })
        );
      }

      // Assemble active features for the overlay from the cached parents in view
      let feats = [];
      for (const p of parents) {
        const arr = nationalCache[res].get(p);
        if (arr && arr.length) feats = feats.concat(arr);
      }
      nationalActive[res] = feats;
      applyNationalData();
    }

    // The national API serves rows-of-arrays chunks ({cols, rows}), so the
    // client turns each row into a GeoJSON Polygon using h3.cellToBoundary.
    function nationalRowsToFeatures(payload) {
      if (!payload || !Array.isArray(payload.cols) || !Array.isArray(payload.rows)) return [];
      const cols = payload.cols;
      const out = [];
      for (const row of payload.rows) {
        const props = {};
        cols.forEach((col, i) => { props[col] = row[i]; });
        const cell = props.h3;
        if (!cell || typeof h3 === 'undefined') continue;
        // Honesty rule: skip hexes with no percentile data so the overlay never
        // invents a color for a null row.
        const jobsPct = Number(props.jobs_pct);
        const workersPct = Number(props.workers_pct);
        if (!Number.isFinite(jobsPct) && !Number.isFinite(workersPct)) continue;
        let boundary;
        try {
          boundary = h3.cellToBoundary(cell);
        } catch (_) {
          continue;
        }
        // h3 boundary is [lat, lng]; GeoJSON wants [lng, lat]; close the ring.
        const ring = boundary.map(([lat, lng]) => [lng, lat]);
        ring.push(ring[0]);
        props.h3_index = cell;
        const c = h3.cellToLatLng(cell);
        props.centroid_lat = c[0];
        props.centroid_lng = c[1];
        out.push({
          type: 'Feature',
          geometry: { type: 'Polygon', coordinates: [ring] },
          properties: props
        });
      }
      return out;
    }

    function applyNationalData() {
      if (!map || !map.getSource('national-hex-source')) return;
      map.getSource('national-hex-source')
        .setData({ type: 'FeatureCollection', features: nationalActive[nationalActiveRes] || [] });
      map.triggerRepaint();
    }

    // MapLibre geojson layers carrying the national LOD hexes. Three layers:
    // flat fill (2D), subtle outline, and fill-extrusion (3D). The color/height
    // expressions read the selected metric's *_national_pct when the national
    // payload carries it, falling back to the LODES jobs/workers percentiles.
    function setupNationalLayers() {
      if (!map || map.getSource('national-hex-source')) return;
      map.addSource('national-hex-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });
      map.addLayer({
        id: 'national-h3-fill',
        type: 'fill',
        source: 'national-hex-source',
        layout: { visibility: 'none' },
        paint: {
          'fill-color': nationalColorExpression(),
          'fill-opacity': 0.7
        }
      });
      map.addLayer({
        id: 'national-h3-line',
        type: 'line',
        source: 'national-hex-source',
        paint: {
          // Boundary-only stroke that scales with zoom: quiet at national
          // view, never a white grid checkerboard.
          'line-color': 'rgba(148, 163, 184, 0.22)',
          'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.4, 6, 0.7]
        }
      });
      map.addLayer({
        id: 'national-h3-extrusion',
        type: 'fill-extrusion',
        source: 'national-hex-source',
        layout: { visibility: 'none' },
        paint: {
          'fill-extrusion-color': nationalColorExpression(),
          'fill-extrusion-height': nationalHeightExpression(),
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.85
        }
      });
      map.on('click', 'national-h3-fill', onNationalHexClick);
      map.on('click', 'national-h3-extrusion', onNationalHexClick);
      updateNationalLayerVisibilities();
    }

    function nationalColorExpression() {
      return hexRampExpr(
        ['coalesce', ['get', `${currentMetric}_national_pct`], ['get', 'jobs_pct'], ['get', 'workers_pct']]
      );
    }

    function nationalHeightExpression() {
      // Match MapLibre 3D emphasis roughly per metric; reuse lims scaling by default
      const factors = {
        lims_score: 18,
        delta_6m_p50: 40,
        delta_12m_spillover: 45,
        prob_18m_macro_outperformance: 9,
      };
      const factor = factors[currentMetric] || 18;
      return [
        '*',
        ['max', 0, ['-', ['coalesce', ['get', `${currentMetric}_national_pct`], ['get', 'jobs_pct'], ['get', 'workers_pct']], 40]],
        factor
      ];
    }

    function updateNationalLayerVisibilities() {
      if (!map) return;
      const z = map.getZoom();
      // The national overlay and the metro LOD pyramid occupy DISJOINT zoom
      // bands (US-422). The overlay previously stayed up until z12 while the
      // metro pyramid already started at ZOOM_FLOOR, so six zoom levels drew
      // both at once: the coarse res-6 national cells (~3km across, extruded
      // in 3D) covered the metro hexes, and because that grid is a uniform
      // country-wide tiling with no land mask it spilled over rivers, bays and
      // airports. lodForZoom() covers every zoom >= ZOOM_FLOOR, so the blend
      // is redundant — hand off cleanly at the floor instead.
      const overlayVisible = z < ZOOM_FLOOR;
      const setVis = (id, visible) => {
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
        }
      };
      setVis('national-h3-fill', overlayVisible && currentPerspective === '2D');
      setVis('national-h3-line', overlayVisible);
      setVis('national-h3-extrusion', overlayVisible && currentPerspective === '3D');
    }

    function updateNationalLayerPaint() {
      if (!map) return;
      if (map.getLayer('national-h3-fill')) {
        map.setPaintProperty('national-h3-fill', 'fill-color', nationalColorExpression());
      }
      if (map.getLayer('national-h3-extrusion')) {
        map.setPaintProperty('national-h3-extrusion', 'fill-extrusion-color', nationalColorExpression());
        map.setPaintProperty('national-h3-extrusion', 'fill-extrusion-height', nationalHeightExpression());
      }
    }

    function onNationalHexClick(e) {
      if (!e.features || !e.features.length) return;
      const props = e.features[0].properties || {};
      const h3idx = props.h3_index;
      if (h3idx) {
        const c = (typeof h3 !== 'undefined' && h3.cellToLatLng) ? h3.cellToLatLng(h3idx) : [null, null];
        inspectH3CellWithNationalFallback(h3idx, c[0], c[1], props);
      }
    }

    async function inspectH3CellWithNationalFallback(h3Index, lat, lng, natProps) {
      try {
        const resp = await fetch('/api/v1/predict', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ h3_index: h3Index, include_shap: true })
        });
        if (resp.ok) {
          const pred = await resp.json();
          handleHexSelection({ ...natProps, ...pred, h3_index: h3Index, centroid_lat: lat, centroid_lng: lng });
          return;
        }
      } catch (e) {
        /* fall through to national-only inspector */
      }
      // Honest no-data: show a minimal card with any *_national_pct properties present
      const props = Object.assign({}, natProps, { h3_index: h3Index, centroid_lat: lat, centroid_lng: lng });
      handleHexSelection(props);
    }
    // Esri Dark Gray Canvas: keyless dark raster basemap, split into a
    // geometry base and a labels/roads reference overlay. Tiles are {z}/{y}/{x}
    // and stop at z16 -- source maxzoom lets MapLibre overzoom the last real
    // tile instead of pulling Esri's light "Map data not yet available" placeholder.
    const BASEMAP_MAX_TILE_ZOOM = 16;
    const BASEMAP_TILE_ROOT = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas';

    const MAP_STYLE = {
      version: 8,
      sources: {
        'basemap-dark': {
          type: 'raster',
          tiles: [BASEMAP_TILE_ROOT + '/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
          tileSize: 256,
          maxzoom: BASEMAP_MAX_TILE_ZOOM,
          attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        },
        'basemap-dark-labels': {
          type: 'raster',
          tiles: [BASEMAP_TILE_ROOT + '/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'],
          tileSize: 256,
          maxzoom: BASEMAP_MAX_TILE_ZOOM
        }
      },
      layers: [
        {
          id: 'style-background',
          type: 'background',
          paint: { 'background-color': '#080d17' }
        },
        {
          id: 'basemap-dark-layer',
          type: 'raster',
          source: 'basemap-dark',
          minzoom: 0,
          maxzoom: 20,
          paint: {
            // Night-shift tonal treatment: pull the stock Esri dark-gray tiles
            // into the ink canvas so the H3 field reads as the hero, not a
            // screenshot pasted on top of a basemap.
            'raster-saturation': -0.55,
            'raster-contrast': 0.08,
            'raster-brightness-max': 0.65,
            'raster-opacity': 0.70
          }
        },
        {
          id: 'basemap-dark-labels-layer',
          type: 'raster',
          source: 'basemap-dark-labels',
          minzoom: 0,
          maxzoom: 20,
          paint: {
            // Reference labels stay readable but never compete with the hexes.
            'raster-saturation': -0.4,
            'raster-brightness-max': 0.55,
            'raster-opacity': 0.35
          }
        }
      ]
    };

    // Authored percentile ramp (US-432): cool luminance ramp with a reserved
    // warm outlier accent, tuned for the dark canvas. Low = quiet ink-blue
    // (zero evidence, nearly invisible on the dark background), mid = cool teal
    // (signal building neutrally), high = warm gold (concentrated catalyst).
    // The amber outlier stop is reserved for the extreme tail (>92nd pctile).
    // Deliberately no red/coral — no good/bad score, no traffic light.
    const HEX_RAMP = [
      [0, '#0c1628'],
      [35, '#1c3c5c'],
      [60, '#3a8688'],
      [80, '#7ab87a'],
      [92, '#c8b84c'],
      [100, '#e8a050']
    ];

    function hexRampExpr(inputExpr) {
      const out = ['interpolate', ['linear'], inputExpr];
      for (const [stop, color] of HEX_RAMP) out.push(stop, color);
      return out;
    }

    function normalizeBorough(b) {
      if (!b) return '';
      const clean = b.toString().trim();
      const upper = clean.toUpperCase().replace(/[\s\-_/]+/g, '');
      if (upper === 'STATENISLAND') return 'Staten Island';
      if (upper === 'MANHATTAN') return 'Manhattan';
      if (upper === 'BROOKLYN') return 'Brooklyn';
      if (upper === 'QUEENS') return 'Queens';
      if (upper === 'BRONX') return 'Bronx';
      if (upper === 'CENTRALDOWNTOWN') return 'Central / Downtown';
      if (upper === 'NORTHSIDE') return 'North Side';
      if (upper === 'NORTHWESTSIDE') return 'Northwest Side';
      if (upper === 'SOUTHSIDE') return 'South Side';
      if (upper === 'FARNORTHSIDE') return 'Far North Side';
      if (upper === 'SOUTHWESTSIDE') return 'Southwest Side';
      if (upper === 'SANFRANCISCOCORE' || upper === 'SFCORE' || upper === 'SANFRANCISCO') return 'SAN_FRANCISCO_CORE';
      if (upper === 'EASTBAY') return 'EAST_BAY';
      if (upper === 'PENINSULA') return 'PENINSULA';
      if (upper === 'SILICONVALLEYSOUTHBAY' || upper === 'SILICONVALLEY' || upper === 'SOUTHBAY') return 'SILICON_VALLEY_SOUTH_BAY';
      if (upper === 'MARINNORTHBAY' || upper === 'MARIN' || upper === 'NORTHBAY') return 'MARIN_NORTH_BAY';
      if (upper === 'NORTHBAYWINECOUNTRY' || upper === 'WINECOUNTRY' || upper === 'NORTHBAYWINE') return 'NORTH_BAY_WINE_COUNTRY';
      if (upper === 'SOLANOCORRIDOR' || upper === 'SOLANO') return 'SOLANO_CORRIDOR';
      if (upper === 'OUTERCONTRACOSTA' || upper === 'CONTRACOSTA' || upper === 'OUTERCC') return 'OUTER_CONTRA_COSTA';
      if (upper === 'SEATTLECORE') return 'SEATTLE_CORE';
      if (upper === 'NORTHKING') return 'NORTH_KING';
      if (upper === 'EASTSIDE') return 'EASTSIDE';
      if (upper === 'CBDFRENCHQUARTER' || upper === 'FRENCHQUARTER' || upper === 'CBD') return 'CBD_FRENCH_QUARTER';
      if (upper === 'BYWATERMARIGNY' || upper === 'BYWATER' || upper === 'MARIGNY') return 'BYWATER_MARIGNY';
      if (upper === 'UPTOWNCARROLLTON' || upper === 'UPTOWN' || upper === 'CARROLLTON') return 'UPTOWN_CARROLLTON';
      if (upper === 'MIDCITY') return 'MID_CITY';
      if (upper === 'LAKEVIEWGENTILLY' || upper === 'LAKEVIEW' || upper === 'GENTILLY') return 'LAKEVIEW_GENTILLY';
      if (upper === 'NEWORLEANSEAST' || upper === 'NOEAST') return 'NEW_ORLEANS_EAST';
      if (upper === 'WESTBANKALGIERS' || upper === 'ALGIERS' || upper === 'WESTBANK') return 'WEST_BANK_ALGIERS';
      if (upper === 'JEFFERSONMETAIRIEKENNER' || upper === 'METAIRIE' || upper === 'KENNER') return 'JEFFERSON_METAIRIE_KENNER';
      if (upper === 'STBERNARDCHALMETTE' || upper === 'CHALMETTE' || upper === 'STBERNARD') return 'ST_BERNARD_CHALMETTE';
      if (upper === 'DOWNTOWNWATERFRONT' || upper === 'DOWNTOWNNORFOLK') return 'DOWNTOWN_WATERFRONT';
      if (upper === 'GHENTWESTBURG' || upper === 'GHENT') return 'GHENT_WESTBURG';
      if (upper === 'OCEANVIEW') return 'OCEAN_VIEW';
      if (upper === 'CENTRALMILITARYCIRCLE' || upper === 'MILITARYCIRCLE') return 'CENTRAL_MILITARY_CIRCLE';
      if (upper === 'SOUTHNORFOLKBERKLEY' || upper === 'BERKLEY' || upper === 'SOUTHNORFOLK') return 'SOUTH_NORFOLK_BERKLEY';
      if (upper === 'DOWNTOWNMIDTOWNCORKTOWN' || upper === 'CORKTOWN' || upper === 'MIDTOWNDETROIT') return 'DOWNTOWN_MIDTOWN_CORKTOWN';
      if (upper === 'EASTSIDEJEFFERSON' || upper === 'JEFFERSONCHALMERS') return 'EAST_SIDE_JEFFERSON';
      if (upper === 'WESTSIDEGRANDRIVER' || upper === 'GRANDRIVER') return 'WEST_SIDE_GRAND_RIVER';
      if (upper === 'SOUTHWESTMEXICANTOWN' || upper === 'MEXICANTOWN') return 'SOUTHWEST_MEXICANTOWN';
      if (upper === 'NORTHENDHIGHLANDPARK' || upper === 'HIGHLANDPARK') return 'NORTH_END_HIGHLAND_PARK';
      if (upper === 'EASTENGLISHVILLAGEMORNINGSIDE' || upper === 'EASTENGLISHVILLAGE') return 'EAST_ENGLISH_VILLAGE_MORNINGSIDE';
      if (upper === 'DOWNTOWNCAPITOL' || upper === 'CAPITOL') return 'DOWNTOWN_CAPITOL';
      if (upper === 'EASTAUSTINMUELLER' || upper === 'MUELLER' || upper === 'EASTAUSTIN') return 'EAST_AUSTIN_MUELLER';
      if (upper === 'SOUTHAUSTINSOCO' || upper === 'SOCO' || upper === 'SOUTHAUSTIN') return 'SOUTH_AUSTIN_SOCO';
      if (upper === 'NORTHAUSTINDOMAIN' || upper === 'THEDOMAIN' || upper === 'DOMAIN') return 'NORTH_AUSTIN_DOMAIN';
      if (upper === 'WESTAUSTINHILLS' || upper === 'WESTAUSTIN') return 'WEST_AUSTIN_HILLS';
      if (upper === 'PFLUGERVILLEROUNDROCKEDGE' || upper === 'PFLUGERVILLE') return 'PFLUGERVILLE_ROUND_ROCK_EDGE';
      if (upper === 'CENTERCITYRITTENHOUSE' || upper === 'RITTENHOUSE' || upper === 'CENTERCITY') return 'CENTER_CITY_RITTENHOUSE';
      if (upper === 'OLDCITYNORTHERNLIBERTIES' || upper === 'OLDCITY' || upper === 'FISHTOWN') return 'OLD_CITY_NORTHERN_LIBERTIES';
      if (upper === 'SOUTHPHILLYPASSYUNK' || upper === 'SOUTHPHILLY' || upper === 'PASSYUNK') return 'SOUTH_PHILLY_PASSYUNK';
      if (upper === 'WESTPHILLYUNIVERSITYCITY' || upper === 'UNIVERSITYCITY' || upper === 'WESTPHILLY') return 'WEST_PHILLY_UNIVERSITY_CITY';
      if (upper === 'NORTHPHILLYTEMPLE' || upper === 'NORTHPHILLY') return 'NORTH_PHILLY_TEMPLE';
      if (upper === 'NORTHEASTEROOSEVELTBLVD' || upper === 'ROOSEVELTBLVD' || upper === 'NORTHEASTPHILLY') return 'NORTHEAST_ROOSEVELT_BLVD';
      if (upper === 'GERMANTOWNMTAIRY' || upper === 'GERMANTOWN' || upper === 'MTAIRY') return 'GERMANTOWN_MT_AIRY';
      if (upper === 'RIVERWARDSKENSINGTON' || upper === 'KENSINGTON' || upper === 'RIVERWARDS') return 'RIVER_WARDS_KENSINGTON';
      if (upper === 'DOWNTOWNNOMACAPITOLRIVERFRONT' || upper === 'NOMA' || upper === 'DOWNTOWNDC') return 'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT';
      if (upper === 'CAPITOLHILLEASTEEND' || upper === 'CAPITOLHILL') return 'CAPITOL_HILL_EAST_END';
      if (upper === 'DUPONTKALORAMAUPTOWN' || upper === 'DUPONTCIRCLE') return 'DUPONT_KALORAMA_UPTOWN';
      if (upper === 'GEORGETOWNFOGGYBOTTOM' || upper === 'GEORGETOWN' || upper === 'FOGGYBOTTOM') return 'GEORGETOWN_FOGGY_BOTTOM';
      if (upper === 'COLUMBIAHEIGHTSPETWORTH' || upper === 'PETWORTH' || upper === 'COLUMBIAHEIGHTS') return 'COLUMBIA_HEIGHTS_PETWORTH';
      if (upper === 'BROOKLANDRHODEISLANDAVE' || upper === 'BROOKLAND') return 'BROOKLAND_RHODE_ISLAND_AVE';
      if (upper === 'HILLEASTFAIRLINTON' || upper === 'HILLEAST') return 'HILL_EAST_FAIRLINTON';
      if (upper === 'ANACOSTIAEASTOFTHERIVER' || upper === 'ANACOSTIA') return 'ANACOSTIA_EAST_OF_THE_RIVER';
      if (upper === 'SOUTHKING') return 'SOUTH_KING';
      if (upper === 'CENTRALLA') return 'CENTRAL_LA';
      if (upper === 'WESTSIDE') return 'WESTSIDE';
      if (upper === 'SANFERNANDOVALLEY' || upper === 'SFV') return 'SAN_FERNANDO_VALLEY';
      if (upper === 'HARBORSOUTHBAY') return 'HARBOR_SOUTH_BAY';
      if (upper === 'SOUTHLA') return 'SOUTH_LA';
      if (upper === 'EASTSIDESGV') return 'EASTSIDE_SGV';
      return clean;
    }

    function getBoroughClass(b) {
      const n = normalizeBorough(b);
      // Registry division ids (SAN_FRANCISCO_CORE) keep their underscores so
      // they match the .borough-tag.<ID> color rules; display names collapse.
      if (/_/.test(n) && n === n.toUpperCase()) return n;
      return n.replace(/[\s\-_/]+/g, '');
    }

    // Human label for a division. normalizeBorough returns registry ids for
    // most metros (SILICON_VALLEY_SOUTH_BAY); people should read place names.
    const DIVISION_LABELS = {
      SAN_FRANCISCO_CORE: 'SF Core',
      EAST_BAY: 'East Bay',
      PENINSULA: 'Peninsula',
      SILICON_VALLEY_SOUTH_BAY: 'Silicon Valley',
      MARIN_NORTH_BAY: 'Marin / North Bay',
      NORTH_BAY_WINE_COUNTRY: 'Wine Country',
      SOLANO_CORRIDOR: 'Solano Corridor',
      OUTER_CONTRA_COSTA: 'Outer Contra Costa',
      CBD_FRENCH_QUARTER: 'CBD / French Quarter',
      BYWATER_MARIGNY: 'Bywater / Marigny',
      UPTOWN_CARROLLTON: 'Uptown / Carrollton',
      LAKEVIEW_GENTILLY: 'Lakeview / Gentilly',
      WEST_BANK_ALGIERS: 'West Bank / Algiers',
      JEFFERSON_METAIRIE_KENNER: 'Metairie / Kenner',
      ST_BERNARD_CHALMETTE: 'St. Bernard / Chalmette',
      GHENT_WESTBURG: 'Ghent / Westburg',
      CENTRAL_MILITARY_CIRCLE: 'Central / Military Circle',
      SOUTH_NORFOLK_BERKLEY: 'South Norfolk / Berkley',
      DOWNTOWN_MIDTOWN_CORKTOWN: 'Downtown / Midtown',
      EAST_SIDE_JEFFERSON: 'East Side / Jefferson',
      WEST_SIDE_GRAND_RIVER: 'West Side / Grand River',
      SOUTHWEST_MEXICANTOWN: 'Southwest / Mexicantown',
      NORTH_END_HIGHLAND_PARK: 'North End / Highland Park',
      EAST_ENGLISH_VILLAGE_MORNINGSIDE: 'East English Village',
    };
    const DIVISION_WORD_CASE = { LA: 'LA', SF: 'SF', CBD: 'CBD', SGV: 'SGV', DC: 'DC', NW: 'NW', NE: 'NE', SW: 'SW', SE: 'SE' };
    function divisionLabel(b) {
      const n = normalizeBorough(b);
      if (!n) return '';
      if (DIVISION_LABELS[n]) return DIVISION_LABELS[n];
      if (/_/.test(n) && n === n.toUpperCase()) {
        return n.split('_').filter(Boolean).map((w) => DIVISION_WORD_CASE[w]
          || (w.charAt(0) + w.slice(1).toLowerCase())).join(' ');
      }
      return n;
    }

    // Short metro name for tight UI (catalyst cards): drop regional suffixes.
    function shortCityName(name) {
      return String(name || '')
        .replace(/\s*\(.*\)\s*$/, '')
        .replace(/ Bay Area$/, ' Bay')
        .replace(/^San Francisco Bay$/, 'SF Bay')
        .replace(/^New York City$/, 'NYC');
    }

    function deltaClass(v) {
      const n = Number(v);
      if (v == null || v === '' || !Number.isFinite(n) || n === 0) return '';
      return n > 0 ? 'delta-pos' : 'delta-neg';
    }

    // Probability in [0, 1] as a percent; the ends read as bounds, not certainty.
    function formatProbability(v) {
      const n = Number(v);
      if (v == null || v === '' || !Number.isFinite(n)) return '—';
      const pct = n * 100;
      if (pct >= 99.5) return '>99%';
      if (pct <= 0.5) return '<1%';
      return pct.toFixed(0) + '%';
    }

    // Signed percent for a fractional delta; '—' when the value is absent.
    function formatSignedPct(v) {
      const n = Number(v);
      if (v == null || v === '' || !Number.isFinite(n)) return '—';
      return (n > 0 ? '+' : '') + (n * 100).toFixed(1) + '%';
    }

    function renderMetroChips() {
      const nav = document.getElementById('metro-chips');
      if (!nav) return;
      const metros = (snapshotManifest && snapshotManifest.metro_index)
        ? [...snapshotManifest.metro_index]
        : Object.keys(METRO_META).map((cityId) => ({ city_id: cityId, name: cityDisplayName(cityId) }));
      metros.sort((a, b) => String(a.name).localeCompare(String(b.name)));
      const chips = [{ id: null, label: 'All Metros' }]
        .concat(metros.map((m) => ({ id: m.city_id, label: m.name || cityDisplayName(m.city_id) })));
      nav.replaceChildren(...chips.map((chip) => {
        const isActive = (chip.id === null && activeMetroChip === null) || (chip.id !== null && activeMetroChip === chip.id);
        const btn = document.createElement('button');
        btn.className = `borough-btn ${isActive ? 'active' : ''}`;
        btn.dataset.metro = chip.id || '';
        btn.setAttribute('aria-pressed', String(isActive));
        btn.textContent = chip.label;
        btn.addEventListener('click', () => selectMetro(chip.id));
        return btn;
      }));
    }

    // Metro chips are navigation, not data scoping: every metro's tiles stay
    // rendered regardless of the active chip. A chip flies the camera and
    // scopes only the catalyst feed list.
    function selectMetro(cityId) {
      activeMetroChip = cityId || null;
      renderMetroChips();
      renderCatalystFeed();
      if (!map) return;
      if (!cityId) {
        fitNationalView();
        return;
      }
      const metro = ((snapshotManifest && snapshotManifest.metro_index) || [])
        .find((m) => m.city_id === cityId);
      if (metro && metro.bbox) {
        map.fitBounds(
          [[metro.bbox.min_lng, metro.bbox.min_lat], [metro.bbox.max_lng, metro.bbox.max_lat]],
          { padding: 70, maxZoom: 12.4, duration: REDUCED_MOTION ? 0 : 1300 }
        );
      } else {
        fitNationalView();
      }
    }

    function fitNationalView() {
      if (!map) return;
      const metros = (snapshotManifest && snapshotManifest.metro_index) || [];
      if (!metros.length) return;
      const bounds = new maplibregl.LngLatBounds();
      metros.forEach((m) => {
        if (!m.bbox) return;
        bounds.extend([m.bbox.min_lng, m.bbox.min_lat]);
        bounds.extend([m.bbox.max_lng, m.bbox.max_lat]);
      });
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 40, maxZoom: 8, duration: REDUCED_MOTION ? 0 : 1400 });
    }

    // Adds one "Bay Area layers" optgroup to the metric picker for every
    // context metric the snapshot actually joined onto grid cells.
    function populateContextMetrics(block) {
      CONTEXT_METRICS = {};
      const select = document.getElementById('metric-select');
      if (select) select.querySelectorAll('optgroup[data-context]').forEach((g) => g.remove());
      if (!select || !block || !Array.isArray(block.metrics) || block.metrics.length === 0) return;
      const layers = block.layers || {};
      const group = document.createElement('optgroup');
      group.label = 'Bay Area layers';
      group.dataset.context = 'true';
      for (const metric of block.metrics) {
        const layer = layers[metric.layer] || {};
        CONTEXT_METRICS[metric.key] = { ...metric, attribution: layer.attribution || '' };
        const option = document.createElement('option');
        option.value = metric.key;
        option.textContent = metric.label;
        group.appendChild(option);
      }
      select.appendChild(group);
    }

    function formatContextValue(key, value) {
      const num = Number(value);
      if (!Number.isFinite(num)) return '—';
      const unit = (CONTEXT_METRICS[key] || {}).unit;
      if (unit === 'usd') return '$' + Math.round(num).toLocaleString();
      if (unit === 'usd_per_month') return '$' + Math.round(num).toLocaleString() + '/mo';
      if (unit === 'usd_per_km2') return '$' + Math.round(num).toLocaleString() + '/km²';
      if (unit === 'ratio') return num.toFixed(2) + 'x';
      if (unit === 'score') return num.toFixed(1);
      return Math.round(num).toLocaleString();
    }

    async function fetchManifest() {
      try {
        const resp = await fetch('/api/v1/manifest');
        if (resp.ok) {
          snapshotManifest = await resp.json();
          populateContextMetrics(snapshotManifest && snapshotManifest.context_layers);
          const stamp = snapshotManifest && snapshotManifest.generated_at;
          const pillText = document.getElementById('stream-status-text');
          const pillDot = document.getElementById('stream-pulse-dot');
          if (pillText && stamp && stamp.length >= 16) {
            pillText.textContent = 'Snapshot ' + stamp.slice(11, 16) + ' UTC';
            if (pillDot) pillDot.classList.add('static');
            const pill = document.getElementById('stream-status-pill');
            if (pill) {
              pill.classList.add('snapshot');
              pill.title = 'Precomputed snapshot published ' + stamp.slice(0, 10) + ' ' + stamp.slice(11, 16) + ' UTC';
            }
          }
          return true;
        }
      } catch (e) {
        console.debug('Manifest fetch error:', e);
      }
      showToast('Snapshot manifest unavailable — cell-level data cannot load.', 'error');
      return false;
    }

    async function loadAllSubmarkets() {
      SUBMARKETS = {};
      const queue = (snapshotManifest && snapshotManifest.cities) ? [...snapshotManifest.cities] : [];
      const worker = async () => {
        while (queue.length) {
          const city = queue.shift();
          try {
            const resp = await fetch(`/api/v1/submarkets?city_id=${city}`);
            if (!resp.ok) continue;
            const data = await resp.json();
            const subs = data.submarkets || {};
            for (const [name, meta] of Object.entries(subs)) {
              SUBMARKETS[name] = { ...meta, city_id: data.city_id || city };
            }
          } catch (e) { /* one stale/missing metro must not sink the rest */ }
        }
      };
      const concurrency = Math.min(6, Math.max(queue.length, 1));
      await Promise.all(Array.from({ length: concurrency }, worker));
    }

    function deepLinkedCity() {
      // US-31: /dashboard?city=<id> deep links land preselected as a camera
      // preset only. Validate against METRO_META so unknown or absent params
      // fall through to the national view untouched.
      try {
        const requested = new URLSearchParams(window.location.search).get('city');
        if (!requested) return null;
        let candidate = String(requested).toLowerCase().trim();
        if (candidate === 'sf') candidate = 'san_francisco';
        return METRO_META[candidate] ? candidate : null;
      } catch (e) {
        return null;
      }
    }

    window.addEventListener('DOMContentLoaded', async () => {
      const inspector = document.getElementById('inspector-content');
      if (inspector) INSPECTOR_EMPTY_HTML = inspector.innerHTML;
      wireMobileChrome();

      const linked = deepLinkedCity();
      initMap();

      await fetchManifest();
      renderMetroChips();
      if (linked) {
        selectMetro(linked);
      } else {
        fitNationalView();
      }

      loadAllSubmarkets().then(() => renderCatalystFeed());
      await fetchCatalysts();

      document.addEventListener('click', (e) => {
        const wrap = document.querySelector('.search-wrapper');
        if (wrap && !wrap.contains(e.target)) {
          const dd = document.getElementById('search-dropdown');
          if (dd) dd.classList.remove('visible');
          setSearchExpanded(false);
        }
      });
      const dd = document.getElementById('search-dropdown');
      if (dd) {
        dd.addEventListener('click', (e) => {
          const row = e.target.closest('.search-result-item');
          if (row && row.dataset.submarket) selectSearchSubmarket(row.dataset.submarket);
        });
      }
      const feed = document.getElementById('catalyst-feed-list');
      if (feed) {
        feed.addEventListener('click', (e) => {
          const item = e.target.closest('.catalyst-item');
          if (item && item.dataset.h3 && item.dataset.lat !== '' && item.dataset.lng !== '') {
            zoomToHex(item.dataset.h3, Number(item.dataset.lat), Number(item.dataset.lng));
          }
        });
      }
    });

    window.addEventListener('resize', () => {
      if (map) map.resize();
      if (!isMobileLayout()) closeMobilePanels();
      syncMobileChrome();
    });

    // ----- Mobile drawer / search-sheet orchestration -----
    function isMobileLayout() {
      return window.matchMedia('(max-width: 860px)').matches;
    }

    // Publish the live header height so the fixed search sheet lands below it.
    function syncHeaderHeight() {
      const header = document.querySelector('header');
      if (header) {
        document.documentElement.style.setProperty('--header-h', header.offsetHeight + 'px');
      }
    }

    function syncMobileChrome() {
      syncHeaderHeight();
    }

    function syncToolbarActive() {
      document.querySelectorAll('.mobile-toolbar .mt-btn').forEach((btn) => {
        const which = btn.dataset.drawer;
        const cls = which === 'left' ? 'drawer-left-open'
          : which === 'right' ? 'drawer-right-open'
          : which === 'search' ? 'search-open' : '';
        const open = cls ? document.body.classList.contains(cls) : false;
        btn.classList.toggle('active', open);
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    function closeMobilePanels() {
      const wasOpen = document.body.classList.contains('drawer-left-open')
        || document.body.classList.contains('drawer-right-open')
        || document.body.classList.contains('search-open');
      document.body.classList.remove('drawer-left-open', 'drawer-right-open', 'search-open');
      syncToolbarActive();
      if (wasOpen && map) map.resize();
    }

    function openMobilePanel(which) {
      if (!isMobileLayout()) return;
      document.body.classList.remove('drawer-left-open', 'drawer-right-open', 'search-open');
      const cls = which === 'left' ? 'drawer-left-open'
        : which === 'right' ? 'drawer-right-open'
        : which === 'search' ? 'search-open' : '';
      if (!cls) return;
      document.body.classList.add(cls);
      syncToolbarActive();
      if (map) requestAnimationFrame(() => map.resize());
      if (which === 'search') {
        const input = document.getElementById('global-search-input');
        if (input) setTimeout(() => input.focus(), 60);
      }
    }

    function toggleMobilePanel(which) {
      if (!isMobileLayout()) return;
      const cls = which === 'left' ? 'drawer-left-open'
        : which === 'right' ? 'drawer-right-open'
        : which === 'search' ? 'search-open' : '';
      if (cls && document.body.classList.contains(cls)) closeMobilePanels();
      else openMobilePanel(which);
    }

    function wireMobileChrome() {
      const scrim = document.querySelector('.drawer-scrim');
      if (scrim) scrim.addEventListener('click', closeMobilePanels);
      document.querySelectorAll('.mobile-toolbar .mt-btn').forEach((btn) => {
        btn.addEventListener('click', () => toggleMobilePanel(btn.dataset.drawer));
      });
      document.querySelectorAll('[data-close]').forEach((el) => {
        el.addEventListener('click', () => {
          // Desktop: the inspector's close control ends the selection and
          // hands its width back to the map. Mobile: it just shuts the drawer.
          if (!isMobileLayout() && el.closest('.sidebar-right')) clearSelection();
          else closeMobilePanels();
        });
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMobilePanels();
      });
      syncMobileChrome();
      // The header reflows after load (metro chips render, web fonts swap in),
      // so track its height continuously instead of measuring once.
      const header = document.querySelector('header');
      if (header && 'ResizeObserver' in window) {
        new ResizeObserver(syncHeaderHeight).observe(header);
      }
    }

    function onGlobalSearch(query) {
      const q = (query || '').toLowerCase().trim();
      const dd = document.getElementById('search-dropdown');
      if (!dd) return;

      if (!q) {
        dd.classList.remove('visible');
        dd.innerHTML = '';
        setSearchExpanded(false);
        return;
      }

      const matches = Object.entries(SUBMARKETS).filter(([name, meta]) => {
        return name.toLowerCase().includes(q) || 
               normalizeBorough(meta.borough).toLowerCase().includes(q) ||
               (meta.description && meta.description.toLowerCase().includes(q));
      }).slice(0, 8);

      if (matches.length === 0) {
        dd.innerHTML = '<div class="search-empty">No submarkets found. Press Enter to search as coordinate or H3.</div>';
        dd.classList.add('visible');
        setSearchExpanded(false);
        return;
      }

      dd.replaceChildren(...matches.map(([name, meta], i) => {
        const bClass = getBoroughClass(meta.borough);
        const row = document.createElement('div');
        row.className = 'search-result-item';
        row.id = 'search-opt-' + i;
        row.setAttribute('role', 'option');
        row.setAttribute('aria-selected', 'false');
        row.dataset.submarket = name;
        const line = document.createElement('span');
        line.className = 'search-result-line';
        const strong = document.createElement('strong');
        strong.textContent = name;
        const right = document.createElement('span');
        right.className = 'item-sub';
        const lims = Number(meta.base_lims);
        right.textContent = Number.isFinite(lims) && meta.base_lims != null ? 'LIMS ' + lims.toFixed(1) : '';
        line.append(strong, right);
        row.append(line);
        const label = divisionLabel(meta.borough);
        if (label) {
          const tag = document.createElement('span');
          tag.className = 'borough-tag ' + bClass;
          tag.textContent = label;
          row.append(tag);
        }
        return row;
      }));
      searchActiveIndex = -1;
      dd.classList.add('visible');
      setSearchExpanded(true);
    }

    let searchActiveIndex = -1;

    function setSearchExpanded(open) {
      const input = document.getElementById('global-search-input');
      if (!input) return;
      input.setAttribute('aria-expanded', String(open));
      if (!open) input.removeAttribute('aria-activedescendant');
    }

    // Arrow keys walk the suggestion list (listbox/combobox pattern); Enter
    // picks the highlighted row, or searches the raw text when none is.
    function onSearchKeydown(event) {
      const dd = document.getElementById('search-dropdown');
      const rows = dd ? [...dd.querySelectorAll('.search-result-item')] : [];
      const input = event.currentTarget;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        if (!rows.length) return;
        event.preventDefault();
        const step = event.key === 'ArrowDown' ? 1 : -1;
        searchActiveIndex = (searchActiveIndex + step + rows.length) % rows.length;
        rows.forEach((r, i) => r.setAttribute('aria-selected', String(i === searchActiveIndex)));
        const active = rows[searchActiveIndex];
        input.setAttribute('aria-activedescendant', active.id);
        active.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter') {
        event.preventDefault();
        const active = rows[searchActiveIndex];
        if (active && dd.classList.contains('visible')) selectSearchSubmarket(active.dataset.submarket);
        else executeSearch();
      } else if (event.key === 'Escape' && dd && dd.classList.contains('visible')) {
        dd.classList.remove('visible');
        setSearchExpanded(false);
      }
    }

    function selectSearchSubmarket(name) {
      const dd = document.getElementById('search-dropdown');
      if (dd) dd.classList.remove('visible');
      setSearchExpanded(false);
      const input = document.getElementById('global-search-input');
      if (input) input.value = name;
      zoomToSubmarket(name);
    }

    function executeSearch() {
      const input = document.getElementById('global-search-input');
      if (!input) return;
      const val = input.value.trim();
      if (!val) return;

      const dd = document.getElementById('search-dropdown');
      if (dd) dd.classList.remove('visible');
      setSearchExpanded(false);

      const foundKey = Object.keys(SUBMARKETS).find(k => k.toLowerCase() === val.toLowerCase());
      if (foundKey) {
        zoomToSubmarket(foundKey);
        return;
      }

      searchCoordinateOrHex(val);
    }

    function initMap() {
      try {
        map = new maplibregl.Map({
          container: 'map',
          style: MAP_STYLE,
          center: [-96.6, 38.9],
          zoom: 4.2,
          pitch: 0,
          bearing: 0,
          antialias: true
        });

        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showCompass: false }), 'bottom-right');
        // The canvas width changes when the inspector opens or closes, not
        // only on window resize, so follow the container itself.
        const mapEl = document.getElementById('map');
        if (mapEl && 'ResizeObserver' in window) {
          new ResizeObserver(() => { if (map) map.resize(); }).observe(mapEl);
        }

        map.on('load', () => {
          map.resize();
          setupGridLayers();
          setupNationalLayers();
          map.on('moveend', () => { scheduleViewportLoad(); scheduleNationalLoad(); });
          map.on('zoomend', () => { scheduleViewportLoad(); scheduleNationalLoad(); updateLayerVisibilities(); });
          // Orientation telemetry: keep the readout in sync with the camera.
          map.on('move', updateMapReadout);
          updateMapReadout();
          regenerateLegend();
          scheduleViewportLoad();
          scheduleNationalLoad();
          setInterval(fetchCatalysts, 15000);
        });

        const popup = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 12
        });

        const showPopup = (e) => {
          if (e.features && e.features.length > 0) {
            map.getCanvas().style.cursor = 'pointer';
            const f = e.features[0];
            const props = f.properties || {};
            const coords = e.lngLat;
            const subInfo = getSubmarketInfoByCoords(props.centroid_lat || coords.lat, props.centroid_lng || coords.lng);
            const subName = props.submarket || (subInfo ? subInfo.name : 'Micro-Block');
            const rawBorough = props.borough || (subInfo ? subInfo.meta.borough : '');
            const borough = divisionLabel(rawBorough);
            const bClass = getBoroughClass(rawBorough);
            const contextMetric = CONTEXT_METRICS[currentMetric];
            const popupRow = (label, value, cls = '') => `
                  <div class="popup-row">
                    <span class="popup-lbl">${escapeHtml(label)}</span>
                    <strong class="popup-val ${cls}">${value}</strong>
                  </div>`;
            const fmtNum = (v, digits) => (v != null && v !== '' && Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : '—');
            const contextRow = contextMetric
              ? popupRow(contextMetric.label, props[currentMetric] == null ? 'No data' : escapeHtml(formatContextValue(currentMetric, props[currentMetric])))
              : '';

            popup.setLngLat(coords)
              .setHTML(`
                <div class="popup-card">
                  <div class="popup-head">
                    <strong class="popup-title">${escapeHtml(subName)}</strong>
                    ${borough ? `<span class="borough-tag ${escapeHtml(bClass)}">${escapeHtml(borough)}</span>` : ''}
                  </div>
                  ${props.city_name ? `<div class="popup-city">${escapeHtml(props.city_name)}</div>` : ''}
                  ${popupRow('LIMS score', fmtNum(props.lims_score, 1))}
                  ${popupRow('National percentile', fmtNum(props.lims_score_national_pct, 0))}
                  ${popupRow('Metro percentile', fmtNum(props.lims_score_metro_pct, 0))}
                  ${popupRow('6M return', formatSignedPct(props.delta_6m_p50), deltaClass(props.delta_6m_p50))}${contextRow}
                </div>
              `)
              .addTo(map);
          }
        };

        map.on('mousemove', 'h3-hex-fill', (e) => {
          showPopup(e);
          if (e.features && e.features.length > 0) {
            const h3 = e.features[0].properties.h3_index;
            if (h3 !== hoveredH3Index) {
              hoveredH3Index = h3;
              if (map.getLayer('h3-hex-hover')) {
                map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], h3]);
              }
            }
          }
        });
        map.on('mouseleave', 'h3-hex-fill', () => {
          map.getCanvas().style.cursor = '';
          popup.remove();
          if (hoveredH3Index) {
            hoveredH3Index = null;
            if (map.getLayer('h3-hex-hover')) {
              map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], '']);
            }
          }
        });

        map.on('mousemove', 'h3-hex-extrusion', (e) => {
          showPopup(e);
          if (e.features && e.features.length > 0) {
            const h3 = e.features[0].properties.h3_index;
            if (h3 !== hoveredH3Index) {
              hoveredH3Index = h3;
              if (map.getLayer('h3-hex-hover')) {
                map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], h3]);
              }
            }
          }
        });
        map.on('mouseleave', 'h3-hex-extrusion', () => {
          map.getCanvas().style.cursor = '';
          popup.remove();
          if (hoveredH3Index) {
            hoveredH3Index = null;
            if (map.getLayer('h3-hex-hover')) {
              map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], '']);
            }
          }
        });

        map.on('click', 'h3-hex-fill', (e) => {
          if (e.features && e.features.length > 0) {
            if (map.getLayer('h3-hex-hover')) {
              map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], '']);
            }
            handleHexSelection(e.features[0].properties);
          }
        });

        map.on('click', 'h3-hex-extrusion', (e) => {
          if (e.features && e.features.length > 0) {
            if (map.getLayer('h3-hex-hover')) {
              map.setFilter('h3-hex-hover', ['==', ['get', 'h3_index'], '']);
            }
            handleHexSelection(e.features[0].properties);
          }
        });
      } catch (err) {
        console.error('Map initialization error:', err);
      }
    }

    // ---- Viewport lazy loading ---------------------------------------------
    // Cells live in res-5 parent-H3 tiles published to KV by the snapshot
    // builder. On camera settle we sample the visible bounds for parents,
    // keep only tiles that exist in the manifest's tile_index, and fetch the
    // missing ones in small batched requests, center-out first.
    function scheduleViewportLoad() {
      clearTimeout(viewportDebounceTimer);
      viewportDebounceTimer = setTimeout(updateViewportTiles, 220);
    }

    function parentsCoveringBounds(bounds, res) {
      if (typeof h3 === 'undefined' || !bounds) return [];
      const west = bounds.getWest();
      const east = bounds.getEast();
      const south = bounds.getSouth();
      const north = bounds.getNorth();
      const latPad = Math.max(0.35, (north - south) * 0.18);
      const lngPad = Math.max(0.45, (east - west) * 0.18);
      const minLat = Math.max(-84, south - latPad);
      const maxLat = Math.min(84, north + latPad);
      const minLng = Math.max(-179.9, west - lngPad);
      const maxLng = Math.min(179.9, east + lngPad);
      const parents = new Set();
      // Sample step stays under the parent-hex diameter for this resolution so
      // sampling cannot skip a tile; coarser LOD uses coarser parents.
      const stepLat = LOD_PARENT_STEP[res] || 0.14;
      const maxSamples = LOD_PARENT_SAMPLES[res] || 4000;
      let samples = 0;
      for (let lat = minLat; lat <= maxLat && samples < maxSamples; lat += stepLat) {
        const stepLng = stepLat / Math.max(0.25, Math.cos(lat * Math.PI / 180));
        for (let lng = minLng; lng <= maxLng && samples < maxSamples; lng += stepLng) {
          parents.add(h3.latLngToCell(lat, lng, res));
          samples += 1;
        }
      }
      return [...parents];
    }

    function setHexLayersVisible(visible) {
      if (!map) return;
      if (map.getLayer('h3-hex-fill')) {
        map.setLayoutProperty('h3-hex-fill', 'visibility', visible && currentPerspective === '2D' ? 'visible' : 'none');
      }
      if (map.getLayer('h3-hex-extrusion')) {
        map.setLayoutProperty('h3-hex-extrusion', 'visibility', visible && currentPerspective === '3D' ? 'visible' : 'none');
      }
    }

    function updateViewportTiles() {
      if (!map || !snapshotManifest) return;
      const z = map.getZoom();
      const hint = document.getElementById('zoom-hint');
      if (hint) hint.hidden = true; // dead-zone hint retired; LOD pyramid covers country view
      if (z < ZOOM_FLOOR) {
        setHexLayersVisible(false);
        return; // below metro band: do not fetch metro tiles
      }
      // Pick the LOD level for this zoom and fetch only that level's parents.
      const res = lodForZoom(z);
      const tileIndexes = snapshotManifest.tile_indexes || {};
      const tileIndex = tileIndexes[String(res)] || snapshotManifest.tile_index || {};
      const candidates = parentsCoveringBounds(map.getBounds(), LOD_TO_PARENT_RES[res] || 5)
        .filter((parent) => Object.prototype.hasOwnProperty.call(tileIndex, parent))
        .filter((parent) => !fetchedTiles.has(parent) && !tilesInFlight.has(parent));

      const center = map.getCenter();
      candidates.sort((a, b) => parentDistance(a, center) - parentDistance(b, center));

      pendingTileParents.length = 0;
      pendingTileParents.push(...candidates);
      activeLodRes = res;
      drainTileQueue();
    }

    function parentDistance(parent, center) {
      const [lat, lng] = h3.cellToLatLng(parent);
      return Math.abs(lat - center.lat) + Math.abs(lng - center.lng);
    }

    function drainTileQueue() {
      while (tileFetchesActive < TILE_FETCH_CONCURRENCY && pendingTileParents.length) {
        const batch = pendingTileParents.splice(0, TILE_PARENTS_PER_REQUEST);
        batch.forEach((parent) => tilesInFlight.add(parent));
        tileFetchesActive += 1;
        fetchTileBatch(batch);
      }
    }

    async function fetchTileBatch(batch) {
      const generation = tileLoadGeneration;
      const res = activeLodRes || 9;
      try {
        const resp = await fetch(`/api/v1/gridtiles?res=${res}&parents=${batch.join(',')}`);
        if (resp.ok) {
          const payload = await resp.json();
          if (generation === tileLoadGeneration) mergeTilePayload(payload);
        }
        // Absent-from-KV parents will not appear later either — mark fetched.
        batch.forEach((parent) => fetchedTiles.add(parent));
      } catch (e) {
        console.debug('Tile fetch error:', e);
      } finally {
        batch.forEach((parent) => tilesInFlight.delete(parent));
        tileFetchesActive -= 1;
        drainTileQueue();
        applyGridData();
      }
    }

    function mergeTilePayload(payload) {
      const features = payload && payload.features ? payload.features : [];
      for (const feature of features) {
        const cell = feature.properties && feature.properties.h3_index;
        if (!cell) continue;
        tileFeatures.set(cell, feature);
      }
      if (features.length) gridDirty = true;
    }

    function applyGridData() {
      if (!gridDirty || !map || !map.getSource('h3-grid-source')) return;
      gridDirty = false;
      // LRU-by-distance eviction to cap memory and avoid frame spikes
      evictDistantGridFeatures();
      gridGeoJSON = { type: 'FeatureCollection', features: [...tileFeatures.values()] };
      map.getSource('h3-grid-source').setData(gridGeoJSON);
      // Programmatic camera jumps can leave the repaint cycle suppressed;
      // nudge it so freshly merged tiles index immediately.
      map.triggerRepaint();
    }

    function evictDistantGridFeatures(maxCount = 120000) {
      const size = tileFeatures.size;
      if (size <= maxCount) return;
      const center = map.getCenter();
      const scored = [];
      for (const [cell, feature] of tileFeatures.entries()) {
        let lat = feature?.properties?.centroid_lat;
        let lng = feature?.properties?.centroid_lng;
        if ((!Number.isFinite(lat) || !Number.isFinite(lng)) && typeof h3 !== 'undefined' && h3.cellToLatLng) {
          const c = h3.cellToLatLng(cell);
          lat = c[0];
          lng = c[1];
        }
        const d = (Number.isFinite(lat) && Number.isFinite(lng)) ? haversineDistance(center.lat, center.lng, lat, lng) : 9999;
        scored.push([cell, d]);
      }
      scored.sort((a, b) => a[1] - b[1]);
      for (let i = maxCount; i < scored.length; i++) {
        tileFeatures.delete(scored[i][0]);
      }
    }

    function setupGridLayers() {
      if (!map || map.getSource('h3-grid-source')) return;

      map.addSource('h3-grid-source', {
        type: 'geojson',
        data: gridGeoJSON || { type: 'FeatureCollection', features: [] }
      });

      // 2D Fill Layer — value-aware opacity so high-percentile cells read as
      // emphasis instead of every cell sitting at one flat alpha. Low-value
      // cells fade into the background, reducing visual noise at dense metro
      // zoom levels.
      map.addLayer({
        id: 'h3-hex-fill',
        type: 'fill',
        source: 'h3-grid-source',
        layout: { visibility: currentPerspective === '2D' ? 'visible' : 'none' },
        paint: {
          'fill-color': hexRampExpr(['get', 'lims_score_national_pct']),
          'fill-opacity': [
            'interpolate', ['linear'],
            ['coalesce', ['get', 'lims_score_national_pct'], 0],
0, 0.25,
            40, 0.45,
            80, 0.7,
            92, 0.88
          ]
        }
      });

      // 2D Line Outline Layer — zoom-scaled boundary stroke with opacity
      // that fades at metro-wide zooms so the dense grid never reads as
      // checkerboard noise. Only the selected/hovered cell gets a full-opacity
      // outline; the rest are a faint slate whisper.
      map.addLayer({
        id: 'h3-hex-line',
        type: 'line',
        source: 'h3-grid-source',
        paint: {
          'line-color': [
            'interpolate', ['linear'], ['zoom'],
            7, 'rgba(148, 163, 184, 0.04)',
            10, 'rgba(148, 163, 184, 0.15)',
            14, 'rgba(148, 163, 184, 0.35)'
          ],
          'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.3, 10, 0.6, 14, 1.0]
        }
      });

      // 3D Fill Extrusion Layer
      map.addLayer({
        id: 'h3-hex-extrusion',
        type: 'fill-extrusion',
        source: 'h3-grid-source',
        layout: { visibility: currentPerspective === '3D' ? 'visible' : 'none' },
        paint: {
          'fill-extrusion-color': hexRampExpr(['get', 'lims_score_national_pct']),
          'fill-extrusion-height': [
            '*',
            ['max', 0, ['-', ['coalesce', ['get', 'lims_score_national_pct'], 50], 40]],
            18
          ],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.92
        }
      });

      // Selected Hex Highlight — fill companion + outline so the selection
      // stays legible on a busy neighborhood (color + geometry, plus the
      // inspector panel opening is the primary non-color signal).
      map.addLayer({
        id: 'h3-hex-selected-fill',
        type: 'fill',
        source: 'h3-grid-source',
        filter: ['==', ['get', 'h3_index'], ''],
        paint: {
          'fill-color': 'rgba(56, 189, 248, 0.3)',
          'fill-opacity': 1
        }
      });
      map.addLayer({
        id: 'h3-hex-selected',
        type: 'line',
        source: 'h3-grid-source',
        filter: ['==', ['get', 'h3_index'], ''],
        paint: {
          'line-color': '#38bdf8',
          'line-width': 2.5
        }
      });

      // Hover Highlight — subtle glow on the cell under the cursor so the
      // grid feels interactive without needing a click. Cleared on mouseleave.
      map.addLayer({
        id: 'h3-hex-hover',
        type: 'line',
        source: 'h3-grid-source',
        filter: ['==', ['get', 'h3_index'], ''],
        paint: {
          'line-color': 'rgba(56, 189, 248, 0.55)',
          'line-width': 1.8
        }
      });
    }

    function updateMetricVisuals() {
      if (!map) return;
      const metricEl = document.getElementById('metric-select');
      if (!metricEl) return;
      currentMetric = metricEl.value;
      const pctProp = `${currentMetric}_national_pct`;
      const legendTitle = document.getElementById('legend-metric-title');

      const contextMetric = CONTEXT_METRICS[currentMetric];
      const titleSuffix = contextMetric ? ' — Percentile Within Coverage' : ' — National Percentile';
      if (legendTitle) legendTitle.innerText = (contextMetric ? contextMetric.label : ({
        lims_score: 'LIMS Momentum Score',
        delta_6m_p50: '6M Expected Return (p50)',
        delta_12m_spillover: '12M Spatial Spillover',
        prob_18m_macro_outperformance: '18M Macro Outperformance'
      })[currentMetric]) + titleSuffix;
      const noDataRow = document.getElementById('legend-no-data');
      if (noDataRow) noDataRow.hidden = !contextMetric;
      const attribution = document.getElementById('legend-attribution');
      if (attribution) {
        attribution.hidden = !(contextMetric && contextMetric.attribution);
        attribution.textContent = contextMetric && contextMetric.attribution ? 'Source: ' + contextMetric.attribution : '';
      }

      // One shared percentile color ramp; only extrusion height differs per metric.
      // Context metrics exist only where their layer has coverage: cells
      // without a percentile render as flat "no data", never as a low value.
      const rampExpr = hexRampExpr(['get', pctProp]);
      const colorExpr = contextMetric ? ['case', ['has', pctProp], rampExpr, NO_DATA_FILL] : rampExpr;
      const valueOpacity = [
        'interpolate', ['linear'],
        ['coalesce', ['get', pctProp], 0],
0, 0.25,
        40, 0.45,
        80, 0.7,
        92, 0.88
      ];
      const opacityExpr = contextMetric ? ['case', ['has', pctProp], valueOpacity, 1] : valueOpacity;
      const heightFactor = {
        lims_score: ['*', ['max', 0, ['-', ['coalesce', ['get', pctProp], 50], 40]], 18],
        delta_6m_p50: ['*', ['max', 0, ['coalesce', ['get', pctProp], 50]], 40],
        delta_12m_spillover: ['*', ['max', 0, ['coalesce', ['get', pctProp], 50]], 45],
        prob_18m_macro_outperformance: ['*', ['max', 0, ['coalesce', ['get', pctProp], 50]], 9]
      }[currentMetric] || ['*', ['coalesce', ['get', pctProp], 0], 12];

      if (map.getLayer('h3-hex-fill')) {
        map.setPaintProperty('h3-hex-fill', 'fill-color', colorExpr);
        map.setPaintProperty('h3-hex-fill', 'fill-opacity', opacityExpr);
      }
      if (map.getLayer('h3-hex-extrusion')) {
        map.setPaintProperty('h3-hex-extrusion', 'fill-extrusion-color', colorExpr);
        map.setPaintProperty('h3-hex-extrusion', 'fill-extrusion-height', heightFactor);
      }
      // Reflect metric change on the national LOD overlay
      updateNationalLayerPaint();
    }

    // Legend truth (US-431): the gradient bar and its stop ticks are
    // regenerated from HEX_RAMP — the same constant that drives the map
    // layers — so the legend can never drift from what is rendered.
    function regenerateLegend() {
      const bar = document.querySelector('.map-legend-card .legend-bar');
      if (bar) {
        const gradient = 'linear-gradient(to right, ' + HEX_RAMP.map(([stop, color]) => `${color} ${stop}%`).join(', ') + ')';
        bar.style.background = gradient;
      }
      const ticks = document.getElementById('legend-ticks');
      if (ticks) {
        const stops = HEX_RAMP.map(([s]) => s).filter((s) => s > 0 && s < 100);
        ticks.replaceChildren(...stops.map((stop) => {
          const span = document.createElement('span');
          span.className = 'legend-tick';
          span.style.left = `${stop}%`;
          span.textContent = String(stop);
          return span;
        }));
      }
    }

    // Orientation readout (US-431): scale bar + zoom/coordinate telemetry so a
    // deep link like ?city=nyc has an anchor. Pure telemetry — reads the
    // camera, invents nothing.
    function updateMapReadout() {
      if (!map) return;
      const zoomEl = document.getElementById('map-zoom-readout');
      const coordsEl = document.getElementById('map-coords-readout');
      const scaleLabel = document.getElementById('map-scale-label');
      const scaleRule = document.getElementById('map-scale-rule');
      const z = map.getZoom();
      const center = map.getCenter();
      if (zoomEl) zoomEl.textContent = `z${z.toFixed(1)}`;
      if (coordsEl) coordsEl.textContent = `${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
      if (scaleLabel && scaleRule) {
        // Meters per pixel at the map center latitude (Web Mercator).
        const mPerPx = 156543.03392 * Math.cos((center.lat * Math.PI) / 180) / Math.pow(2, z);
        const maxPx = 90;
        const nice = [25, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000];
        // Largest nice distance that still fits in maxPx (smallest as floor).
        let meters = nice[0];
        for (const candidate of nice) {
          if (candidate / mPerPx <= maxPx) meters = candidate;
          else break;
        }
        const px = Math.round(meters / mPerPx);
        scaleRule.style.width = `${px}px`;
        scaleLabel.textContent = meters >= 1000 ? `${meters / 1000} km` : `${meters} m`;
      }
    }
    function setPerspective(mode) {
      currentPerspective = mode;
      const btn3d = document.getElementById('btn-3d');
      const btn2d = document.getElementById('btn-2d');
      if (btn3d) { btn3d.classList.toggle('active', mode === '3D'); btn3d.setAttribute('aria-pressed', String(mode === '3D')); }
      if (btn2d) { btn2d.classList.toggle('active', mode === '2D'); btn2d.setAttribute('aria-pressed', String(mode === '2D')); }

      if (map) {
        updateLayerVisibilities();

        map.easeTo({
          pitch: mode === '3D' ? 52 : 0,
          bearing: mode === '3D' ? -15 : 0,
          duration: REDUCED_MOTION ? 0 : 900
        });
      }
    }
    function updateLayerVisibilities() {
      if (!map) return;
      const z = map.getZoom();
      // Metro LOD pyramid renders at every zoom above the floor — no dead zone
      // between the national layer and the metro hexes (US-413). The national
      // overlay doubles as the LODES fallback only below the metro band.
      const showMetro = z >= ZOOM_FLOOR;
      setHexLayersVisible(showMetro);
      // National overlay visibility is driven by zoom + perspective
      updateNationalLayerVisibilities();
      scheduleNationalLoad();
    }

    function zoomToSubmarket(name) {
      if (!name) return;
      const meta = SUBMARKETS[name];
      if (!meta) return;

      if (map) {
        map.flyTo({
          center: [meta.lng, meta.lat],
          zoom: Math.min(meta.zoom || FOCUS_ZOOM, FOCUS_ZOOM + 0.5),
          pitch: currentPerspective === '3D' ? Math.min(meta.pitch || FOCUS_PITCH, FOCUS_PITCH) : 0,
          bearing: -15,
          duration: REDUCED_MOTION ? 0 : 1200
        });
      }

      let foundProps = null;
      if (gridGeoJSON && gridGeoJSON.features) {
        const found = gridGeoJSON.features.find(f => f.properties && f.properties.submarket === name);
        if (found) foundProps = found.properties;
      }

      if (foundProps) {
        handleHexSelection(foundProps);
      } else {
        const h3Cell = (typeof h3 !== 'undefined') ? h3.latLngToCell(meta.lat, meta.lng, 9) : 'hex_' + name.toLowerCase();
        handleHexSelection({
          h3_index: h3Cell,
          submarket: name,
          borough: normalizeBorough(meta.borough),
          description: meta.description,
          centroid_lat: meta.lat,
          centroid_lng: meta.lng,
          lims_score: meta.base_lims,
          capex_density_decayed: meta.capex,
          permit_velocity: meta.permit_vel,
          shift_ratio_311: meta.shift_ratio,
          sla_new_filings_90d: meta.sla,
          __baseline: true
        });
      }
    }

    async function fetchCatalysts() {
      try {
        const resp = await fetch('/api/v1/catalysts/all');
        if (resp.ok) {
          const data = await resp.json();
          catalystAlerts = data.catalysts || [];
          renderCatalystFeed();
          return;
        }
        if (!catalystAlerts.length) {
          showToast('No combined catalyst snapshot published yet.', 'error');
        }
      } catch (e) {
        console.debug('Catalyst fetch error:', e);
      }
      renderCatalystFeed();
    }

    function renderCatalystFeed() {
      const container = document.getElementById('catalyst-feed-list');
      const countBadge = document.getElementById('stat-active-catalysts');
      if (!container) return;

      const filtered = catalystAlerts.filter(c => (
        !activeMetroChip || c.city_id === activeMetroChip
      ));


      if (countBadge) {
        countBadge.innerText = String(filtered.length);
        countBadge.setAttribute('aria-label', `${filtered.length} catalysts`);
      }

      if (filtered.length === 0) {
        container.innerHTML = `<div class="catalyst-empty">No catalysts${activeMetroChip ? ` in ${escapeHtml(cityDisplayName(activeMetroChip))}` : ''}</div>`;
        return;
      }

      container.replaceChildren(...filtered.map((c) => {
        const subInfo = getSubmarketInfoByCoords(c.centroid_lat, c.centroid_lng);
        const submarket = c.submarket || (subInfo ? subInfo.name : 'Unnamed cluster');
        const rawBorough = c.borough || (subInfo ? subInfo.meta.borough : '');
        const borough = divisionLabel(rawBorough);
        const bClass = getBoroughClass(rawBorough);
        const lat = c.centroid_lat != null ? c.centroid_lat : (subInfo ? subInfo.meta.lat : null);
        const lng = c.centroid_lng != null ? c.centroid_lng : (subInfo ? subInfo.meta.lng : null);
        const isSelected = selectedH3Index === c.h3_index;

        // A real button: focusable, and Enter/Space activate it for free.
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'catalyst-item' + (isSelected ? ' selected' : '');
        item.setAttribute('aria-pressed', String(isSelected));
        item.dataset.h3 = c.h3_index || '';
        item.dataset.lat = lat == null ? '' : String(lat);
        item.dataset.lng = lng == null ? '' : String(lng);
        const top = document.createElement('div');
        top.className = 'catalyst-item-top';
        const nameEl = document.createElement('span');
        nameEl.className = 'catalyst-name';
        nameEl.textContent = submarket;
        const limsEl = document.createElement('span');
        limsEl.className = 'catalyst-lims-tag';
        const limsNum = Number(c.lims_score);
        limsEl.textContent = c.lims_score != null && Number.isFinite(limsNum) ? limsNum.toFixed(1) : '—';
        top.append(nameEl, limsEl);
        const bottom = document.createElement('div');
        bottom.className = 'catalyst-item-bottom';
        const tags = document.createElement('span');
        tags.className = 'catalyst-tags';
        if (borough) {
          const boroughEl = document.createElement('span');
          boroughEl.className = 'borough-tag ' + bClass;
          boroughEl.textContent = borough;
          tags.append(boroughEl);
        }
        // The metro is implied once a metro chip scopes the feed.
        if (c.city_name && !activeMetroChip) {
          const cityEl = document.createElement('span');
          cityEl.className = 'borough-tag';
          cityEl.textContent = shortCityName(c.city_name);
          cityEl.title = c.city_name;
          tags.append(cityEl);
        }
        const deltaEl = document.createElement('span');
        deltaEl.className = 'delta-tag ' + deltaClass(c.delta_6m_p50);
        deltaEl.textContent = formatSignedPct(c.delta_6m_p50) + ' 6M';
        bottom.append(tags, deltaEl);
        item.append(top, bottom);
        return item;
      }));
    }

    // Camera for focusing one cell or submarket (catalyst, search, deep
    // link): neighbourhood scale, so the selection keeps its surroundings and
    // tall extrusions (up to ~1 km) don't fill the viewport.
    const FOCUS_ZOOM = 12.9;
    const FOCUS_PITCH = 40;

    function zoomToHex(h3Index, lat, lng) {
      selectedH3Index = h3Index;
      if (map) {
        map.flyTo({
          center: [lng, lat],
          zoom: FOCUS_ZOOM,
          pitch: currentPerspective === '3D' ? FOCUS_PITCH : 0,
          bearing: -12,
          duration: REDUCED_MOTION ? 0 : 1100
        });

        if (map.getLayer('h3-hex-selected')) {
          map.setFilter('h3-hex-selected', ['==', ['get', 'h3_index'], h3Index]);
          if (map.getLayer('h3-hex-selected-fill')) map.setFilter('h3-hex-selected-fill', ['==', ['get', 'h3_index'], h3Index]);
        }
      }

      renderCatalystFeed();
      inspectH3Cell(h3Index, lat, lng);
    }

    async function inspectH3Cell(h3Index, lat, lng) {
      let props = null;
      if (gridGeoJSON && gridGeoJSON.features) {
        const f = gridGeoJSON.features.find(item => item.properties && item.properties.h3_index === h3Index);
        if (f) props = f.properties;
      }

      if (!props) {
        try {
          const resp = await fetch('/api/v1/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ h3_index: h3Index, include_shap: true })
          });
          if (resp.ok) {
            props = await resp.json();
            const subInfo = getSubmarketInfoByCoords(lat, lng);
            props.submarket = subInfo ? subInfo.name : 'Target Micro-Parcel';
            props.borough = normalizeBorough(subInfo ? subInfo.meta.borough : getBoroughNameByCoords(lat, lng));
            props.description = subInfo ? subInfo.meta.description : 'Custom spatial coordinate';
            props.centroid_lat = lat;
            props.centroid_lng = lng;
          }
        } catch (e) {}
      }

      if (!props) {
        const subInfo = getSubmarketInfoByCoords(lat, lng);
        props = {
          h3_index: h3Index,
          submarket: subInfo ? subInfo.name : 'Selected Parcel',
          borough: normalizeBorough(subInfo ? subInfo.meta.borough : getBoroughNameByCoords(lat, lng)),
          description: subInfo ? subInfo.meta.description : 'Selected coordinate — outside published cell snapshots',
          centroid_lat: lat,
          centroid_lng: lng,
          lims_score: subInfo ? subInfo.meta.base_lims : undefined,
          capex_density_decayed: subInfo ? subInfo.meta.capex : undefined,
          permit_velocity: subInfo ? subInfo.meta.permit_vel : undefined,
          shift_ratio_311: subInfo ? subInfo.meta.shift_ratio : undefined,
          sla_new_filings_90d: subInfo ? subInfo.meta.sla : undefined,
          __baseline: true
        };
      }

      handleHexSelection(props);
    }

    let INSPECTOR_EMPTY_HTML = null;

    // Desktop keeps the inspector collapsed until something is selected, so
    // the map gets the width; the body class drives that (CSS, >860px only).
    function clearSelection() {
      selectedH3Index = null;
      if (map) {
        ['h3-hex-selected', 'h3-hex-selected-fill'].forEach((id) => {
          if (map.getLayer(id)) map.setFilter(id, ['==', ['get', 'h3_index'], '']);
        });
      }
      const container = document.getElementById('inspector-content');
      if (container && INSPECTOR_EMPTY_HTML != null) container.innerHTML = INSPECTOR_EMPTY_HTML;
      if (shapChart) { shapChart.destroy(); shapChart = null; }
      document.body.classList.add('inspector-empty');
      renderCatalystFeed();
    }

    function handleHexSelection(props) {
      if (!props) return;
      selectedH3Index = props.h3_index;
      document.body.classList.remove('inspector-empty');
      // Mobile: the inspector is an off-canvas drawer, so surface it on every
      // selection (map click, catalyst item, or search) — otherwise the user
      // taps a hex and sees nothing change.
      if (isMobileLayout() && !document.body.classList.contains('drawer-right-open')) {
        openMobilePanel('right');
      }
      if (map && map.getLayer('h3-hex-selected')) {
        map.setFilter('h3-hex-selected', ['==', ['get', 'h3_index'], props.h3_index]);
          if (map.getLayer('h3-hex-selected-fill')) map.setFilter('h3-hex-selected-fill', ['==', ['get', 'h3_index'], props.h3_index]);
      }

      const container = document.getElementById('inspector-content');
      if (!container) return;

      const baselineOnly = props.__baseline === true;
      const limsRaw = Number(props.lims_score);
      const limsKnown = props.lims_score != null && Number.isFinite(limsRaw);
      const lims = limsKnown ? limsRaw : 0;
      const isCatalyst = !baselineOnly && limsKnown && lims >= 84.0;
      // Absent model outputs render as '—', never as a plausible-looking default.
      const deltaCell = (v) => `<span class="${deltaClass(v)}">${formatSignedPct(v)}</span>`;
      const macroProb = formatProbability(props.prob_18m_macro_outperformance);

      const latRaw = Number(props.centroid_lat);
      const lngRaw = Number(props.centroid_lng);
      const hasCoords = props.centroid_lat != null && props.centroid_lng != null
        && Number.isFinite(latRaw) && Number.isFinite(lngRaw);
      const lat = hasCoords ? latRaw : NaN;
      const lng = hasCoords ? lngRaw : NaN;
      const subInfo = hasCoords ? getSubmarketInfoByCoords(lat, lng) : null;
      const submarketName = props.submarket || (subInfo ? subInfo.name : 'Selected cell');
      const rawBorough = props.borough || (subInfo ? subInfo.meta.borough : (hasCoords ? getBoroughNameByCoords(lat, lng) : ''));
      const boroughName = divisionLabel(rawBorough);
      const description = props.description || (subInfo ? subInfo.meta.description : '');
      const bClass = getBoroughClass(rawBorough);
      const numOr = (v, fmt) => (v != null && v !== '' && Number.isFinite(Number(v)) ? fmt(Number(v)) : '—');

      let shapObj = props.shap_attributions;
      if (typeof shapObj === 'string') {
        try { shapObj = JSON.parse(shapObj); } catch(e) { shapObj = null; }
      }

      const esc = escapeHtml;
      container.innerHTML = `
        <div class="inspector-content">
          <div class="parcel-header">
            <div class="parcel-title-row">
              <div class="parcel-name">${esc(submarketName)}</div>
              ${boroughName ? `<span class="borough-tag ${esc(bClass)}">${esc(boroughName)}</span>` : ''}
            </div>
            <div class="parcel-meta-sub">
              ${props.city_name ? `<span>${esc(props.city_name)}</span><span>•</span>` : ''}
              ${hasCoords ? `<span>${lat.toFixed(4)}, ${lng.toFixed(4)}</span><span>•</span>` : ''}
              <span>H3 ${esc(props.h3_index || '—')}</span>
            </div>
            ${description ? `<div class="parcel-description">${esc(description)}</div>` : ''}
          </div>

          <div class="score-hero-block">
            <div class="score-hero-left">
              <span class="score-hero-label">${baselineOnly ? 'Registry Baseline Momentum' : 'LIMS Momentum Score'}</span>
              <span class="score-status-pill ${baselineOnly ? 'baseline' : isCatalyst ? 'catalyst' : ''}">
                ${baselineOnly ? '○ Baseline — no model snapshot' : isCatalyst ? '● Catalyst' : '● Active signal'}
              </span>
            </div>
            <div class="score-hero-val ${baselineOnly ? 'baseline' : isCatalyst ? 'catalyst' : ''}">
              ${limsKnown ? lims.toFixed(1) : '—'}
            </div>
          </div>
          ${
            baselineOnly
              ? `
          <div>
            <div class="forecast-section-title">Multi-Horizon Projections</div>
            <div class="shap-empty">No precomputed model snapshot covers this cell yet. Fly to a rendered hexagon (or open a catalyst alert) for the full 6/12/18-month forecast with SHAP attribution.</div>
          </div>

          <div>
            <div class="forecast-section-title">Registry Baseline Telemetry</div>
            <table class="telemetry-table">
              <tr>
                <td class="lbl">CapEx Density (Decayed)</td>
                <td class="val">${Number.isFinite(Number(props.capex_density_decayed)) ? '$' + Number(props.capex_density_decayed).toLocaleString() + '/km²' : '—'}</td>
              </tr>
              <tr>
                <td class="lbl">Permit Velocity</td>
                <td class="val">${Number.isFinite(Number(props.permit_velocity)) ? (Number(props.permit_velocity) * 100).toFixed(1) + '%' : '—'}</td>
              </tr>
              <tr>
                <td class="lbl">311 Shift Ratio (QoL/Neglect)</td>
                <td class="val">${Number.isFinite(Number(props.shift_ratio_311)) ? Number(props.shift_ratio_311).toFixed(2) + 'x' : '—'}</td>
              </tr>
              <tr>
                <td class="lbl">SLA Filings (90d)</td>
                <td class="val">${Number.isFinite(Number(props.sla_new_filings_90d)) ? props.sla_new_filings_90d + ' filings' : '—'}</td>
              </tr>
            </table>
          </div>`
              : `
          <div>
            <div class="forecast-section-title">Multi-Horizon Projections</div>
            <div class="quantiles-card">
              <div class="quantiles-header">
                <span>6-Month Forecast Quantiles</span>
                <span class="quantiles-model">LightGBM</span>
              </div>
              <div class="quantiles-spread-row">
                <div class="q-box">
                  <span class="q-lbl">Bearish (p10)</span>
                  <span class="q-num">${formatSignedPct(props.delta_6m_p10)}</span>
                </div>
                <div class="q-box expected">
                  <span class="q-lbl">Expected (p50)</span>
                  <span class="q-num">${deltaCell(props.delta_6m_p50)}</span>
                </div>
                <div class="q-box">
                  <span class="q-lbl">Bullish (p90)</span>
                  <span class="q-num">${formatSignedPct(props.delta_6m_p90)}</span>
                </div>
              </div>
            </div>

            <div class="horizon-pairs">
              <div class="horizon-mini-card">
                <div class="horizon-mini-lbl">12M Spatial Spillover</div>
                <div class="horizon-mini-val">${deltaCell(props.delta_12m_spillover)}</div>
              </div>
              <div class="horizon-mini-card">
                <div class="horizon-mini-lbl">18M Outperformance Probability</div>
                <div class="horizon-mini-val">${macroProb}</div>
              </div>
            </div>
          </div>

          <div>
            <div class="forecast-section-title">SHAP Feature Attribution</div>
            <div class="chart-block">
              <canvas id="shap-chart"></canvas>
            </div>
          </div>

          ${leadingIndicatorsHtml(props, numOr)}`
          }${contextInspectorHtml(props)}
        </div>
      `;

      renderShapChart(shapObj);
    }

    // Leading indicators the snapshot actually carries for this cell; rows
    // with no value are left out rather than padded with defaults.
    function leadingIndicatorsHtml(props, numOr) {
      const rows = [
        ['CapEx Density (Decayed)', props.capex_density_decayed, numOr(props.capex_density_decayed, (n) => '$' + Math.round(n).toLocaleString() + '/km²')],
        ['Permit Velocity', props.permit_velocity, formatSignedPct(props.permit_velocity)],
        ['311 Shift Ratio (QoL/Neglect)', props.shift_ratio_311, numOr(props.shift_ratio_311, (n) => n.toFixed(2) + 'x')],
        ['Liquor License Filings (90d)', props.sla_new_filings_90d, numOr(props.sla_new_filings_90d, (n) => Math.round(n) + ' filings')],
      ].filter(([, raw, shown]) => raw != null && shown !== '—');
      const body = rows.length
        ? `<table class="telemetry-table">${rows.map(([lbl, , shown]) => `
              <tr>
                <td class="lbl">${escapeHtml(lbl)}</td>
                <td class="val">${escapeHtml(shown)}</td>
              </tr>`).join('')}
            </table>`
        : '<div class="shap-empty">No leading indicators published for this cell.</div>';
      return `
          <div>
            <div class="forecast-section-title">Leading Telemetry Indicators</div>
            ${body}
          </div>`;
    }

    // Every Bay Area context value the selected cell carries, with sources.
    function contextInspectorHtml(props) {
      const rows = Object.entries(CONTEXT_METRICS).filter(([key]) => props[key] != null);
      if (rows.length === 0) return '';
      const sources = [...new Set(rows.map(([, m]) => m.attribution).filter(Boolean))];
      return `
          <div>
            <div class="forecast-section-title">Bay Area Context</div>
            <table class="telemetry-table">
              ${rows.map(([key, m]) => `
              <tr>
                <td class="lbl">${escapeHtml(m.label)}</td>
                <td class="val">${escapeHtml(formatContextValue(key, props[key]))}</td>
              </tr>`).join('')}
            </table>
            <div class="legend-attribution context-sources">${sources.map((s) => escapeHtml(s)).join('<br>')}</div>
          </div>`;
    }

    // Canvas text can't read CSS variables, so resolve the tokens once; the
    // font stacks carry fallbacks so a slow web font never drops to serif.
    const ROOT_STYLE = getComputedStyle(document.documentElement);
    const CHART_TEXT_MUTED = ROOT_STYLE.getPropertyValue('--text-muted').trim() || '#8190a6';
    const CHART_TEXT_SECONDARY = ROOT_STYLE.getPropertyValue('--text-secondary').trim() || '#a7b5c9';
    const CHART_FONT_MONO = ROOT_STYLE.getPropertyValue('--font-mono').trim() || 'monospace';
    const CHART_FONT_SANS = ROOT_STYLE.getPropertyValue('--font-sans').trim() || 'sans-serif';

    function renderShapChart(shap) {
      const ctx = document.getElementById('shap-chart');
      if (!ctx) return;

      if (shapChart) {
        shapChart.destroy();
        shapChart = null;
      }

      const hasData = shap && typeof shap === 'object' && Object.keys(shap).length > 0;
      if (!hasData) {
        const block = ctx.closest('.chart-block');
        if (block) block.innerHTML = '<div class="shap-empty">No SHAP attribution published for this cell.</div>';
        return;
      }
      const data = shap;

      const labels = Object.keys(data).map(k => k.replace(/_/g, ' '));
      const values = Object.values(data);
      const bgColors = values.map(v => v >= 0 ? 'rgba(52, 211, 153, 0.75)' : 'rgba(244, 63, 94, 0.75)');

      shapChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: bgColors,
            borderRadius: 3,
            borderSkipped: false
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: REDUCED_MOTION ? 0 : 200 },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` Impact: ${ctx.raw >= 0 ? '+' : ''}${(ctx.raw * 100).toFixed(2)}%`
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.04)' },
              ticks: {
                color: CHART_TEXT_MUTED,
                font: { family: CHART_FONT_MONO, size: 11 },
                callback: (v) => `${(v * 100).toFixed(1)}%`
              }
            },
            y: {
              grid: { display: false },
              ticks: {
                color: CHART_TEXT_SECONDARY,
                font: { family: CHART_FONT_SANS, size: 11 },
                // Narrow panels (tablet overlay) can't fit the longest feature
                // names; shorten them there. The tooltip keeps the full name.
                callback: function (value) {
                  const label = String(this.getLabelForValue(value));
                  const max = this.chart.width < 320 ? 18 : 28;
                  return label.length > max ? label.slice(0, max - 1) + '…' : label;
                }
              }
            }
          }
        }
      });
    }

    async function searchCoordinateOrHex(input) {
      let lat, lng, h3Index;
      const hasH3 = typeof h3 !== 'undefined';

      if (input.includes(',')) {
        const parts = input.split(',').map(s => parseFloat(s.trim()));
        lat = parts[0];
        lng = parts[1];
        if (hasH3) h3Index = h3.latLngToCell(lat, lng, 9);
      } else if (hasH3 && h3.isValidCell && h3.isValidCell(input)) {
        h3Index = input;
        const coords = h3.cellToLatLng(h3Index);
        lat = coords[0];
        lng = coords[1];
      } else if (input.startsWith('8')) {
        h3Index = input;
        if (hasH3) {
          try {
            const coords = h3.cellToLatLng(h3Index);
            lat = coords[0];
            lng = coords[1];
          } catch(e) {}
        }
      }

      if (lat && lng) {
        if (map) {
          map.flyTo({
            center: [lng, lat],
            zoom: FOCUS_ZOOM,
            pitch: currentPerspective === '3D' ? FOCUS_PITCH : 0,
            bearing: -15,
            duration: REDUCED_MOTION ? 0 : 1100
          });
        }

        const subInfo = getSubmarketInfoByCoords(lat, lng);
        const submarketName = subInfo ? subInfo.name : 'Searched Coordinate';
        const boroughName = normalizeBorough(subInfo ? subInfo.meta.borough : getBoroughNameByCoords(lat, lng));

        let predData = null;
        try {
          const resp = await fetch('/api/v1/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              latitude: lat,
              longitude: lng,
              h3_index: h3Index,
              include_shap: true
            })
          });
          if (resp.ok) predData = await resp.json();
        } catch (e) {}

        if (!predData) {
          predData = {
            h3_index: h3Index || 'custom_hex',
            lims_score: subInfo ? subInfo.meta.base_lims : undefined,
            capex_density_decayed: subInfo ? subInfo.meta.capex : undefined,
            permit_velocity: subInfo ? subInfo.meta.permit_vel : undefined,
            shift_ratio_311: subInfo ? subInfo.meta.shift_ratio : undefined,
            sla_new_filings_90d: subInfo ? subInfo.meta.sla : undefined,
            __baseline: true
          };
        }

        predData.submarket = submarketName;
        predData.borough = boroughName;
        predData.description = subInfo ? subInfo.meta.description : 'Searched coordinate parcel';
        predData.centroid_lat = lat;
        predData.centroid_lng = lng;
        handleHexSelection(predData);
      }
    }

    function getSubmarketInfoByCoords(lat, lng) {
      if (!lat || !lng) return null;
      let closestName = null;
      let closestMeta = null;
      let minDst = Infinity;
      for (const [name, meta] of Object.entries(SUBMARKETS)) {
        const d = Math.hypot(lat - meta.lat, lng - meta.lng);
        if (d < minDst) {
          minDst = d;
          closestName = name;
          closestMeta = meta;
        }
      }
      return minDst < 0.05 ? { name: closestName, meta: closestMeta } : null;
    }

    function resolveDivisionByNearestSubmarket(lat, lng) {
      // Mirrors server-side get_division_for_coordinate: snap to the nearest
      // submarket within 25 km and return its division. Falls back to null so
      // the static bbox chains below apply.
      const subs = SUBMARKETS || {};
      const keys = Object.keys(subs);
      if (!keys.length) return null;
      let bestName = null, bestMeta = null, bestDist = Infinity;
      for (const k of keys) {
        const m = subs[k] || {};
        if (typeof m.lat !== 'number' || typeof m.lng !== 'number') continue;
        const d = haversineDistance(lat, lng, m.lat, m.lng);
        if (d < bestDist) { bestDist = d; bestName = k; bestMeta = m; }
      }
      if (bestMeta && bestDist <= 25.0) return bestMeta.borough;
      return null;
    }

    function getBoroughNameByCoords(lat, lng) {
      if (!lat || !lng) return '';
      // Server grid properties carry borough; this fallback snaps to the
      // nearest submarket (any metro) within 25 km, else reports unknown.
      return resolveDivisionByNearestSubmarket(lat, lng) || '';
    }
  </script>
  <script>
    // WebMCP (feature-detected): expose read-only site tools to AI agents via
    // the browser. Tools mirror the edge data API (/api/v1/*) — no auth needed.
    (function () {
      var modelContext = navigator.modelContext;
      if (!modelContext || typeof modelContext.registerTool !== 'function') return;
      async function callApi(path, init) {
        var res = await fetch(path, init);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return JSON.stringify(await res.json());
      }
      try {
        modelContext.registerTool({
          name: 'urban_signal_list_cities',
          description: 'List the metropolitan regions available on the Urban Signal dashboard.',
          inputSchema: { type: 'object', properties: {}, additionalProperties: false },
          execute: async function () {
            return callApi('/api/v1/cities');
          }
        });
        modelContext.registerTool({
          name: 'urban_signal_get_catalysts',
          description: 'Get the strongest commercial catalyst cells (H3 index + LIMS score) for one metro.',
          inputSchema: {
            type: 'object',
            properties: {
              city_id: { type: 'string', description: 'Metro id from urban_signal_list_cities.' },
              limit: { type: 'integer', minimum: 1, maximum: 500, description: 'Max cells to return.' }
            },
            required: ['city_id'],
            additionalProperties: false
          },
          execute: async function (args) {
            var params = new URLSearchParams({ city_id: String(args.city_id), limit: String(args.limit || 25) });
            return callApi('/api/v1/catalysts?' + params.toString());
          }
        });
        modelContext.registerTool({
          name: 'urban_signal_predict_cell',
          description: 'Look up the precomputed catalyst forecast for one resolution-9 H3 cell.',
          inputSchema: {
            type: 'object',
            properties: {
              h3_index: { type: 'string', description: 'Resolution-9 H3 cell index.' },
              include_shap: { type: 'boolean', description: 'Include SHAP attributions (default true).' }
            },
            required: ['h3_index'],
            additionalProperties: false
          },
          execute: async function (args) {
            return callApi('/api/v1/predict', {
              method: 'POST',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ h3_index: String(args.h3_index), include_shap: args.include_shap !== false })
            });
          }
        });
      } catch (err) {
        console.debug('WebMCP registration skipped:', err);
      }
    })();
  </script>
</body>
</html>
"""
    return html.replace("__FAVICON_LINK__", favicon_link).replace("__METRO_META__", _metro_meta_js())
