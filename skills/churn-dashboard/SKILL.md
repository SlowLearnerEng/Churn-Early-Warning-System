---
name: churn-dashboard
description: Build, extend, debug, and operate a real-time seller churn intelligence dashboard using vanilla JavaScript and Chart.js. Use when an agent needs to add a new dashboard page or chart, fix a rendering bug, update the data pipeline export, modify the seller 360 profile view, change KPI cards, or wire up new data fields in a B2B marketplace analytics dashboard.
compatibility: Requires Python 3 http.server (or equivalent) to serve the dashboard. Dashboard data must be regenerated via the export pipeline before serving.
metadata:
  author: IndiaMART
  version: "1.0"
---

# Churn Dashboard

A vanilla JS + Chart.js dark-theme single-page application for monitoring B2B seller churn risk, renewal status, cohort patterns, and retention interventions.

## File Map

| File | Role |
| --- | --- |
| `dashboard/index.html` | Static HTML; all tab panels declared here; Chart.js 4.4.7 via CDN |
| `dashboard/app.js` | Data load, tab navigation, KPI cards, watchlist table, executive charts |
| `dashboard/views.js` | Seller 360 picker, cohorts, interventions, upsell signals, activation health |
| `dashboard/styles.css` | CSS custom properties dark theme |
| `dashboard/data/dashboard_data.json` | Runtime data payload; loaded via `fetch()` on startup |

## Regenerate Data

Run the full pipeline before serving:

```bash
python scripts/export_excel_to_csv.py
python scripts/build_features.py
python scripts/score_real_data.py
python scripts/export_real_dashboard.py
```

Serve:

```bash
cd dashboard && python -m http.server 8765
# Open http://localhost:8765
```

## Tab Layout

| Tab | Panel ID | Primary Renderers | Key Data |
| --- | --- | --- | --- |
| Executive | `panel-executive` | `renderKPIs`, `renderDonut`, `renderFunnel`, `renderTopReasons` | `DATA.executive` |
| Watchlist | `panel-watchlist` | `renderWatchlist`, `initWatchlistFilters` | `DATA.sellers` (non-low band) |
| Seller 360 | `panel-seller360` | `initSellerPicker`, `openSeller360` | `DATA.sellers` (individual) |
| Renewal Risk | `panel-renewal` | `renderRenewalRisk` | `DATA.sellers` |
| Cohorts | `panel-cohorts` | `renderCohorts`, `initCohortTabs` | `DATA.cohorts` |
| Interventions | `panel-interventions` | `renderInterventions`, `renderInterventionROI` | `DATA.sellers` |
| Upsell Signals | `panel-upsell` | `renderUpsellSignals` | `DATA.sellers` |
| Activation | `panel-activation` | `renderActivation` | `DATA.sellers` |

## Critical Design Patterns

### Lazy Rendering (required)
Charts rendered inside `display:none` panels draw at 0×0 — always blank. Each tab renders the first time the user activates it:

```javascript
// In initTabs() — renderers map in app.js
const renderers = {
    watchlist:     () => { initWatchlistFilters(); renderWatchlist(); },
    seller360:     () => initSellerPicker(),
    renewal:       () => renderRenewalRisk(),
    // ...
};
// On tab click: if (!rendered.has(tab)) { renderers[tab](); rendered.add(tab); }
```

### Chart Lifecycle
Always destroy before recreating:

```javascript
function makeChart(id, cfg) {
    destroyChart(id);  // prevents "Canvas already in use" error
    const c = document.getElementById(id);
    if (!c) return null;
    chartInstances[id] = new Chart(c.getContext('2d'), cfg);
    return chartInstances[id];
}
```

### CSS Custom Properties

```css
--bg-base, --bg-card, --bg-card-hover, --bg-surface
--accent: #6366f1
--critical: #ef4444
--high:     #f59e0b
--medium:   #3b82f6
--low:      #10b981
--text-primary, --text-secondary, --text-muted
--border, --radius, --radius-lg, --radius-sm
--font: 'Inter', sans-serif
```

### INR Formatting

```javascript
formatINR(val)  // → ₹1.2 Cr / ₹45.3 L / ₹12.4K / ₹890
```

### Seeded Weekly Data
Use `seededRand(hashStr(seller_id))` LCG PRNG for consistent per-seller weekly sparklines — same output on every page reload.

## Seller Object Shape

```javascript
DATA.sellers[i] = {
  seller_id, seller_name, company_name, city, state,
  package,               // "STAR" | "PRIME" | "STAR-MAXI" | "PRIME-MAXI"
  member_since_years,    // integer
  subscription_end_date, // "YYYY-MM-DD"
  days_to_renewal,       // integer; negative = expired
  risk_score,            // 0–100
  risk_band,             // "low" | "medium" | "high" | "critical"
  confidence,            // 0–1
  reason_codes,          // [{code, severity, evidence}]
  recommended_action, action_code, action_status,
  revenue_at_risk, priority_score,
  call_pickup_pct_30d, total_enquiries_30d, overall_rating,
  negative_intent_pct, cancellation_rate, untouched_pct,
  health_trend,          // [{period:"Oct-2025", buyleads, enquiries, call_pickup_pct, lms_active_days, replies, callbacks}]
  calls, reviews, tickets, catalogue
}
```

## Adding a New Tab

1. Add `<button class="nav-btn" data-tab="my-tab">` to the sidebar in `index.html`.
2. Add `<section class="tab-panel" id="panel-my-tab">` with inner containers.
3. Add `'my-tab': () => renderMyTab()` to the `renderers` map in `initTabs()` inside `app.js`.
4. Write `function renderMyTab()` in `views.js`.
5. Add CSS classes to `styles.css`.

## Adding a New Field to Dashboard Data

1. Add computation in `scripts/export_real_dashboard.py` under the seller loop.
2. Run `python scripts/export_real_dashboard.py` to regenerate `dashboard_data.json`.
3. Reference the field in your render function as `s.my_new_field`.
