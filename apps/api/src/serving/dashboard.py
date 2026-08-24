"""Interactive Geospatial Web Visualization Dashboard HTML/JS/CSS generator for Urban Signal."""

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

def get_dashboard_html() -> str:
    favicon_link = (
        f'  <link rel="icon" type="image/svg+xml" href="{_favicon_data_uri()}">'
    )
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Urban Signal — Real-Time Geospatial Intelligence & Commercial Catalyst Forecasting Engine">
  <title>Urban Signal — Real-Time Geospatial Intelligence & Catalyst Forecaster</title>
  __FAVICON_LINK__
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  
  <!-- MapLibre GL JS -->
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" />
  <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
  
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  
  <!-- H3 JS -->
  <script src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js"></script>

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
      
      --text-main: #f8fafc;
      --text-secondary: #a7b5c9;
      --text-muted: #718198;
      
      --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'IBM Plex Mono', monospace;
      
      --glass-blur: blur(12px);
      --radius-sm: 5px;
      --radius-md: 7px;
      --radius-lg: 10px;
      --shadow-dropdown: 0 18px 42px rgba(0, 0, 0, 0.48), 0 4px 12px rgba(0, 0, 0, 0.28);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
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
      background: rgba(30, 20, 28, 0.95);
      color: #fecdd3;
    }

    .toast-banner.warning {
      border-color: var(--accent-warning);
      background: rgba(30, 26, 18, 0.95);
      color: #fef08a;
    }

    .toast-banner.success {
      border-color: var(--accent-success);
      background: rgba(18, 30, 24, 0.95);
      color: #a7f3d0;
    }

    .toast-btn {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
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
      background: rgba(255, 255, 255, 0.2);
    }

    @keyframes toastIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
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
      background: rgba(255, 255, 255, 0.14);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.28);
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
      font-size: 13px;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
    }

    .brand-badge {
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 500;
      padding: 1px 6px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-secondary);
      border-radius: 4px;
    }
    .city-selector-wrapper {
      display: flex;
      align-items: center;
      margin-left: 3px;
    }

    .city-select-dropdown {
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 28px 6px 10px;
      border-radius: var(--radius-sm);
      outline: none;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .city-select-dropdown:hover, .city-select-dropdown:focus {
      border-color: var(--accent-primary);
    }

    .compare-control {
      position: relative;
      display: flex;
      align-items: center;
      margin-left: -3px;
    }

    .compare-toggle {
      background: var(--accent-primary-dim);
      border: 1px solid var(--border-active);
      color: var(--accent-primary);
      font-size: 11px;
      font-weight: 600;
      padding: 6px 10px;
      border-radius: var(--radius-sm);
      cursor: pointer;
    }

    .compare-toggle:hover, .compare-toggle.active {
      color: var(--text-main);
      border-color: var(--accent-primary);
      background: var(--accent-primary-dim);
    }

    .compare-menu {
      position: absolute;
      top: 34px;
      left: 0;
      z-index: 200;
      width: 246px;
      padding: 13px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-active);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-dropdown);
    }

    .compare-menu[hidden] { display: none; }
    .compare-menu-title { margin: 0 2px 7px; color: var(--text-main); font-family: var(--font-mono); font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
    .compare-menu label { display: flex; gap: 9px; align-items: center; padding: 8px 7px; border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 11px; cursor: pointer; transition: background .15s ease, color .15s ease; }
    .compare-menu label:hover { color: var(--text-main); background: rgba(255, 255, 255, .05); }
    .compare-menu input { width: 14px; height: 14px; accent-color: var(--accent-primary); }
    .compare-apply { width: 100%; margin-top: 10px; padding: 8px; border: 0; border-radius: var(--radius-sm); background: var(--accent-primary); color: var(--bg-base); font-size: 11px; font-weight: 700; cursor: pointer; transition: filter .15s ease, transform .15s ease; }
    .compare-apply:hover { filter: brightness(1.08); }
    .compare-apply:active { transform: translateY(1px); }

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
      background: rgba(255, 255, 255, 0.04);
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
    .borough-btn.active.SouthwestSide { color: #38bdf8; }
    .borough-btn.active.SanFranciscoCore, .borough-btn.active.SAN_FRANCISCO_CORE, .borough-btn.active.SFCore { color: var(--division-sf-core); }
    .borough-btn.active.EastBay, .borough-btn.active.EAST_BAY { color: var(--division-east-bay); }
    .borough-btn.active.Peninsula, .borough-btn.active.PENINSULA { color: var(--division-peninsula); }
    .borough-btn.active.SiliconValleySouthBay, .borough-btn.active.SILICON_VALLEY_SOUTH_BAY, .borough-btn.active.SiliconValley { color: var(--division-silicon-valley); }
    .borough-btn.active.MarinNorthBay, .borough-btn.active.MARIN_NORTH_BAY, .borough-btn.active.Marin { color: var(--division-marin); }
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
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      transition: background 0.1s ease;
    }

    .search-result-item:last-child {
      border-bottom: none;
    }

    .search-result-item:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-main);
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
      border: 1px solid rgba(52, 211, 153, .24);
      border-radius: var(--radius-sm);
      white-space: nowrap;
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

    /* Main Map Viewport */
    .map-container {
      flex: 1;
      position: relative;
      background: var(--bg-base);
      overflow: hidden;
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
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--accent-danger);
      background: var(--accent-danger-dim);
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
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 11px 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .catalyst-item:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.15);
    }

    .catalyst-item.selected {
      background: var(--accent-primary-dim);
      border-color: var(--accent-primary);
    }

    .catalyst-item-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .catalyst-name {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-main);
    }

    .catalyst-lims-tag {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      color: var(--accent-danger);
    }

    .catalyst-item-bottom {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-secondary);
    }

    .borough-tag {
      font-size: 10px;
      font-weight: 500;
      padding: 1px 5px;
      border-radius: 3px;
      background: rgba(255, 255, 255, 0.04);
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
    .borough-tag.SouthwestSide { color: #38bdf8; }
    .borough-tag.SanFranciscoCore, .borough-tag.SAN_FRANCISCO_CORE, .borough-tag.SFCore { color: var(--division-sf-core); }
    .borough-tag.EastBay, .borough-tag.EAST_BAY { color: var(--division-east-bay); }
    .borough-tag.Peninsula, .borough-tag.PENINSULA { color: var(--division-peninsula); }
    .borough-tag.SiliconValleySouthBay, .borough-tag.SILICON_VALLEY_SOUTH_BAY, .borough-tag.SiliconValley { color: var(--division-silicon-valley); }
    .borough-tag.MarinNorthBay, .borough-tag.MARIN_NORTH_BAY, .borough-tag.Marin { color: var(--division-marin); }
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
      color: var(--accent-success);
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
      width: 32px;
      height: 32px;
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
      border-color: rgba(255, 255, 255, 0.15);
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
      background: linear-gradient(to right, #34d399, #fbbf24, #fb923c, #f43f5e);
      margin-bottom: 4px;
    }

    .legend-range-labels {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      font-family: var(--font-mono);
      color: var(--text-muted);
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
      background: rgba(255, 255, 255, 0.03);
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
      font-size: 13px;
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
      font-size: 15px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }

    .parcel-meta-sub {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      margin-bottom: 6px;
    }

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
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .score-hero-val {
      font-size: 28px;
      font-weight: 700;
      font-family: var(--font-mono);
    }

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
      font-size: 10px;
      color: var(--text-muted);
    }

    .q-num {
      font-size: 12px;
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-secondary);
    }

    .q-box.expected .q-num {
      font-size: 14px;
      color: var(--accent-success);
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
      font-size: 15px;
      font-weight: 600;
      font-family: var(--font-mono);
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
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
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

    @media (max-width: 1024px) {
      .sidebar-left { width: 260px; }
      .sidebar-right { width: 300px; }
      .search-wrapper { width: 160px; }
    }
  </style>
</head>
<body>

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
        <span class="sr-only" style="display:none;">Geospatial Intelligence Dashboard</span>
        <span class="brand-badge">v2.0</span>
      </div>
      <!-- Multi-City Selector -->
      <div class="city-selector-wrapper">
        <select id="city-select" class="city-select-dropdown" aria-label="Select Metropolitan Region" onchange="changeCity(this.value)">
          <option value="san_francisco" selected>🌉 San Francisco Bay Area (5 Divisions)</option>
          <option value="nyc">🗽 NYC (5 Boroughs)</option>
          <option value="chicago">🏙️ Chicago (6 Divisions)</option>
          <option value="seattle">🌲 Seattle Metro (4 Divisions)</option>
          <option value="los_angeles">🌴 Los Angeles Metro (6 Divisions)</option>
          <option value="new_orleans">🎺 New Orleans Metro (9 Divisions)</option>
          <option value="norfolk">⚓ Norfolk (5 Divisions)</option>
          <option value="detroit">🏙️ Detroit (6 Divisions)</option>
          <option value="austin">🦇 Austin (6 Divisions)</option>
          <option value="cincinnati">🏛️ Cincinnati (1 Division)</option>
          <option value="boston">🦄 Boston (4 Divisions)</option>
          <option value="baltimore">🦀 Baltimore (1 Division)</option>
          <option value="montgomery">🦌 Montgomery County (1 Division)</option>
          <option value="baton_rouge">🌶️ Baton Rouge (1 Division)</option>
          <option value="denver">🏔️ Denver (1 Division)</option>
          <option value="philadelphia">🔔 Philadelphia (8 Divisions)</option>
          <option value="washington_dc">🏛️ Washington DC (8 Divisions)</option>
        </select>
      </div>
      <div class="compare-control">
        <button id="compare-toggle" class="compare-toggle" type="button" onclick="toggleCompareMenu()" aria-expanded="false">+ Compare</button>
        <div id="compare-menu" class="compare-menu" hidden>
          <div class="compare-menu-title">Compare regions</div>
          <div id="compare-options"></div>
          <button class="compare-apply" type="button" onclick="applyComparison()">Show selected regions</button>
        </div>
      </div>
    </div>

    <!-- Borough / Division Navigation Selector -->
    <nav class="borough-nav" id="borough-tabs" role="navigation" aria-label="Division Filters">
      <button class="borough-btn active" data-borough="ALL" onclick="selectBoroughFilter('ALL')">All NYC</button>
      <button class="borough-btn Manhattan" data-borough="Manhattan" onclick="selectBoroughFilter('Manhattan')">Manhattan</button>
      <button class="borough-btn Brooklyn" data-borough="Brooklyn" onclick="selectBoroughFilter('Brooklyn')">Brooklyn</button>
      <button class="borough-btn Queens" data-borough="Queens" onclick="selectBoroughFilter('Queens')">Queens</button>
      <button class="borough-btn Bronx" data-borough="Bronx" onclick="selectBoroughFilter('Bronx')">Bronx</button>
      <button class="borough-btn StatenIsland" data-borough="Staten Island" onclick="selectBoroughFilter('Staten Island')">Staten Island</button>
    </nav>

    <!-- Header Actions & Search -->
    <div class="header-actions">
      <!-- Search & Jump -->
      <div class="search-wrapper" role="search">
        <div class="search-input-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" id="global-search-input" placeholder="Search submarket, coords, H3..." autocomplete="off" aria-label="Search submarket or coordinate" oninput="onGlobalSearch(this.value)" onkeydown="if(event.key==='Enter') executeSearch()">
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

    <!-- Left Sidebar: Layer Controls & Active Catalysts -->
    <aside class="sidebar-left">
      <!-- Map Controls Panel -->
      <div class="panel-section">
        <div class="panel-header-row">
          <span class="section-title">Projection & Metric</span>
        </div>
        <div class="control-row">
          <div class="view-toggle">
            <button id="btn-3d" class="active" onclick="setPerspective('3D')">3D</button>
            <button id="btn-2d" onclick="setPerspective('2D')">2D</button>
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
      <div class="catalyst-feed-section" title="Real-Time Catalyst Alerts">
        <div class="panel-header-row">
          <span class="section-title">Catalyst Clusters (Real-Time Catalyst Alerts)</span>
          <span class="feed-count-badge" id="stat-active-catalysts">29 Active</span>
        </div>
        <div class="catalyst-list-scroll" id="catalyst-feed-list">
          <!-- Populated dynamically via JS -->
        </div>
      </div>
    </aside>

    <!-- Center Map Viewport -->
    <main class="map-container">
      <div id="map"></div>

      <!-- Floating Quick Tools -->
      <div class="map-controls-group">
        <button class="map-tool-btn" title="Toggle 3D/2D View" onclick="togglePerspective()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 17 22 12"></polyline></svg>
        </button>
        <button class="map-tool-btn" title="Reset View (All NYC)" onclick="selectBoroughFilter('ALL')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
        </button>
      </div>

      <!-- Sleek Map Legend -->
      <div class="map-legend-card">
        <div class="legend-header">
          <span id="legend-metric-title">LIMS Momentum Score</span>
        </div>
        <div class="legend-bar"></div>
        <div class="legend-range-labels">
          <span id="legend-min">0.0</span>
          <span id="legend-mid">70.0</span>
          <span id="legend-max">100.0</span>
        </div>
      </div>
    </main>

    <!-- Right Sidebar: Parcel & Submarket Inspector -->
    <aside class="sidebar-right" id="inspector-panel">
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

    const CITY_CONFIGS = {
      nyc: {
        center: [-73.965, 40.7128],
        zoom: 11.2,
        pitch: 48,
        bearing: -12,
        name: 'New York City',
        allLabel: 'All NYC',
        divisions: [
          { key: 'ALL', label: 'All NYC', class: 'ALL' },
          { key: 'Manhattan', label: 'Manhattan', class: 'Manhattan' },
          { key: 'Brooklyn', label: 'Brooklyn', class: 'Brooklyn' },
          { key: 'Queens', label: 'Queens', class: 'Queens' },
          { key: 'Bronx', label: 'Bronx', class: 'Bronx' },
          { key: 'Staten Island', label: 'Staten Island', class: 'StatenIsland' }
        ],
        presets: {
          'ALL': { lat: 40.7128, lng: -73.9650, zoom: 10.8, pitch: 45, bearing: -12 },
          'Manhattan': { lat: 40.7580, lng: -73.9855, zoom: 12.8, pitch: 52, bearing: -15 },
          'Brooklyn': { lat: 40.6782, lng: -73.9442, zoom: 12.4, pitch: 48, bearing: -10 },
          'Queens': { lat: 40.7282, lng: -73.8448, zoom: 12.0, pitch: 45, bearing: -10 },
          'Bronx': { lat: 40.8448, lng: -73.8648, zoom: 12.5, pitch: 48, bearing: -10 },
          'Staten Island': { lat: 40.5795, lng: -74.1502, zoom: 12.2, pitch: 45, bearing: -10 }
        }
      },
      chicago: {
        center: [-87.6298, 41.8781],
        zoom: 11.0,
        pitch: 48,
        bearing: -10,
        name: 'Chicago',
        allLabel: 'All Chicago',
        divisions: [
          { key: 'ALL', label: 'All Chicago', class: 'ALL' },
          { key: 'Central / Downtown', label: 'Central / Loop', class: 'CentralDowntown' },
          { key: 'North Side', label: 'North Side', class: 'NorthSide' },
          { key: 'Northwest Side', label: 'Northwest Side', class: 'NorthwestSide' },
          { key: 'South Side', label: 'South Side', class: 'SouthSide' },
          { key: 'Far North Side', label: 'Far North', class: 'FarNorthSide' },
          { key: 'Southwest Side', label: 'Southwest', class: 'SouthwestSide' }
        ],
        presets: {
          'ALL': { lat: 41.8781, lng: -87.6298, zoom: 10.6, pitch: 45, bearing: -10 },
          'Central / Downtown': { lat: 41.8827, lng: -87.6360, zoom: 13.0, pitch: 52, bearing: -12 },
          'North Side': { lat: 41.9350, lng: -87.6550, zoom: 12.6, pitch: 48, bearing: -10 },
          'Northwest Side': { lat: 41.9200, lng: -87.7000, zoom: 12.5, pitch: 48, bearing: -10 },
          'South Side': { lat: 41.8200, lng: -87.6300, zoom: 12.2, pitch: 45, bearing: -10 },
          'Far North Side': { lat: 41.9800, lng: -87.6650, zoom: 12.2, pitch: 45, bearing: -10 },
          'Southwest Side': { lat: 41.8350, lng: -87.7000, zoom: 12.2, pitch: 45, bearing: -10 }
        }
      },
      san_francisco: {
        center: [-122.4194, 37.7749],
        zoom: 11.8,
        pitch: 50.0,
        bearing: -10,
        name: 'San Francisco Bay Area',
        allLabel: 'All Bay Area',
        divisions: [
          { key: 'ALL', label: 'All Bay Area', class: 'ALL' },
          { key: 'SAN_FRANCISCO_CORE', label: 'SF Core', class: 'SanFranciscoCore' },
          { key: 'EAST_BAY', label: 'East Bay', class: 'EastBay' },
          { key: 'PENINSULA', label: 'Peninsula', class: 'Peninsula' },
          { key: 'SILICON_VALLEY_SOUTH_BAY', label: 'Silicon Valley', class: 'SiliconValleySouthBay' },
          { key: 'MARIN_NORTH_BAY', label: 'Marin / North Bay', class: 'MarinNorthBay' }
        ],
        presets: {
          'ALL': { lat: 37.7749, lng: -122.4194, zoom: 11.0, pitch: 48, bearing: -10 },
          'SAN_FRANCISCO_CORE': { lat: 37.7749, lng: -122.4194, zoom: 12.8, pitch: 52, bearing: -12 },
          'EAST_BAY': { lat: 37.8044, lng: -122.2712, zoom: 12.5, pitch: 48, bearing: -10 },
          'PENINSULA': { lat: 37.5630, lng: -122.3255, zoom: 12.2, pitch: 48, bearing: -10 },
          'SILICON_VALLEY_SOUTH_BAY': { lat: 37.3382, lng: -121.8863, zoom: 12.2, pitch: 45, bearing: -10 },
          'MARIN_NORTH_BAY': { lat: 37.9735, lng: -122.5311, zoom: 12.0, pitch: 45, bearing: -10 },
          'San Francisco Core': { lat: 37.7749, lng: -122.4194, zoom: 12.8, pitch: 52, bearing: -12 },
          'East Bay': { lat: 37.8044, lng: -122.2712, zoom: 12.5, pitch: 48, bearing: -10 },
          'Peninsula': { lat: 37.5630, lng: -122.3255, zoom: 12.2, pitch: 48, bearing: -10 },
          'Silicon Valley / South Bay': { lat: 37.3382, lng: -121.8863, zoom: 12.2, pitch: 45, bearing: -10 },
          'Marin / North Bay': { lat: 37.9735, lng: -122.5311, zoom: 12.0, pitch: 45, bearing: -10 }
        }
      },
      seattle: {
        center: [-122.3321, 47.6062],
        zoom: 10.4,
        pitch: 48,
        bearing: -10,
        name: 'Seattle Metro',
        allLabel: 'All Seattle',
        divisions: [
          { key: 'ALL', label: 'All Seattle', class: 'ALL' },
          { key: 'SEATTLE_CORE', label: 'Seattle Core', class: 'SeattleCore' },
          { key: 'NORTH_KING', label: 'North King', class: 'NorthKing' },
          { key: 'EASTSIDE', label: 'Eastside', class: 'Eastside' },
          { key: 'SOUTH_KING', label: 'South King', class: 'SouthKing' }
        ],
        presets: {
          'ALL': { lat: 47.6062, lng: -122.3321, zoom: 10.0, pitch: 45, bearing: -10 },
          'SEATTLE_CORE': { lat: 47.6120, lng: -122.3300, zoom: 12.5, pitch: 52, bearing: -12 },
          'NORTH_KING': { lat: 47.6950, lng: -122.3530, zoom: 12.0, pitch: 48, bearing: -10 },
          'EASTSIDE': { lat: 47.6350, lng: -122.1350, zoom: 11.5, pitch: 45, bearing: -10 },
          'SOUTH_KING': { lat: 47.4400, lng: -122.2850, zoom: 11.5, pitch: 45, bearing: -10 }
        }
      },
      los_angeles: {
        center: [-118.2437, 34.0522],
        zoom: 10.2,
        pitch: 48,
        bearing: -10,
        name: 'Los Angeles Metro',
        allLabel: 'All LA',
        divisions: [
          { key: 'ALL', label: 'All LA', class: 'ALL' },
          { key: 'CENTRAL_LA', label: 'Central LA', class: 'CentralLA' },
          { key: 'WESTSIDE', label: 'Westside', class: 'Westside' },
          { key: 'SAN_FERNANDO_VALLEY', label: 'San Fernando Valley', class: 'SanFernandoValley' },
          { key: 'HARBOR_SOUTH_BAY', label: 'Harbor / South Bay', class: 'HarborSouthBay' },
          { key: 'SOUTH_LA', label: 'South LA', class: 'SouthLA' },
          { key: 'EASTSIDE_SGV', label: 'Eastside / SGV', class: 'EastsideSGV' }
        ],
        presets: {
          'ALL': { lat: 34.0522, lng: -118.2437, zoom: 10.0, pitch: 45, bearing: -10 },
          'CENTRAL_LA': { lat: 34.07, lng: -118.28, zoom: 12.5, pitch: 48, bearing: -10 },
          'WESTSIDE': { lat: 34.04, lng: -118.45, zoom: 12.0, pitch: 48, bearing: -10 },
          'SAN_FERNANDO_VALLEY': { lat: 34.19, lng: -118.44, zoom: 11.5, pitch: 45, bearing: -10 },
          'HARBOR_SOUTH_BAY': { lat: 33.81, lng: -118.29, zoom: 11.5, pitch: 45, bearing: -10 },
          'SOUTH_LA': { lat: 33.98, lng: -118.29, zoom: 12.0, pitch: 48, bearing: -10 },
          'EASTSIDE_SGV': { lat: 34.11, lng: -118.16, zoom: 11.5, pitch: 48, bearing: -10 }
        }
      },
      new_orleans: {
        center: [-90.0715, 29.9511],
        zoom: 10.4,
        pitch: 48,
        bearing: -10,
        name: 'New Orleans Metro',
        metroBbox: { min_lat: 29.82, max_lat: 30.16, min_lng: -90.30, max_lng: -89.62 },
        allLabel: 'All NOLA',
        divisions: [
          { key: 'ALL', label: 'All NOLA', class: 'ALL' },
          { key: 'CBD_FRENCH_QUARTER', label: 'CBD / French Quarter', class: 'CBDFrenchQuarter' },
          { key: 'BYWATER_MARIGNY', label: 'Bywater / Marigny', class: 'BywaterMarigny' },
          { key: 'UPTOWN_CARROLLTON', label: 'Uptown / Carrollton', class: 'UptownCarrollton' },
          { key: 'MID_CITY', label: 'Mid City', class: 'MidCity' },
          { key: 'LAKEVIEW_GENTILLY', label: 'Lakeview / Gentilly', class: 'LakeviewGentilly' },
          { key: 'NEW_ORLEANS_EAST', label: 'New Orleans East', class: 'NewOrleansEast' },
          { key: 'WEST_BANK_ALGIERS', label: 'West Bank / Algiers', class: 'WestBankAlgiers' },
          { key: 'JEFFERSON_METAIRIE_KENNER', label: 'Jefferson / Metairie / Kenner', class: 'JeffersonMetairieKenner' },
          { key: 'ST_BERNARD_CHALMETTE', label: 'St. Bernard / Chalmette', class: 'StBernardChalmette' }
        ],
        presets: {
          'ALL': { lat: 29.9511, lng: -90.0715, zoom: 10.2, pitch: 45, bearing: -10 },
          'CBD_FRENCH_QUARTER': { lat: 29.9580, lng: -90.0660, zoom: 13.4, pitch: 52, bearing: -12 },
          'BYWATER_MARIGNY': { lat: 29.9680, lng: -90.0280, zoom: 13.0, pitch: 50, bearing: -10 },
          'UPTOWN_CARROLLTON': { lat: 29.9380, lng: -90.1080, zoom: 12.8, pitch: 48, bearing: -10 },
          'MID_CITY': { lat: 29.9850, lng: -90.0950, zoom: 12.6, pitch: 48, bearing: -10 },
          'LAKEVIEW_GENTILLY': { lat: 30.0150, lng: -90.0800, zoom: 12.4, pitch: 45, bearing: -10 },
          'NEW_ORLEANS_EAST': { lat: 30.0250, lng: -89.9400, zoom: 11.8, pitch: 45, bearing: -10 },
          'WEST_BANK_ALGIERS': { lat: 29.9350, lng: -90.0300, zoom: 12.2, pitch: 45, bearing: -10 },
          'JEFFERSON_METAIRIE_KENNER': { lat: 29.9850, lng: -90.1800, zoom: 11.8, pitch: 45, bearing: -10 },
          'ST_BERNARD_CHALMETTE': { lat: 29.8850, lng: -89.9700, zoom: 11.8, pitch: 45, bearing: -10 }
        }
      },
      norfolk: {
        center: [-76.2859, 36.8508],
        zoom: 11.6,
        pitch: 48,
        bearing: -10,
        name: 'Norfolk',
        metroBbox: { min_lat: 36.83, max_lat: 37.04, min_lng: -76.35, max_lng: -76.17 },
        allLabel: 'All Norfolk',
        divisions: [
          { key: 'ALL', label: 'All Norfolk', class: 'ALL' },
          { key: 'DOWNTOWN_WATERFRONT', label: 'Downtown Waterfront', class: 'DowntownWaterfront' },
          { key: 'GHENT_WESTBURG', label: 'Ghent / Westburg', class: 'GhentWestburg' },
          { key: 'OCEAN_VIEW', label: 'Ocean View', class: 'OceanView' },
          { key: 'CENTRAL_MILITARY_CIRCLE', label: 'Central / Military Circle', class: 'CentralMilitaryCircle' },
          { key: 'SOUTH_NORFOLK_BERKLEY', label: 'South Norfolk / Berkley', class: 'SouthNorfolkBerkley' }
        ],
        presets: {
          'ALL': { lat: 36.8800, lng: -76.2859, zoom: 11.4, pitch: 45, bearing: -10 },
          'DOWNTOWN_WATERFRONT': { lat: 36.8560, lng: -76.2930, zoom: 13.6, pitch: 54, bearing: -12 },
          'GHENT_WESTBURG': { lat: 36.8660, lng: -76.3000, zoom: 13.2, pitch: 50, bearing: -10 },
          'OCEAN_VIEW': { lat: 36.9450, lng: -76.3100, zoom: 12.6, pitch: 45, bearing: -10 },
          'CENTRAL_MILITARY_CIRCLE': { lat: 36.8850, lng: -76.2400, zoom: 12.8, pitch: 48, bearing: -10 },
          'SOUTH_NORFOLK_BERKLEY': { lat: 36.8500, lng: -76.2650, zoom: 13.0, pitch: 48, bearing: -10 }
        }
      },
      detroit: {
        center: [-83.0458, 42.3314],
        zoom: 10.6,
        pitch: 48,
        bearing: -10,
        name: 'Detroit',
        metroBbox: { min_lat: 42.25, max_lat: 42.49, min_lng: -83.35, max_lng: -82.88 },
        allLabel: 'All Detroit',
        divisions: [
          { key: 'ALL', label: 'All Detroit', class: 'ALL' },
          { key: 'DOWNTOWN_MIDTOWN_CORKTOWN', label: 'Downtown / Midtown / Corktown', class: 'DowntownMidtownCorktown' },
          { key: 'EAST_SIDE_JEFFERSON', label: 'East Side / Jefferson', class: 'EastSideJefferson' },
          { key: 'WEST_SIDE_GRAND_RIVER', label: 'West Side / Grand River', class: 'WestSideGrandRiver' },
          { key: 'SOUTHWEST_MEXICANTOWN', label: 'Southwest / Mexicantown', class: 'SouthwestMexicantown' },
          { key: 'NORTH_END_HIGHLAND_PARK', label: 'North End / Highland Park', class: 'NorthEndHighlandPark' },
          { key: 'EAST_ENGLISH_VILLAGE_MORNINGSIDE', label: 'East English Village / Morningside', class: 'EastEnglishVillageMorningside' }
        ],
        presets: {
          'ALL': { lat: 42.3314, lng: -83.0458, zoom: 10.4, pitch: 45, bearing: -10 },
          'DOWNTOWN_MIDTOWN_CORKTOWN': { lat: 42.3310, lng: -83.0600, zoom: 13.2, pitch: 52, bearing: -12 },
          'EAST_SIDE_JEFFERSON': { lat: 42.3450, lng: -82.9850, zoom: 12.6, pitch: 48, bearing: -10 },
          'WEST_SIDE_GRAND_RIVER': { lat: 42.3950, lng: -83.2100, zoom: 12.4, pitch: 45, bearing: -10 },
          'SOUTHWEST_MEXICANTOWN': { lat: 42.3150, lng: -83.1100, zoom: 12.8, pitch: 48, bearing: -10 },
          'NORTH_END_HIGHLAND_PARK': { lat: 42.3950, lng: -83.0900, zoom: 12.8, pitch: 48, bearing: -10 },
          'EAST_ENGLISH_VILLAGE_MORNINGSIDE': { lat: 42.3700, lng: -82.9550, zoom: 12.8, pitch: 48, bearing: -10 }
        }
      },
      austin: {
        center: [-97.7431, 30.2672],
        zoom: 10.8,
        pitch: 48,
        bearing: -10,
        name: 'Austin',
        metroBbox: { min_lat: 30.10, max_lat: 30.62, min_lng: -98.05, max_lng: -97.52 },
        allLabel: 'All Austin',
        divisions: [
          { key: 'ALL', label: 'All Austin', class: 'ALL' },
          { key: 'DOWNTOWN_CAPITOL', label: 'Downtown / Capitol', class: 'DowntownCapitol' },
          { key: 'EAST_AUSTIN_MUELLER', label: 'East Austin / Mueller', class: 'EastAustinMueller' },
          { key: 'SOUTH_AUSTIN_SOCO', label: 'South Austin / SoCo', class: 'SouthAustinSoCo' },
          { key: 'NORTH_AUSTIN_DOMAIN', label: 'North Austin / The Domain', class: 'NorthAustinDomain' },
          { key: 'WEST_AUSTIN_HILLS', label: 'West Austin Hills', class: 'WestAustinHills' },
          { key: 'PFLUGERVILLE_ROUND_ROCK_EDGE', label: 'Pflugerville / Round Rock Edge', class: 'PflugervilleRoundRockEdge' }
        ],
        presets: {
          'ALL': { lat: 30.2672, lng: -97.7431, zoom: 10.6, pitch: 45, bearing: -10 },
          'DOWNTOWN_CAPITOL': { lat: 30.2720, lng: -97.7430, zoom: 13.6, pitch: 54, bearing: -12 },
          'EAST_AUSTIN_MUELLER': { lat: 30.2800, lng: -97.6950, zoom: 12.8, pitch: 48, bearing: -10 },
          'SOUTH_AUSTIN_SOCO': { lat: 30.2300, lng: -97.7550, zoom: 12.8, pitch: 48, bearing: -10 },
          'NORTH_AUSTIN_DOMAIN': { lat: 30.3950, lng: -97.7100, zoom: 12.4, pitch: 48, bearing: -10 },
          'WEST_AUSTIN_HILLS': { lat: 30.3100, lng: -97.8000, zoom: 12.4, pitch: 45, bearing: -10 },
          'PFLUGERVILLE_ROUND_ROCK_EDGE': { lat: 30.4500, lng: -97.6400, zoom: 12.0, pitch: 45, bearing: -10 }
        }
      },
      cincinnati: {
        center: [-84.5120, 39.1031],
        zoom: 11.4,
        pitch: 48,
        bearing: -10,
        name: 'Cincinnati',
        metroBbox: { min_lat: 38.80, max_lat: 39.45, min_lng: -84.95, max_lng: -84.15 },
        allLabel: 'All Cincinnati',
        divisions: [
          { key: 'ALL', label: 'All Cincinnati', class: 'ALL' },
          { key: 'CINCINNATI_CORE', label: 'Cincinnati Core', class: 'CincinnatiCore' }
        ],
        presets: {
          'ALL': { lat: 39.1031, lng: -84.5120, zoom: 11.2, pitch: 45, bearing: -10 },
          'CINCINNATI_CORE': { lat: 39.1085, lng: -84.5145, zoom: 12.8, pitch: 48, bearing: -10 }
        }
      },
      boston: {
        center: [-71.065, 42.355],
        zoom: 10.8,
        pitch: 48,
        bearing: -10,
        name: 'Boston',
        metroBbox: { min_lat: 42.15, max_lat: 42.55, min_lng: -71.30, max_lng: -70.75 },
        allLabel: 'All Boston',
        divisions: [
          { key: 'ALL', label: 'All Boston', class: 'ALL' },
          { key: 'BOSTON_CORE', label: 'Boston Core', class: 'BostonCore' },
          { key: 'CAMBRIDGE_SOMERVILLE', label: 'Cambridge & Somerville', class: 'CambridgeSomerville' },
          { key: 'INNER_NORTH', label: 'Inner North & Route 128', class: 'InnerNorth' },
          { key: 'INNER_SOUTH', label: 'Inner South', class: 'InnerSouth' }
        ],
        presets: {
          'ALL': { lat: 42.355, lng: -71.065, zoom: 10.8, pitch: 45, bearing: -10 },
          'BOSTON_CORE': { lat: 42.351, lng: -71.065, zoom: 12.8, pitch: 48, bearing: -10 },
          'CAMBRIDGE_SOMERVILLE': { lat: 42.376, lng: -71.107, zoom: 12.8, pitch: 45, bearing: -10 },
          'INNER_NORTH': { lat: 42.425, lng: -71.075, zoom: 11.8, pitch: 42, bearing: -10 },
          'INNER_SOUTH': { lat: 42.245, lng: -71.030, zoom: 11.8, pitch: 43, bearing: -10 }
        }
      },
      baltimore: {
        center: [-76.612, 39.290],
        zoom: 10.8,
        pitch: 48,
        bearing: -10,
        name: 'Baltimore',
        metroBbox: { min_lat: 39.15, max_lat: 39.75, min_lng: -76.85, max_lng: -76.25 },
        allLabel: 'All Baltimore',
        divisions: [
          { key: 'ALL', label: 'All Baltimore', class: 'ALL' },
          { key: 'BALTIMORE_CORE', label: 'Baltimore Core', class: 'BaltimoreCore' }
        ],
        presets: {
          'ALL': { lat: 39.290, lng: -76.612, zoom: 10.8, pitch: 45, bearing: -10 },
          'BALTIMORE_CORE': { lat: 39.290, lng: -76.612, zoom: 11.8, pitch: 48, bearing: -10 }
        }
      },
      montgomery: {
        center: [-77.190, 39.140],
        zoom: 10.8,
        pitch: 48,
        bearing: -10,
        name: 'Montgomery County',
        metroBbox: { min_lat: 38.90, max_lat: 39.35, min_lng: -77.60, max_lng: -76.80 },
        allLabel: 'All Montgomery County',
        divisions: [
          { key: 'ALL', label: 'All Montgomery County', class: 'ALL' },
          { key: 'MONTGOMERY_CORE', label: 'Montgomery County', class: 'MontgomeryCore' }
        ],
        presets: {
          'ALL': { lat: 39.140, lng: -77.190, zoom: 10.8, pitch: 45, bearing: -10 },
          'MONTGOMERY_CORE': { lat: 39.140, lng: -77.190, zoom: 10.8, pitch: 45, bearing: -10 }
        }
      },
      baton_rouge: {
        center: [-91.1870, 30.4505],
        zoom: 11.4,
        pitch: 48,
        bearing: -10,
        name: 'Baton Rouge / EBR',
        metroBbox: { min_lat: 30.25, max_lat: 30.65, min_lng: -91.35, max_lng: -90.85 },
        allLabel: 'All Baton Rouge',
        divisions: [
          { key: 'ALL', label: 'All Baton Rouge', class: 'ALL' },
          { key: 'BATON_ROUGE_CORE', label: 'Baton Rouge Core', class: 'BatonRougeCore' }
        ],
        presets: {
          'ALL': { lat: 30.4505, lng: -91.1870, zoom: 11.2, pitch: 45, bearing: -10 },
          'BATON_ROUGE_CORE': { lat: 30.4505, lng: -91.1870, zoom: 11.8, pitch: 48, bearing: -10 }
        }
      },
      denver: {
        center: [-104.9903, 39.7392],
        zoom: 10.8,
        pitch: 48,
        bearing: -10,
        name: 'Denver',
        metroBbox: { min_lat: 39.55, max_lat: 39.95, min_lng: -105.20, max_lng: -104.50 },
        allLabel: 'All Denver',
        divisions: [
          { key: 'ALL', label: 'All Denver', class: 'ALL' },
          { key: 'DENVER_CORE', label: 'Denver Core', class: 'DenverCore' }
        ],
        presets: {
          'ALL': { lat: 39.7392, lng: -104.9903, zoom: 10.6, pitch: 45, bearing: -10 },
          'DENVER_CORE': { lat: 39.7527, lng: -104.9992, zoom: 11.8, pitch: 48, bearing: -10 }
        }
      },
      philadelphia: {
        center: [-75.1652, 39.9526],
        zoom: 11.0,
        pitch: 48,
        bearing: -10,
        name: 'Philadelphia',
        metroBbox: { min_lat: 39.87, max_lat: 40.14, min_lng: -75.28, max_lng: -74.95 },
        allLabel: 'All Philly',
        divisions: [
          { key: 'ALL', label: 'All Philly', class: 'ALL' },
          { key: 'CENTER_CITY_RITTENHOUSE', label: 'Center City / Rittenhouse', class: 'CenterCityRittenhouse' },
          { key: 'OLD_CITY_NORTHERN_LIBERTIES', label: 'Old City / NoLibs', class: 'OldCityNorthernLiberties' },
          { key: 'SOUTH_PHILLY_PASSYUNK', label: 'South Philly / Passyunk', class: 'SouthPhillyPassyunk' },
          { key: 'WEST_PHILLY_UNIVERSITY_CITY', label: 'West Philly / University City', class: 'WestPhillyUniversityCity' },
          { key: 'NORTH_PHILLY_TEMPLE', label: 'North Philly / Temple', class: 'NorthPhillyTemple' },
          { key: 'NORTHEAST_ROOSEVELT_BLVD', label: 'Northeast / Roosevelt Blvd', class: 'NortheastRooseveltBlvd' },
          { key: 'GERMANTOWN_MT_AIRY', label: 'Germantown / Mt. Airy', class: 'GermantownMtAiry' },
          { key: 'RIVER_WARDS_KENSINGTON', label: 'River Wards / Kensington', class: 'RiverWardsKensington' }
        ],
        presets: {
          'ALL': { lat: 39.9526, lng: -75.1652, zoom: 10.8, pitch: 45, bearing: -10 },
          'CENTER_CITY_RITTENHOUSE': { lat: 39.9500, lng: -75.1700, zoom: 13.6, pitch: 54, bearing: -12 },
          'OLD_CITY_NORTHERN_LIBERTIES': { lat: 39.9600, lng: -75.1400, zoom: 13.2, pitch: 50, bearing: -10 },
          'SOUTH_PHILLY_PASSYUNK': { lat: 39.9300, lng: -75.1750, zoom: 12.8, pitch: 48, bearing: -10 },
          'WEST_PHILLY_UNIVERSITY_CITY': { lat: 39.9500, lng: -75.2100, zoom: 13.0, pitch: 48, bearing: -10 },
          'NORTH_PHILLY_TEMPLE': { lat: 39.9950, lng: -75.1800, zoom: 12.4, pitch: 45, bearing: -10 },
          'NORTHEAST_ROOSEVELT_BLVD': { lat: 40.0450, lng: -75.0750, zoom: 12.2, pitch: 45, bearing: -10 },
          'GERMANTOWN_MT_AIRY': { lat: 40.0650, lng: -75.1850, zoom: 12.4, pitch: 45, bearing: -10 },
          'RIVER_WARDS_KENSINGTON': { lat: 39.9850, lng: -75.1250, zoom: 12.8, pitch: 48, bearing: -10 }
        }
      },
      washington_dc: {
        center: [-77.0369, 38.9072],
        zoom: 11.2,
        pitch: 48,
        bearing: -10,
        name: 'Washington DC',
        metroBbox: { min_lat: 38.79, max_lat: 38.995, min_lng: -77.12, max_lng: -76.909 },
        allLabel: 'All DC',
        divisions: [
          { key: 'ALL', label: 'All DC', class: 'ALL' },
          { key: 'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT', label: 'Downtown / NoMa / Riverfront', class: 'DowntownNomaCapitolRiverfront' },
          { key: 'CAPITOL_HILL_EAST_END', label: 'Capitol Hill / East End', class: 'CapitolHillEastEnd' },
          { key: 'DUPONT_KALORAMA_UPTOWN', label: 'Dupont / Kalorama / Uptown', class: 'DupontKaloramaUptown' },
          { key: 'GEORGETOWN_FOGGY_BOTTOM', label: 'Georgetown / Foggy Bottom', class: 'GeorgetownFoggyBottom' },
          { key: 'COLUMBIA_HEIGHTS_PETWORTH', label: 'Columbia Heights / Petworth', class: 'ColumbiaHeightsPetworth' },
          { key: 'BROOKLAND_RHODE_ISLAND_AVE', label: 'Brookland / Rhode Island Ave', class: 'BrooklandRhodeIslandAve' },
          { key: 'HILL_EAST_FAIRLINTON', label: 'Hill East / Fairlinton', class: 'HillEastFairlinton' },
          { key: 'ANACOSTIA_EAST_OF_THE_RIVER', label: 'Anacostia / East of the River', class: 'AnacostiaEastOfTheRiver' }
        ],
        presets: {
          'ALL': { lat: 38.9072, lng: -77.0369, zoom: 11.0, pitch: 45, bearing: -10 },
          'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT': { lat: 38.8950, lng: -77.0160, zoom: 13.6, pitch: 54, bearing: -12 },
          'CAPITOL_HILL_EAST_END': { lat: 38.8890, lng: -76.9840, zoom: 13.4, pitch: 50, bearing: -10 },
          'DUPONT_KALORAMA_UPTOWN': { lat: 38.9130, lng: -77.0420, zoom: 13.2, pitch: 48, bearing: -10 },
          'GEORGETOWN_FOGGY_BOTTOM': { lat: 38.9030, lng: -77.0680, zoom: 13.2, pitch: 48, bearing: -10 },
          'COLUMBIA_HEIGHTS_PETWORTH': { lat: 38.9380, lng: -77.0250, zoom: 12.8, pitch: 48, bearing: -10 },
          'BROOKLAND_RHODE_ISLAND_AVE': { lat: 38.9330, lng: -76.9780, zoom: 13.0, pitch: 48, bearing: -10 },
          'HILL_EAST_FAIRLINTON': { lat: 38.8760, lng: -76.9700, zoom: 13.0, pitch: 45, bearing: -10 },
          'ANACOSTIA_EAST_OF_THE_RIVER': { lat: 38.8620, lng: -76.9650, zoom: 12.6, pitch: 45, bearing: -10 }
        }
      }
    };
    CITY_CONFIGS.sf = CITY_CONFIGS.san_francisco;

    let currentCity = 'san_francisco';
    let activeCities = ['san_francisco'];
    let map = null;
    let gridGeoJSON = null;
    let shapChart = null;
    let currentPerspective = '3D';
    let currentMetric = 'lims_score';
    let selectedH3Index = null;
    let activeBoroughFilter = 'ALL';
    let catalystAlerts = [];

    function cityDisplayName(cityId) {
      return (CITY_CONFIGS[cityId] || {}).name || cityId.replace(/_/g, ' ');
    }

    const COMPARE_RADIUS_MILES = 175;
    const CITY_COORDINATES = {
      san_francisco: { lat: 37.7749, lng: -122.4194 }, chicago: { lat: 41.8781, lng: -87.6298 },
      nyc: { lat: 40.7128, lng: -74.0060 }, seattle: { lat: 47.6062, lng: -122.3321 },
      los_angeles: { lat: 34.0522, lng: -118.2437 }, new_orleans: { lat: 29.9511, lng: -90.0715 },
      norfolk: { lat: 36.8508, lng: -76.2859 }, detroit: { lat: 42.3314, lng: -83.0458 },
      austin: { lat: 30.2672, lng: -97.7431 }, philadelphia: { lat: 39.9526, lng: -75.1652 },
      washington_dc: { lat: 38.9072, lng: -77.0369 }, baltimore: { lat: 39.2904, lng: -76.6122 },
      montgomery: { lat: 39.0840, lng: -77.1528 }, boston: { lat: 42.3601, lng: -71.0589 },
      cincinnati: { lat: 39.1031, lng: -84.5120 }, baton_rouge: { lat: 30.4515, lng: -91.1871 },
      denver: { lat: 39.7392, lng: -104.9903 }
    };

    function renderCompareOptions() {
      const options = document.getElementById('compare-options');
      const toggle = document.getElementById('compare-toggle');
      if (!options || !toggle) return;
      const origin = CITY_COORDINATES[currentCity];
      const nearby = origin ? Object.entries(CITY_COORDINATES)
        .filter(([cityId, coords]) => cityId !== currentCity && haversineDistance(origin.lat, origin.lng, coords.lat, coords.lng) <= COMPARE_RADIUS_MILES)
        .sort(([a], [b]) => cityDisplayName(a).localeCompare(cityDisplayName(b))) : [];
      options.replaceChildren(...nearby.map(([cityId]) => {
        const label = document.createElement('label');
        label.innerHTML = `<input type="checkbox" name="compare-city" value="${cityId}"> ${escapeHtml(cityDisplayName(cityId))}`;
        label.querySelector('input').checked = activeCities.includes(cityId);
        return label;
      }));
      toggle.disabled = nearby.length === 0;
      toggle.title = nearby.length ? `Compare with nearby regions within ${COMPARE_RADIUS_MILES} miles` : 'No nearby regions available for comparison';
      if (!nearby.length) options.innerHTML = '<div style="color:var(--text-secondary);font-size:11px;padding:4px 0 7px;">No nearby regions available</div>';
    }

    function toggleCompareMenu() {
      const menu = document.getElementById('compare-menu');
      const toggle = document.getElementById('compare-toggle');
      if (!menu || !toggle) return;
      renderCompareOptions();
      menu.hidden = !menu.hidden;
      toggle.classList.toggle('active', !menu.hidden);
      toggle.setAttribute('aria-expanded', String(!menu.hidden));
      document.querySelectorAll('input[name="compare-city"]').forEach((input) => {
        input.checked = activeCities.includes(input.value) && input.value !== currentCity;
      });
    }

    async function applyComparison() {
      const selected = Array.from(document.querySelectorAll('input[name="compare-city"]:checked')).map((input) => input.value);
      activeCities = [currentCity, ...selected.filter((city) => city !== currentCity)];
      const menu = document.getElementById('compare-menu');
      const toggle = document.getElementById('compare-toggle');
      if (menu) menu.hidden = true;
      if (toggle) {
        toggle.classList.toggle('active', activeCities.length > 1);
        toggle.innerText = activeCities.length > 1 ? `${activeCities.length} regions` : '+ Compare';
        toggle.setAttribute('aria-expanded', 'false');
      }
      activeBoroughFilter = 'ALL';
      renderDivisionTabs();
      await fetchGridData();
      await fetchCatalysts();
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

    function findClosestCity(lat, lng) {
      const cityCoordinates = {
        'san_francisco': { lat: 37.7749, lng: -122.4194 },
        'chicago': { lat: 41.8781, lng: -87.6298 },
        'nyc': { lat: 40.7128, lng: -74.0060 },
        'seattle': { lat: 47.6062, lng: -122.3321 },
        'los_angeles': { lat: 34.0522, lng: -118.2437 },
        'new_orleans': { lat: 29.9511, lng: -90.0715 },
        'norfolk': { lat: 36.8508, lng: -76.2859 },
        'detroit': { lat: 42.3314, lng: -83.0458 },
        'austin': { lat: 30.2672, lng: -97.7431 },
        'philadelphia': { lat: 39.9526, lng: -75.1652 },
        'washington_dc': { lat: 38.9072, lng: -77.0369 }
      };
      let closest = 'san_francisco';
      let minDist = Infinity;
      for (const [cId, coords] of Object.entries(cityCoordinates)) {
        const d = haversineDistance(lat, lng, coords.lat, coords.lng);
        if (d < minDist) {
          minDist = d;
          closest = cId;
        }
      }
      return closest;
    }

    async function detectUserDefaultCity() {
      try {
        const saved = sessionStorage.getItem('urban_dev_user_city');
        if (saved && (saved === 'san_francisco' || saved === 'chicago' || saved === 'nyc' || saved === 'seattle' || saved === 'los_angeles' || saved === 'new_orleans' || saved === 'norfolk' || saved === 'detroit' || saved === 'austin' || saved === 'philadelphia' || saved === 'washington_dc')) {
          return saved;
        }
      } catch (e) {}

      if (!navigator.geolocation) {
        try { sessionStorage.setItem('urban_dev_user_city', 'san_francisco'); } catch (e) {}
        return 'san_francisco';
      }

      return new Promise((resolve) => {
        let resolved = false;
        const timeout = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            try { sessionStorage.setItem('urban_dev_user_city', 'san_francisco'); } catch (e) {}
            resolve('san_francisco');
          }
        }, 3000);

        navigator.geolocation.getCurrentPosition(
          (pos) => {
            if (resolved) return;
            resolved = true;
            clearTimeout(timeout);
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            const closest = findClosestCity(lat, lng);
            try { sessionStorage.setItem('urban_dev_user_city', closest); } catch (e) {}
            resolve(closest);
          },
          (err) => {
            if (resolved) return;
            resolved = true;
            clearTimeout(timeout);
            try { sessionStorage.setItem('urban_dev_user_city', 'san_francisco'); } catch (e) {}
            resolve('san_francisco');
          },
          { timeout: 2500, maximumAge: 600000, enableHighAccuracy: false }
        );
      });
    }

    const MAP_STYLE = {
      version: 8,
      sources: {
        'carto-dark': {
          type: 'raster',
          tiles: [
            'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
          ],
          tileSize: 256,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }
      },
      layers: [
        {
          id: 'style-background',
          type: 'background',
          paint: { 'background-color': '#080c14' }
        },
        {
          id: 'carto-dark-layer',
          type: 'raster',
          source: 'carto-dark',
          minzoom: 0,
          maxzoom: 20
        }
      ]
    };

    function normalizeBorough(b) {
      if (!b) {
        if (currentCity === 'san_francisco' || currentCity === 'sf') return 'SAN_FRANCISCO_CORE';
        if (currentCity === 'chicago') return 'Central / Downtown';
        if (currentCity === 'seattle') return 'SEATTLE_CORE';
        if (currentCity === 'los_angeles') return 'CENTRAL_LA';
        if (currentCity === 'new_orleans') return 'CBD_FRENCH_QUARTER';
        if (currentCity === 'norfolk') return 'DOWNTOWN_WATERFRONT';
        if (currentCity === 'detroit') return 'DOWNTOWN_MIDTOWN_CORKTOWN';
        if (currentCity === 'austin') return 'DOWNTOWN_CAPITOL';
        if (currentCity === 'philadelphia') return 'CENTER_CITY_RITTENHOUSE';
        if (currentCity === 'washington_dc') return 'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT';
        return 'Manhattan';
      }
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
      return normalizeBorough(b).replace(/[\s\-_/]+/g, '');
    }

    function renderDivisionTabs() {
      const nav = document.getElementById('borough-tabs');
      if (!nav) return;
      const cfg = CITY_CONFIGS[currentCity] || CITY_CONFIGS.nyc;
      nav.innerHTML = cfg.divisions.map(d => {
        const isActive = (activeBoroughFilter === 'ALL' && d.key === 'ALL') || (normalizeBorough(d.key) === activeBoroughFilter);
        return `<button class="borough-btn ${d.class} ${isActive ? 'active' : ''}" data-borough="${d.key}" onclick="selectBoroughFilter('${d.key}')">${d.label}</button>`;
      }).join('');
    }

    async function changeCity(cityId) {
      currentCity = (cityId || 'san_francisco').toLowerCase().trim();
      if (currentCity === 'sf') currentCity = 'san_francisco';
      activeCities = activeCities.length > 1
        ? [currentCity, ...activeCities.filter((city) => city !== currentCity)]
        : [currentCity];
      renderCompareOptions();
      try { sessionStorage.setItem('urban_dev_user_city', currentCity); } catch (e) {}
      activeBoroughFilter = 'ALL';
      renderDivisionTabs();
      
      const cfg = CITY_CONFIGS[currentCity] || CITY_CONFIGS.nyc;
      if (map) {
        map.flyTo({
          center: cfg.center,
          zoom: cfg.zoom,
          pitch: currentPerspective === '3D' ? cfg.pitch : 0,
          bearing: currentPerspective === '3D' ? cfg.bearing : 0,
          duration: 1400
        });
      }

      await loadSubmarkets();
      await fetchGridData();
      await fetchCatalysts();
    }

    async function loadSubmarkets() {
      // Never let a failed city request render the previously selected city's data.
      // The edge API can reject a stale/missing snapshot; retaining SUBMARKETS here
      // makes the grid and catalyst fallbacks silently show the wrong city.
      SUBMARKETS = {};
      try {
        const resp = await fetch(`/api/v1/submarkets?city_id=${currentCity}`);
        if (resp.ok) {
          const data = await resp.json();
          if (data.submarkets && Object.keys(data.submarkets).length > 0) {
            SUBMARKETS = data.submarkets;
          }
        }
      } catch (e) {
        console.debug('Submarket fetch error:', e);
      }
    }

    window.addEventListener('DOMContentLoaded', async () => {
      try {
        const detected = await detectUserDefaultCity();
        currentCity = detected || 'san_francisco';
      } catch (e) {
        currentCity = 'san_francisco';
      }

      const citySelect = document.getElementById('city-select');
      if (citySelect) {
        citySelect.value = currentCity;
      }

      renderDivisionTabs();
      initMap();
      await loadSubmarkets();

      document.addEventListener('click', (e) => {
        const wrap = document.querySelector('.search-wrapper');
        if (wrap && !wrap.contains(e.target)) {
          const dd = document.getElementById('search-dropdown');
          if (dd) dd.classList.remove('visible');
        }
      });
    });

    window.addEventListener('resize', () => {
      if (map) map.resize();
    });

    function selectBoroughFilter(borough) {
      activeBoroughFilter = normalizeBorough(borough === 'ALL' ? 'ALL' : borough);
      
      document.querySelectorAll('.borough-btn').forEach(btn => {
        const b = btn.getAttribute('data-borough');
        const isActive = (activeBoroughFilter === 'ALL' && b === 'ALL') || (normalizeBorough(b) === activeBoroughFilter);
        btn.classList.toggle('active', isActive);
      });

      jumpToBorough(activeBoroughFilter);
      filterFeedByBorough();
    }

    function jumpToBorough(borough) {
      const bKey = normalizeBorough(borough);
      const cfg = CITY_CONFIGS[currentCity] || CITY_CONFIGS.nyc;
      const preset = cfg.presets[bKey] || cfg.presets['ALL'];
      if (map && preset) {
        map.flyTo({
          center: [preset.lng, preset.lat],
          zoom: preset.zoom,
          pitch: currentPerspective === '3D' ? preset.pitch : 0,
          bearing: currentPerspective === '3D' ? preset.bearing : 0,
          duration: 1200
        });
      }
    }

    function onGlobalSearch(query) {
      const q = (query || '').toLowerCase().trim();
      const dd = document.getElementById('search-dropdown');
      if (!dd) return;

      if (!q) {
        dd.classList.remove('visible');
        dd.innerHTML = '';
        return;
      }

      const matches = Object.entries(SUBMARKETS).filter(([name, meta]) => {
        return name.toLowerCase().includes(q) || 
               normalizeBorough(meta.borough).toLowerCase().includes(q) ||
               (meta.description && meta.description.toLowerCase().includes(q));
      }).slice(0, 8);

      if (matches.length === 0) {
        dd.innerHTML = '<div style="padding: 10px 12px; font-size:11px; color:var(--text-muted);">No submarkets found. Press Enter to search as coordinate or H3.</div>';
        dd.classList.add('visible');
        return;
      }

      dd.innerHTML = matches.map(([name, meta]) => {
        const borough = normalizeBorough(meta.borough);
        const bClass = getBoroughClass(borough);
        return `
          <div class="search-result-item" onclick="selectSearchSubmarket('${name}')">
            <span><strong>${name}</strong> <span class="borough-tag ${bClass}" style="margin-left:4px;">${borough}</span></span>
            <span class="item-sub">LIMS ${Number(meta.base_lims || 80.0).toFixed(1)}</span>
          </div>
        `;
      }).join('');
      dd.classList.add('visible');
    }

    function selectSearchSubmarket(name) {
      const dd = document.getElementById('search-dropdown');
      if (dd) dd.classList.remove('visible');
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

      const foundKey = Object.keys(SUBMARKETS).find(k => k.toLowerCase() === val.toLowerCase());
      if (foundKey) {
        zoomToSubmarket(foundKey);
        return;
      }

      searchCoordinateOrHex(val);
    }

    function initMap() {
      try {
        const cfg = CITY_CONFIGS[currentCity] || CITY_CONFIGS.san_francisco;
        map = new maplibregl.Map({
          container: 'map',
          style: MAP_STYLE,
          center: cfg.center,
          zoom: cfg.zoom,
          pitch: currentPerspective === '3D' ? cfg.pitch : 0,
          bearing: currentPerspective === '3D' ? cfg.bearing : 0,
          antialias: true
        });

        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showCompass: false }), 'bottom-right');

        map.on('load', async () => {
          map.resize();
          setupGridLayers();
          await fetchGridData();
          await fetchCatalysts();
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
            const subName = props.submarket || (subInfo ? subInfo.name : 'NYC Micro-Block');
            const borough = normalizeBorough(props.borough || (subInfo ? subInfo.meta.borough : getBoroughNameByCoords(coords.lat, coords.lng)));
            const bClass = getBoroughClass(borough);
            const limsVal = Number(props.lims_score || 80.0);
            const delta6m = Number(props.delta_6m_p50 || 0.12);
            
            popup.setLngLat(coords)
              .setHTML(`
                <div style="font-size: 11px; min-width: 150px; line-height: 1.4;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong style="color: var(--text-main); font-size:12px;">${subName}</strong>
                    <span class="borough-tag ${bClass}">${borough}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; gap:8px; margin-top:2px;">
                    <span style="color:var(--text-secondary);">LIMS Score:</span>
                    <strong style="color: ${limsVal >= 85 ? 'var(--accent-danger)' : 'var(--accent-success)'}">${limsVal.toFixed(1)}</strong>
                  </div>
                  <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span style="color:var(--text-secondary);">6M Return:</span>
                    <strong style="color: var(--accent-success);">+${(delta6m * 100).toFixed(1)}%</strong>
                  </div>
                </div>
              `)
              .addTo(map);
          }
        };

        map.on('mousemove', 'h3-hex-fill', showPopup);
        map.on('mouseleave', 'h3-hex-fill', () => {
          map.getCanvas().style.cursor = '';
          popup.remove();
        });

        map.on('mousemove', 'h3-hex-extrusion', showPopup);
        map.on('mouseleave', 'h3-hex-extrusion', () => {
          map.getCanvas().style.cursor = '';
          popup.remove();
        });

        map.on('click', 'h3-hex-fill', (e) => {
          if (e.features && e.features.length > 0) handleHexSelection(e.features[0].properties);
        });

        map.on('click', 'h3-hex-extrusion', (e) => {
          if (e.features && e.features.length > 0) handleHexSelection(e.features[0].properties);
        });
      } catch (err) {
        console.error('Map initialization error:', err);
      }
    }

    async function fetchGridData() {
      if (activeCities.length > 1) {
        const grids = await Promise.all(activeCities.map(async (cityId) => {
          try {
            const resp = await fetch(`/api/v1/grid?city_id=${cityId}`);
            if (!resp.ok) return { type: 'FeatureCollection', features: [] };
            const data = await resp.json();
            return {
              ...data,
              features: (data.features || []).map((feature) => ({
                ...feature,
                properties: { ...(feature.properties || {}), city_id: cityId, city_name: cityDisplayName(cityId) }
              }))
            };
          } catch (e) {
            return { type: 'FeatureCollection', features: [] };
          }
        }));
        gridGeoJSON = { type: 'FeatureCollection', features: grids.flatMap((grid) => grid.features || []) };
        if (map && map.getSource('h3-grid-source')) {
          map.getSource('h3-grid-source').setData(gridGeoJSON);
          fitMapToFeatures(gridGeoJSON.features);
        }
        return;
      }
      try {
        const resp = await fetch(`/api/v1/grid?city_id=${currentCity}`);
        if (resp.ok) {
          gridGeoJSON = await resp.json();
        } else {
          gridGeoJSON = generateClientGridGeoJSON();
        }
      } catch (err) {
        gridGeoJSON = generateClientGridGeoJSON();
      }

      if (map && map.getSource('h3-grid-source')) {
        map.getSource('h3-grid-source').setData(gridGeoJSON);
      }
    }

    function fitMapToFeatures(features) {
      if (!map || !features || !features.length) return;
      const bounds = new maplibregl.LngLatBounds();
      features.forEach((feature) => (feature.geometry?.coordinates?.[0] || []).forEach(([lng, lat]) => bounds.extend([lng, lat])));
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 90, maxZoom: 11.6, duration: 1100 });
    }

    function buildFeature(cell, name, meta, boundary, lat, lng, lims) {
      const borough = normalizeBorough(meta.borough);
      return {
        type: 'Feature',
        id: cell,
        geometry: {
          type: 'Polygon',
          coordinates: [boundary]
        },
        properties: {
          h3_index: cell,
          submarket: name,
          borough: borough,
          description: meta.description || '',
          centroid_lat: lat,
          centroid_lng: lng,
          lims_score: lims,
          delta_6m_p10: +(lims * 0.0011).toFixed(4),
          delta_6m_p50: +(lims * 0.0018).toFixed(4),
          delta_6m_p90: +(lims * 0.0026).toFixed(4),
          delta_12m_spillover: +(lims * 0.0014).toFixed(4),
          prob_18m_macro_outperformance: +(lims / 115.0).toFixed(4),
          is_catalyst: lims >= 85.0,
          capex_density_decayed: meta.capex || 500000.0,
          permit_velocity: meta.permit_vel || 0.35,
          shift_ratio_311: meta.shift_ratio || 2.5,
          sla_new_filings_90d: meta.sla || 3,
          shap_attributions: JSON.stringify({
            capex_density_decayed: +(lims * 0.0007).toFixed(4),
            permit_velocity: +(lims * 0.0005).toFixed(4),
            shift_ratio_311: +(lims * 0.0004).toFixed(4),
            sla_new_filings_90d: +(lims * 0.0002).toFixed(4),
            complaints_neglect_count: -0.0012
          })
        }
      };
    }

    function generateClientGridGeoJSON() {
      const features = [];
      const hasH3 = typeof h3 !== 'undefined';

      for (const [name, meta] of Object.entries(SUBMARKETS)) {
        if (hasH3) {
          try {
            const centerCell = h3.latLngToCell(meta.lat, meta.lng, 9);
            const ring = h3.gridDisk(centerCell, 1);
            ring.forEach((cell, idx) => {
              let boundary = h3.cellToBoundary(cell, true);
              if (boundary && boundary.length > 0) {
                if (boundary[0][0] !== boundary[boundary.length - 1][0] || boundary[0][1] !== boundary[boundary.length - 1][1]) {
                  boundary.push([boundary[0][0], boundary[0][1]]);
                }
              }
              const centroid = h3.cellToLatLng(cell);
              const lims = Math.min(98.0, Math.max(60.0, (meta.base_lims || 80.0) + (idx % 3 - 1) * 2.2));
              features.push(buildFeature(cell, name, meta, boundary, centroid[0], centroid[1], lims));
            });
            continue;
          } catch (e) {}
        }

        const cellId = 'hex_' + name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const radius = 0.0035;
        const boundary = [];
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i;
          boundary.push([meta.lng + radius * Math.cos(angle), meta.lat + (radius * 0.75) * Math.sin(angle)]);
        }
        boundary.push([boundary[0][0], boundary[0][1]]);
        features.push(buildFeature(cellId, name, meta, boundary, meta.lat, meta.lng, meta.base_lims || 80.0));
      }
      return { type: 'FeatureCollection', features };
    }

    function setupGridLayers() {
      if (!map || map.getSource('h3-grid-source')) return;

      map.addSource('h3-grid-source', {
        type: 'geojson',
        data: gridGeoJSON || { type: 'FeatureCollection', features: [] }
      });

      // 2D Fill Layer
      map.addLayer({
        id: 'h3-hex-fill',
        type: 'fill',
        source: 'h3-grid-source',
        layout: { visibility: currentPerspective === '2D' ? 'visible' : 'none' },
        paint: {
          'fill-color': [
            'interpolate', ['linear'], ['get', 'lims_score'],
            50, '#34d399',
            70, '#fbbf24',
            85, '#fb923c',
            95, '#f43f5e'
          ],
          'fill-opacity': 0.78
        }
      });

      // 2D Line Outline Layer
      map.addLayer({
        id: 'h3-hex-line',
        type: 'line',
        source: 'h3-grid-source',
        paint: {
          'line-color': 'rgba(255, 255, 255, 0.25)',
          'line-width': 1.0
        }
      });

      // 3D Fill Extrusion Layer
      map.addLayer({
        id: 'h3-hex-extrusion',
        type: 'fill-extrusion',
        source: 'h3-grid-source',
        layout: { visibility: currentPerspective === '3D' ? 'visible' : 'none' },
        paint: {
          'fill-extrusion-color': [
            'interpolate', ['linear'], ['get', 'lims_score'],
            50, '#34d399',
            70, '#fbbf24',
            85, '#fb923c',
            95, '#f43f5e'
          ],
          'fill-extrusion-height': [
            '*',
            ['max', 0, ['-', ['coalesce', ['get', 'lims_score'], 50], 40]],
            18
          ],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.88
        }
      });

      // Selected Hex Highlight Outline
      map.addLayer({
        id: 'h3-hex-selected',
        type: 'line',
        source: 'h3-grid-source',
        filter: ['==', ['get', 'h3_index'], ''],
        paint: {
          'line-color': '#38bdf8',
          'line-width': 3
        }
      });
    }

    function updateMetricVisuals() {
      if (!map) return;
      const metricEl = document.getElementById('metric-select');
      if (!metricEl) return;
      currentMetric = metricEl.value;
      const legendTitle = document.getElementById('legend-metric-title');
      const legendMin = document.getElementById('legend-min');
      const legendMid = document.getElementById('legend-mid');
      const legendMax = document.getElementById('legend-max');

      let colorExpr, heightExpr;
      if (currentMetric === 'lims_score') {
        if (legendTitle) legendTitle.innerText = 'LIMS Momentum Score';
        if (legendMin) legendMin.innerText = '0.0';
        if (legendMid) legendMid.innerText = '70.0';
        if (legendMax) legendMax.innerText = '100.0';
        colorExpr = [
          'interpolate', ['linear'], ['get', 'lims_score'],
          50, '#34d399',
          70, '#fbbf24',
          85, '#fb923c',
          95, '#f43f5e'
        ];
        heightExpr = ['*', ['max', 0, ['-', ['coalesce', ['get', 'lims_score'], 50], 40]], 18];
      } else if (currentMetric === 'delta_6m_p50') {
        if (legendTitle) legendTitle.innerText = '6M Expected Return (p50)';
        if (legendMin) legendMin.innerText = '+0%';
        if (legendMid) legendMid.innerText = '+12%';
        if (legendMax) legendMax.innerText = '+25%';
        colorExpr = [
          'interpolate', ['linear'], ['get', 'delta_6m_p50'],
          0.04, '#34d399',
          0.10, '#fbbf24',
          0.16, '#fb923c',
          0.22, '#f43f5e'
        ];
        heightExpr = ['*', ['max', 0, ['coalesce', ['get', 'delta_6m_p50'], 0.05]], 4000];
      } else if (currentMetric === 'delta_12m_spillover') {
        if (legendTitle) legendTitle.innerText = '12M Spatial Spillover';
        if (legendMin) legendMin.innerText = '+0%';
        if (legendMid) legendMid.innerText = '+10%';
        if (legendMax) legendMax.innerText = '+20%';
        colorExpr = [
          'interpolate', ['linear'], ['get', 'delta_12m_spillover'],
          0.02, '#34d399',
          0.08, '#fbbf24',
          0.14, '#fb923c',
          0.20, '#f43f5e'
        ];
        heightExpr = ['*', ['max', 0, ['coalesce', ['get', 'delta_12m_spillover'], 0.04]], 4500];
      } else {
        if (legendTitle) legendTitle.innerText = '18M Macro Outperformance';
        if (legendMin) legendMin.innerText = '0.0';
        if (legendMid) legendMid.innerText = '0.5';
        if (legendMax) legendMax.innerText = '1.0';
        colorExpr = [
          'interpolate', ['linear'], ['get', 'prob_18m_macro_outperformance'],
          0.2, '#34d399',
          0.5, '#fbbf24',
          0.75, '#fb923c',
          0.95, '#f43f5e'
        ];
        heightExpr = ['*', ['max', 0, ['coalesce', ['get', 'prob_18m_macro_outperformance'], 0.5]], 900];
      }

      if (map.getLayer('h3-hex-fill')) {
        map.setPaintProperty('h3-hex-fill', 'fill-color', colorExpr);
      }
      if (map.getLayer('h3-hex-extrusion')) {
        map.setPaintProperty('h3-hex-extrusion', 'fill-extrusion-color', colorExpr);
        map.setPaintProperty('h3-hex-extrusion', 'fill-extrusion-height', heightExpr);
      }
    }

    function setPerspective(mode) {
      currentPerspective = mode;
      const btn3d = document.getElementById('btn-3d');
      const btn2d = document.getElementById('btn-2d');
      if (btn3d) btn3d.classList.toggle('active', mode === '3D');
      if (btn2d) btn2d.classList.toggle('active', mode === '2D');

      if (map) {
        if (map.getLayer('h3-hex-fill') && map.getLayer('h3-hex-extrusion')) {
          map.setLayoutProperty('h3-hex-fill', 'visibility', mode === '2D' ? 'visible' : 'none');
          map.setLayoutProperty('h3-hex-extrusion', 'visibility', mode === '3D' ? 'visible' : 'none');
        }

        map.easeTo({
          pitch: mode === '3D' ? 52 : 0,
          bearing: mode === '3D' ? -15 : 0,
          duration: 900
        });
      }
    }

    function togglePerspective() {
      setPerspective(currentPerspective === '3D' ? '2D' : '3D');
    }

    function zoomToSubmarket(name) {
      if (!name) return;
      const meta = SUBMARKETS[name];
      if (!meta) return;

      if (map) {
        map.flyTo({
          center: [meta.lng, meta.lat],
          zoom: meta.zoom || 15.2,
          pitch: currentPerspective === '3D' ? (meta.pitch || 50) : 0,
          bearing: -15,
          duration: 1200
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
          lims_score: meta.base_lims || 82.0,
          delta_6m_p10: +((meta.base_lims || 82.0) * 0.0011).toFixed(4),
          delta_6m_p50: +((meta.base_lims || 82.0) * 0.0018).toFixed(4),
          delta_6m_p90: +((meta.base_lims || 82.0) * 0.0026).toFixed(4),
          delta_12m_spillover: +((meta.base_lims || 82.0) * 0.0014).toFixed(4),
          prob_18m_macro_outperformance: +((meta.base_lims || 82.0) / 115.0).toFixed(4),
          capex_density_decayed: meta.capex || 500000.0,
          permit_velocity: meta.permit_vel || 0.35,
          shift_ratio_311: meta.shift_ratio || 2.5,
          sla_new_filings_90d: meta.sla || 3,
          inference_latency_ms: 2.8
        });
      }
    }

    async function fetchCatalysts() {
      if (activeCities.length > 1) {
        const responses = await Promise.all(activeCities.map(async (cityId) => {
          try {
            const resp = await fetch(`/api/v1/catalysts?city_id=${cityId}&min_lims=85.0`);
            if (!resp.ok) return [];
            const data = await resp.json();
            return (data.catalysts || []).map((c) => ({ ...c, city_id: cityId, city_name: cityDisplayName(cityId) }));
          } catch (e) { return []; }
        }));
        catalystAlerts = responses.flat();
        renderCatalystFeed();
        return;
      }
      try {
        const resp = await fetch(`/api/v1/catalysts?city_id=${currentCity}&min_lims=85.0`);
        if (resp.ok) {
          const data = await resp.json();
          catalystAlerts = data.catalysts || [];
          renderCatalystFeed();
          return;
        }
      } catch (err) {}

      catalystAlerts = Object.entries(SUBMARKETS)
        .filter(([_, meta]) => (meta.base_lims || 0) >= 85.0)
        .map(([name, meta]) => {
          const cell = (typeof h3 !== 'undefined') ? h3.latLngToCell(meta.lat, meta.lng, 9) : 'hex_' + name.toLowerCase();
          return {
            h3_index: cell,
            submarket: name,
            borough: normalizeBorough(meta.borough),
            centroid_lat: meta.lat,
            centroid_lng: meta.lng,
            lims_score: meta.base_lims,
            delta_6m_p50: +(meta.base_lims * 0.0018).toFixed(4),
            delta_12m_spillover: +(meta.base_lims * 0.0014).toFixed(4)
          };
        });
      renderCatalystFeed();
    }

    function filterFeedByBorough() {
      renderCatalystFeed();
    }

    function renderCatalystFeed() {
      const container = document.getElementById('catalyst-feed-list');
      const countBadge = document.getElementById('stat-active-catalysts');
      if (!container) return;

      const filtered = catalystAlerts.filter(c => {
        if (activeBoroughFilter === 'ALL') return true;
        const b = normalizeBorough(c.borough);
        return b === activeBoroughFilter;
      });

      if (countBadge) {
        countBadge.innerText = `${filtered.length} Active`;
      }

      if (filtered.length === 0) {
        container.innerHTML = `<div style="font-size:11px; color:var(--text-muted); text-align:center; padding:24px 0;">No active catalysts in ${activeBoroughFilter}</div>`;
        return;
      }

      container.innerHTML = filtered.map((c) => {
        const subInfo = getSubmarketInfoByCoords(c.centroid_lat, c.centroid_lng);
        const submarket = c.submarket || (subInfo ? subInfo.name : 'Active Parcel');
        const borough = normalizeBorough(c.borough || (subInfo ? subInfo.meta.borough : 'Manhattan'));
        const bClass = getBoroughClass(borough);
        const lat = c.centroid_lat || (subInfo ? subInfo.meta.lat : 40.72);
        const lng = c.centroid_lng || (subInfo ? subInfo.meta.lng : -74.00);
        const isSelected = selectedH3Index === c.h3_index;

        return `
          <div class="catalyst-item ${isSelected ? 'selected' : ''}" onclick="zoomToHex('${c.h3_index}', ${lat}, ${lng})">
            <div class="catalyst-item-top">
              <span class="catalyst-name">${submarket}</span>
              <span class="catalyst-lims-tag">${Number(c.lims_score || 85.0).toFixed(1)}</span>
            </div>
            <div class="catalyst-item-bottom">
              <span class="borough-tag ${bClass}">${borough}</span>
              ${c.city_name ? `<span class="borough-tag">${c.city_name}</span>` : ''}
              <span class="delta-tag">+${(Number(c.delta_6m_p50 || 0.14) * 100).toFixed(1)}% 6M</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function zoomToHex(h3Index, lat, lng) {
      selectedH3Index = h3Index;
      if (map) {
        map.flyTo({
          center: [lng, lat],
          zoom: 15.6,
          pitch: currentPerspective === '3D' ? 55 : 0,
          bearing: -12,
          duration: 1100
        });

        if (map.getLayer('h3-hex-selected')) {
          map.setFilter('h3-hex-selected', ['==', ['get', 'h3_index'], h3Index]);
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
          description: subInfo ? subInfo.meta.description : 'Active spatio-temporal cluster',
          centroid_lat: lat,
          centroid_lng: lng,
          lims_score: subInfo ? subInfo.meta.base_lims : 84.0,
          delta_6m_p10: 0.035,
          delta_6m_p50: 0.145,
          delta_6m_p90: 0.225,
          delta_12m_spillover: 0.125,
          prob_18m_macro_outperformance: 0.85,
          capex_density_decayed: subInfo ? subInfo.meta.capex : 550000.0,
          permit_velocity: subInfo ? subInfo.meta.permit_vel : 0.42,
          shift_ratio_311: subInfo ? subInfo.meta.shift_ratio : 3.0,
          sla_new_filings_90d: subInfo ? subInfo.meta.sla : 4,
          inference_latency_ms: 2.8
        };
      }

      handleHexSelection(props);
    }

    function handleHexSelection(props) {
      if (!props) return;
      selectedH3Index = props.h3_index;
      if (map && map.getLayer('h3-hex-selected')) {
        map.setFilter('h3-hex-selected', ['==', ['get', 'h3_index'], props.h3_index]);
      }

      const container = document.getElementById('inspector-content');
      if (!container) return;

      const lims = Number(props.lims_score) || 0;
      const isCatalyst = lims >= 85.0;
      const p10 = (Number(props.delta_6m_p10 || 0.02) * 100).toFixed(1);
      const p50 = (Number(props.delta_6m_p50 || 0.12) * 100).toFixed(1);
      const p90 = (Number(props.delta_6m_p90 || 0.20) * 100).toFixed(1);
      const spillover = (Number(props.delta_12m_spillover || 0.10) * 100).toFixed(1);
      const macroProb = (Number(props.prob_18m_macro_outperformance || 0.75) * 100).toFixed(1);

      const lat = Number(props.centroid_lat || 40.72);
      const lng = Number(props.centroid_lng || -74.00);
      const subInfo = getSubmarketInfoByCoords(lat, lng);
      const submarketName = props.submarket || (subInfo ? subInfo.name : 'NYC Corridor');
      const boroughName = normalizeBorough(props.borough || (subInfo ? subInfo.meta.borough : getBoroughNameByCoords(lat, lng)));
      const description = props.description || (subInfo ? subInfo.meta.description : 'Active spatio-temporal cluster');
      const bClass = getBoroughClass(boroughName);

      let shapObj = props.shap_attributions;
      if (typeof shapObj === 'string') {
        try { shapObj = JSON.parse(shapObj); } catch(e) { shapObj = null; }
      }

      container.innerHTML = `
        <div class="inspector-content">
          <!-- Parcel Header -->
          <div class="parcel-header">
            <div class="parcel-title-row">
              <div class="parcel-name">${submarketName}</div>
              <span class="borough-tag ${bClass}">${boroughName}</span>
            </div>
            <div class="parcel-meta-sub">
              <span>H3: ${props.h3_index || ''}</span>
              <span>•</span>
              <span>${lat.toFixed(4)}, ${lng.toFixed(4)}</span>
            </div>
            <div class="parcel-description">${description}</div>
          </div>

          <!-- Score Hero Summary -->
          <div class="score-hero-block">
            <div class="score-hero-left">
              <span class="score-hero-label">LIMS Momentum Score</span>
              <span class="score-status-pill" style="color: ${isCatalyst ? 'var(--accent-danger)' : 'var(--accent-success)'}">
                ${isCatalyst ? '● High Catalyst Alert' : '● Active Signal'}
              </span>
            </div>
            <div class="score-hero-val" style="color: ${isCatalyst ? 'var(--accent-danger)' : 'var(--accent-success)'}">
              ${lims.toFixed(1)}
            </div>
          </div>

          <!-- Multi-Horizon Forecast -->
          <div>
            <div class="forecast-section-title">Multi-Horizon Projections</div>
            <div class="quantiles-card">
              <div class="quantiles-header">
                <span>6-Month Forecast Quantiles</span>
                <span style="font-family:var(--font-mono); font-size:10px; color:var(--text-muted);">LightGBM</span>
              </div>
              <div class="quantiles-spread-row">
                <div class="q-box">
                  <span class="q-lbl">Bearish (p10)</span>
                  <span class="q-num">+${p10}%</span>
                </div>
                <div class="q-box expected">
                  <span class="q-lbl">Expected (p50)</span>
                  <span class="q-num">+${p50}%</span>
                </div>
                <div class="q-box">
                  <span class="q-lbl">Bullish (p90)</span>
                  <span class="q-num">+${p90}%</span>
                </div>
              </div>
            </div>

            <div class="horizon-pairs">
              <div class="horizon-mini-card">
                <div class="horizon-mini-lbl">12M Spatial Spillover</div>
                <div class="horizon-mini-val" style="color: var(--accent-warning);">+${spillover}%</div>
              </div>
              <div class="horizon-mini-card">
                <div class="horizon-mini-lbl">18M Macro Outperf.</div>
                <div class="horizon-mini-val" style="color: var(--accent-purple);">${macroProb}%</div>
              </div>
            </div>
          </div>

          <!-- SHAP Attribution Breakdown -->
          <div>
            <div class="forecast-section-title">SHAP Feature Attribution</div>
            <div class="chart-block">
              <canvas id="shap-chart"></canvas>
            </div>
          </div>

          <!-- Telemetry Attributes Table -->
          <div>
            <div class="forecast-section-title">Leading Telemetry Indicators</div>
            <table class="telemetry-table">
              <tr>
                <td class="lbl">CapEx Density (Decayed)</td>
                <td class="val">$${Number(props.capex_density_decayed || 550000).toLocaleString()}/km²</td>
              </tr>
              <tr>
                <td class="lbl">DOB Permit Velocity</td>
                <td class="val">+${(Number(props.permit_velocity || 0.42) * 100).toFixed(1)}%</td>
              </tr>
              <tr>
                <td class="lbl">311 Shift Ratio (QoL/Neglect)</td>
                <td class="val">${Number(props.shift_ratio_311 || 3.0).toFixed(2)}x</td>
              </tr>
              <tr>
                <td class="lbl">SLA Liquor Filings (90d)</td>
                <td class="val">${props.sla_new_filings_90d || 4} filings</td>
              </tr>
              <tr>
                <td class="lbl">Inference Latency</td>
                <td class="val" style="color:var(--accent-primary);">${props.inference_latency_ms || 2.8} ms</td>
              </tr>
            </table>
          </div>
        </div>
      `;

      renderShapChart(shapObj);
    }

    function renderShapChart(shap) {
      const ctx = document.getElementById('shap-chart');
      if (!ctx) return;

      if (shapChart) {
        shapChart.destroy();
        shapChart = null;
      }

      const hasData = shap && typeof shap === 'object' && Object.keys(shap).length > 0;
      const data = hasData ? shap : {
        'CapEx Density': 0.048,
        'Permit Velocity': 0.035,
        '311 Shift Ratio': 0.027,
        'SLA Filings': 0.015,
        'Deed Volume': 0.008,
        'Neglect 311': -0.012
      };

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
          animation: { duration: 200 },
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
                color: '#64748b',
                font: { family: 'IBM Plex Mono', size: 9 },
                callback: (v) => `${(v * 100).toFixed(1)}%`
              }
            },
            y: {
              grid: { display: false },
              ticks: {
                color: '#94a3b8',
                font: { family: 'IBM Plex Sans', size: 10 }
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
            zoom: 15.5,
            pitch: currentPerspective === '3D' ? 52 : 0,
            bearing: -15,
            duration: 1100
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
          const baseLims = subInfo ? (subInfo.meta.base_lims || 82.5) : 82.5;
          predData = {
            h3_index: h3Index || 'custom_hex',
            lims_score: baseLims,
            delta_6m_p10: +(baseLims * 0.0011).toFixed(4),
            delta_6m_p50: +(baseLims * 0.0018).toFixed(4),
            delta_6m_p90: +(baseLims * 0.0026).toFixed(4),
            delta_12m_spillover: +(baseLims * 0.0014).toFixed(4),
            prob_18m_macro_outperformance: +(baseLims / 115.0).toFixed(4),
            capex_density_decayed: subInfo ? subInfo.meta.capex : 450000.0,
            permit_velocity: subInfo ? subInfo.meta.permit_vel : 0.38,
            shift_ratio_311: subInfo ? subInfo.meta.shift_ratio : 2.8,
            sla_new_filings_90d: subInfo ? subInfo.meta.sla : 3,
            inference_latency_ms: 2.7
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
      if (!lat || !lng) {
        if (currentCity === 'san_francisco' || currentCity === 'sf') return 'SAN_FRANCISCO_CORE';
        if (currentCity === 'chicago') return 'Central / Downtown';
        if (currentCity === 'seattle') return 'SEATTLE_CORE';
        if (currentCity === 'los_angeles') return 'CENTRAL_LA';
        if (currentCity === 'new_orleans') return 'CBD_FRENCH_QUARTER';
        if (currentCity === 'norfolk') return 'DOWNTOWN_WATERFRONT';
        if (currentCity === 'detroit') return 'DOWNTOWN_MIDTOWN_CORKTOWN';
        if (currentCity === 'austin') return 'DOWNTOWN_CAPITOL';
        if (currentCity === 'philadelphia') return 'CENTER_CITY_RITTENHOUSE';
        if (currentCity === 'washington_dc') return 'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT';
        return 'Manhattan';
      }
      const cfg = CITY_CONFIGS[currentCity];
      if (cfg && cfg.metroBbox) {
        const b = cfg.metroBbox;
        if (lat >= b.min_lat && lat <= b.max_lat && lng >= b.min_lng && lng <= b.max_lng) {
          const viaSubmarket = resolveDivisionByNearestSubmarket(lat, lng);
          if (viaSubmarket) return viaSubmarket;
        }
      }
      if (currentCity === 'seattle') {
        // SEATTLE_METRO_BBOX guard: min_lat 47.28 max_lat 47.78 min_lng -122.43 max_lng -122.00
        if (lat >= 47.28 && lat <= 47.78 && lng >= -122.43 && lng <= -122.00) {
          if (lat >= 47.645 && lat <= 47.745 && lng >= -122.425 && lng <= -122.280) return 'NORTH_KING';
          if (lat >= 47.500 && lat <= 47.770 && lng >= -122.260 && lng <= -122.010) return 'EASTSIDE';
          if (lat >= 47.290 && lat <= 47.590 && lng >= -122.420 && lng <= -122.150) return 'SOUTH_KING';
        }
        return 'SEATTLE_CORE';
      }
      if (currentCity === 'los_angeles') {
        // LA_METRO_BBOX guard: min_lat 33.7 max_lat 34.34 min_lng -118.63 max_lng -117.95
        if (lat >= 33.7 && lat <= 34.34 && lng >= -118.63 && lng <= -117.95) {
          if (lat >= 34.14 && lat <= 34.34 && lng >= -118.63 && lng <= -118.28) return 'SAN_FERNANDO_VALLEY';
          if (lat >= 33.98 && lat <= 34.12 && lng >= -118.56 && lng <= -118.35) return 'WESTSIDE';
          if (lat >= 33.7 && lat <= 33.9 && lng >= -118.45 && lng <= -118.1) return 'HARBOR_SOUTH_BAY';
          if (lat >= 33.9 && lat <= 34.03 && lng >= -118.38 && lng <= -118.2) return 'SOUTH_LA';
          if (lat >= 34.03 && lat <= 34.14 && lng >= -118.35 && lng <= -118.2) return 'CENTRAL_LA';
          if (lat >= 34.03 && lat <= 34.2 && lng >= -118.28 && lng <= -117.95) return 'EASTSIDE_SGV';
          return 'CENTRAL_LA';
        }
      }
      if (currentCity === 'new_orleans') {
        // NEW_ORLEANS_METRO_BBOX guard: min_lat 29.82 max_lat 30.16 min_lng -90.30 max_lng -89.62
        if (lat >= 29.82 && lat <= 30.16 && lng >= -90.30 && lng <= -89.62) {
          if (lat >= 29.93 && lat <= 30.00 && lng >= -90.10 && lng <= -90.02) return 'CBD_FRENCH_QUARTER';
          if (lat >= 29.95 && lat <= 30.00 && lng >= -90.05 && lng <= -89.98) return 'BYWATER_MARIGNY';
          if (lat >= 29.90 && lat <= 30.00 && lng >= -90.15 && lng <= -90.05) return 'UPTOWN_CARROLLTON';
          if (lat >= 29.96 && lat <= 30.04 && lng >= -90.13 && lng <= -90.05) return 'MID_CITY';
          if (lat >= 29.98 && lat <= 30.06 && lng >= -90.15 && lng <= -90.04) return 'LAKEVIEW_GENTILLY';
          if (lat >= 29.86 && lat <= 29.98 && lng >= -90.08 && lng <= -89.95) return 'WEST_BANK_ALGIERS';
          if (lat >= 29.99 && lat <= 30.10 && lng >= -90.08 && lng <= -89.62) return 'NEW_ORLEANS_EAST';
          if (lat >= 29.87 && lat <= 30.05 && lng >= -90.30 && lng <= -90.10) return 'JEFFERSON_METAIRIE_KENNER';
          if (lat >= 29.82 && lat <= 29.95 && lng >= -90.10 && lng <= -89.80) return 'ST_BERNARD_CHALMETTE';
          return 'CBD_FRENCH_QUARTER';
        }
      }
      if (currentCity === 'norfolk') {
        // NORFOLK_METRO_BBOX guard: min_lat 36.83 max_lat 37.04 min_lng -76.35 max_lng -76.17
        if (lat >= 36.83 && lat <= 37.04 && lng >= -76.35 && lng <= -76.17) {
          if (lat >= 36.915 && lng <= -76.24) return 'OCEAN_VIEW';
          if (lat >= 36.87 && lat <= 36.92 && lng >= -76.27 && lng <= -76.205) return 'CENTRAL_MILITARY_CIRCLE';
          if (lat <= 36.88 && lng >= -76.30 && lng <= -76.23) return 'SOUTH_NORFOLK_BERKLEY';
          if (lat >= 36.84 && lat <= 36.90 && lng >= -76.315 && lng <= -76.28) return 'DOWNTOWN_WATERFRONT';
          if (lat >= 36.85 && lat <= 36.905 && lng >= -76.31 && lng <= -76.255) return 'GHENT_WESTBURG';
          return 'DOWNTOWN_WATERFRONT';
        }
      }
      if (currentCity === 'detroit') {
        // DETROIT_METRO_BBOX guard: min_lat 42.25 max_lat 42.49 min_lng -83.35 max_lng -82.88
        if (lat >= 42.25 && lat <= 42.49 && lng >= -83.35 && lng <= -82.88) {
          if (lat >= 42.38 && lng <= -83.15) return 'WEST_SIDE_GRAND_RIVER';
          if (lat >= 42.365 && lng >= -83.12 && lng <= -83.06) return 'NORTH_END_HIGHLAND_PARK';
          if (lat <= 42.33 && lng >= -83.15 && lng <= -83.08) return 'SOUTHWEST_MEXICANTOWN';
          if (lat >= 42.35 && lng >= -82.95) return 'EAST_ENGLISH_VILLAGE_MORNINGSIDE';
          if (lat >= 42.325 && lng >= -83.03) return 'EAST_SIDE_JEFFERSON';
          if (lat >= 42.31 && lat <= 42.365 && lng >= -83.10 && lng <= -83.02) return 'DOWNTOWN_MIDTOWN_CORKTOWN';
          return 'DOWNTOWN_MIDTOWN_CORKTOWN';
        }
      }
      if (currentCity === 'austin') {
        // AUSTIN_METRO_BBOX guard: min_lat 30.10 max_lat 30.62 min_lng -98.05 max_lng -97.52
        if (lat >= 30.10 && lat <= 30.62 && lng >= -98.05 && lng <= -97.52) {
          if (lat >= 30.305 && lat <= 30.48 && lng >= -97.76 && lng <= -97.655) return 'NORTH_AUSTIN_DOMAIN';
          if (lat >= 30.39 && lng >= -97.66) return 'PFLUGERVILLE_ROUND_ROCK_EDGE';
          if (lat >= 30.25 && lng <= -97.755 && lat <= 30.40) return 'WEST_AUSTIN_HILLS';
          if (lat <= 30.25 && lng <= -97.72) return 'SOUTH_AUSTIN_SOCO';
          if (lat >= 30.25 && lat <= 30.31 && lng >= -97.72 && lng <= -97.66) return 'EAST_AUSTIN_MUELLER';
          if (lat >= 30.25 && lat <= 30.29 && lng >= -97.765 && lng <= -97.725) return 'DOWNTOWN_CAPITOL';
          return 'DOWNTOWN_CAPITOL';
        }
      }
      if (currentCity === 'philadelphia') {
        // PHILADELPHIA_METRO_BBOX guard: min_lat 39.87 max_lat 40.14 min_lng -75.28 max_lng -74.95
        if (lat >= 39.87 && lat <= 40.14 && lng >= -75.28 && lng <= -74.95) {
          if (lat >= 40.005 && lng >= -75.115) return 'NORTHEAST_ROOSEVELT_BLVD';
          if (lat >= 40.032 && lng <= -75.16) return 'GERMANTOWN_MT_AIRY';
          if (lat >= 39.96 && lat <= 40.01 && lng >= -75.15 && lng <= -75.105) return 'RIVER_WARDS_KENSINGTON';
          if (lat >= 39.963 && lng <= -75.235) return 'NORTH_PHILLY_TEMPLE';
          if (lat >= 39.933 && lat <= 39.972 && lng <= -75.188) return 'WEST_PHILLY_UNIVERSITY_CITY';
          if (lat <= 39.952 && lng >= -75.20) return 'SOUTH_PHILLY_PASSYUNK';
          if (lat >= 39.946 && lng <= -75.152) return 'OLD_CITY_NORTHERN_LIBERTIES';
          if (lat >= 39.938 && lng <= -75.195) return 'CENTER_CITY_RITTENHOUSE';
          return 'CENTER_CITY_RITTENHOUSE';
        }
      }
      if (currentCity === 'washington_dc') {
        // DC_METRO_BBOX guard: min_lat 38.79 max_lat 38.995 min_lng -77.12 max_lng -76.909
        if (lat >= 38.79 && lat <= 38.995 && lng >= -77.12 && lng <= -76.909) {
          if (lat <= 38.884 && lng >= -76.986) return 'HILL_EAST_FAIRLINTON';
          if (lat <= 38.878 && lng >= -76.988) return 'ANACOSTIA_EAST_OF_THE_RIVER';
          if (lat >= 38.926 && lng <= -77.00 && lng >= -77.04) return 'COLUMBIA_HEIGHTS_PETWORTH';
          if (lat >= 38.926 && lng >= -77.00) return 'BROOKLAND_RHODE_ISLAND_AVE';
          if (lat >= 38.90 && lng <= -77.045) return 'GEORGETOWN_FOGGY_BOTTOM';
          if (lat >= 38.90 && lng <= -77.022) return 'DUPONT_KALORAMA_UPTOWN';
          if (lat <= 38.90 && lng >= -76.995 && lng <= -76.972) return 'CAPITOL_HILL_EAST_END';
          return 'DOWNTOWN_NOMA_CAPITOL_RIVERFRONT';
        }
      }
      if (lat >= 37.0 && lat <= 38.5 && lng >= -123.0 && lng <= -121.5) {
        if (lat >= 37.835 && lng <= -122.35) return 'MARIN_NORTH_BAY';
        if (lat <= 37.460 && lng >= -122.20) return 'SILICON_VALLEY_SOUTH_BAY';
        if (lat >= 37.420 && lat <= 37.700 && lng >= -122.480 && lng <= -122.180) return 'PENINSULA';
        if (lng >= -122.350) return 'EAST_BAY';
        return 'SAN_FRANCISCO_CORE';
      }
      if (lat >= 40.785 && lat <= 40.915 && lng >= -73.935 && lng <= -73.765) return 'Bronx';
      if (lat >= 40.495 && lat <= 40.650 && lng >= -74.255 && lng <= -74.050) return 'Staten Island';
      if (lat >= 40.540 && lat <= 40.800 && lng >= -73.960 && lng <= -73.700 && lng > -73.930) return 'Queens';
      if (lat >= 40.570 && lat <= 40.740 && lng >= -74.050 && lng <= -73.830) return 'Brooklyn';
      return 'Manhattan';
    }
  </script>
</body>
</html>
"""
    return html.replace("__FAVICON_LINK__", favicon_link)
