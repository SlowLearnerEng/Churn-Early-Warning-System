/* ============================================
   Churn Intelligence Platform — Core Engine
   (Rebuilt for real IndiaMART data)
   ============================================ */

let DATA = null;
let currentSortCol = 'priority_score';
let currentSortDir = -1;
let chartInstances = {};

const BAND_COLORS = { low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' };
const BAND_ORDER = ['critical', 'high', 'medium', 'low'];

function formatINR(val) {
    if (val >= 10000000) return '₹' + (val / 10000000).toFixed(1) + ' Cr';
    if (val >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
    if (val >= 1000) return '₹' + (val / 1000).toFixed(1) + 'K';
    return '₹' + Math.round(val);
}

function bandChip(band) { return `<span class="chip chip-${band}">${band}</span>`; }
function statusChip(st) { return `<span class="chip chip-status ${st||'open'}">${st||'—'}</span>`; }
function actionLabel(c) { return c ? c.replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase()) : '—'; }

function destroyChart(id) { if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; } }
function makeChart(id, cfg) { destroyChart(id); const c=document.getElementById(id); if(!c) return null; chartInstances[id]=new Chart(c.getContext('2d'),cfg); return chartInstances[id]; }

/* ---- Tab Navigation ---- */
function initTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel-' + tab)?.classList.add('active');
        });
    });
}

/* ---- KPI Cards ---- */
function renderKPIs() {
    const ex = DATA.executive;
    document.getElementById('kpi-grid').innerHTML = [
        { label: 'Revenue at Risk', value: formatINR(ex.total_revenue_at_risk), sub: `${ex.total_sellers} sellers scored`, cls: 'danger' },
        { label: 'High Risk Sellers', value: ex.high_count, sub: `${ex.band_counts.medium || 0} medium risk`, cls: 'danger' },
        { label: 'Total Alerts', value: ex.total_alerts, sub: 'Requiring action', cls: 'warning' },
        { label: 'Upcoming Renewals', value: ex.renewal_funnel.upcoming, sub: `${ex.renewal_funnel.high_risk} high-risk`, cls: 'accent' },
        { label: 'Actioned', value: ex.renewal_funnel.actioned, sub: 'Interventions scheduled', cls: 'success' },
    ].map(k => `<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');
}

/* ---- Executive Charts ---- */
function renderDonut() {
    const bc = DATA.executive.band_counts;
    const labels = BAND_ORDER.filter(b => bc[b]);
    makeChart('chart-risk-donut', {
        type: 'doughnut',
        data: { labels: labels.map(l => l.charAt(0).toUpperCase()+l.slice(1)),
                datasets: [{ data: labels.map(b => bc[b]||0), backgroundColor: labels.map(b => BAND_COLORS[b]), borderWidth: 0, borderRadius: 4 }] },
        options: { cutout: '68%', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#8b949e', font: { family: 'Inter', size: 11 }, padding: 14, usePointStyle: true, pointStyleWidth: 8 }}} }
    });
}

function renderFunnel() {
    const f = DATA.executive.renewal_funnel;
    makeChart('chart-renewal-funnel', {
        type: 'bar', data: { labels: ['Upcoming','High Risk','Actioned'],
            datasets: [{ data: [f.upcoming, f.high_risk, f.actioned], backgroundColor: ['#6366f1','#f97316','#10b981'], borderRadius: 6, borderSkipped: false }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font:{family:'Inter'}}}, y: { grid: { display: false }, ticks: { color: '#8b949e', font:{family:'Inter',weight:600}}} },
            plugins: { legend: { display: false }} }
    });
}

function renderTopReasons() {
    const reasons = DATA.executive.top_reasons.slice(0, 7);
    makeChart('chart-top-reasons', {
        type: 'bar', data: { labels: reasons.map(r => r[0].replace(/_/g,' ')),
            datasets: [{ data: reasons.map(r => r[1]), backgroundColor: '#6366f1', borderRadius: 4, borderSkipped: false }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font:{family:'Inter'}}}, y: { grid: { display: false }, ticks: { color: '#8b949e', font:{family:'Inter',size:10}}} },
            plugins: { legend: { display: false }} }
    });
}

function renderHeatmap() {
    const hm = DATA.executive.heatmap;
    const packages = Object.keys(hm).sort();
    const allStates = new Set();
    packages.forEach(p => Object.keys(hm[p]).forEach(s => allStates.add(s)));
    const states = [...allStates].sort().slice(0, 12); // top 12

    let html = '<table class="heatmap-table"><thead><tr><th></th>';
    states.forEach(s => { html += `<th>${s}</th>`; });
    html += '</tr></thead><tbody>';
    packages.forEach(pkg => {
        html += `<tr><th>${pkg}</th>`;
        states.forEach(state => {
            const cell = (hm[pkg]||{})[state];
            if (cell) {
                const risk = cell.avg_risk;
                const bg = risk >= 50 ? 'rgba(239,68,68,0.25)' : risk >= 35 ? 'rgba(245,158,11,0.25)' : 'rgba(16,185,129,0.15)';
                const color = risk >= 50 ? '#ef4444' : risk >= 35 ? '#f59e0b' : '#10b981';
                html += `<td class="heatmap-cell" style="background:${bg};color:${color}" title="${pkg} × ${state}: ${cell.count} sellers, avg risk ${risk}">${risk}</td>`;
            } else { html += '<td class="heatmap-cell" style="opacity:0.2">—</td>'; }
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('heatmap-container').innerHTML = html;
}

/* ---- Watchlist ---- */
function getFilteredSellers() {
    const band = document.getElementById('filter-band').value;
    const pkg = document.getElementById('filter-category').value;
    const city = document.getElementById('filter-city').value;
    const q = document.getElementById('filter-search').value.toLowerCase();

    let list = DATA.sellers.filter(s => s.risk_band !== 'low');
    if (band) list = list.filter(s => s.risk_band === band);
    if (pkg) list = list.filter(s => s.package === pkg);
    if (city) list = list.filter(s => s.city === city);
    if (q) list = list.filter(s => s.seller_id.toLowerCase().includes(q) || (s.company_name||'').toLowerCase().includes(q) || (s.seller_name||'').toLowerCase().includes(q));

    list.sort((a,b) => {
        const av = a[currentSortCol], bv = b[currentSortCol];
        if (typeof av === 'number') return (av - bv) * currentSortDir;
        return String(av).localeCompare(String(bv)) * currentSortDir;
    });
    return list;
}

function renderWatchlist() {
    const list = getFilteredSellers();
    document.getElementById('filter-count').textContent = `${list.length} sellers`;
    document.getElementById('watchlist-body').innerHTML = list.slice(0, 100).map(s => {
        const reasons = (s.reason_codes||[]).slice(0,2).map(r => `<span class="chip chip-reason">${(r.code||'').replace(/_/g,' ')}</span>`).join('');
        return `<tr>
            <td><strong>${s.priority_score.toFixed(1)}</strong></td>
            <td><strong>${s.seller_id}</strong><br><span style="color:var(--text-secondary);font-size:0.74rem">${s.company_name||s.seller_name}</span></td>
            <td>${s.package}</td>
            <td>${s.city}</td>
            <td>${bandChip(s.risk_band)} <span style="font-size:0.76rem;color:var(--text-secondary)">${s.risk_score.toFixed(0)}</span></td>
            <td>${s.revenue_at_risk ? formatINR(s.revenue_at_risk) : '—'}</td>
            <td>${reasons || '—'}</td>
            <td><span class="chip chip-action">${actionLabel(s.recommended_action)}</span></td>
            <td>${statusChip(s.action_status)}</td>
            <td><button class="btn-view" onclick="openSeller360('${s.seller_id}')">View</button></td>
        </tr>`;
    }).join('');
}

function initWatchlistFilters() {
    // Package filter (replaces category)
    const pkgs = [...new Set(DATA.sellers.map(s => s.package))].sort();
    const catSel = document.getElementById('filter-category');
    catSel.innerHTML = '<option value="">All Packages</option>';
    pkgs.forEach(p => { const o=document.createElement('option'); o.value=p; o.textContent=p; catSel.appendChild(o); });
    // City filter
    const cities = [...new Set(DATA.sellers.map(s => s.city))].sort();
    const citySel = document.getElementById('filter-city');
    cities.forEach(c => { const o=document.createElement('option'); o.value=c; o.textContent=c; citySel.appendChild(o); });

    ['filter-band','filter-category','filter-city','filter-search'].forEach(id => {
        document.getElementById(id).addEventListener(id==='filter-search'?'input':'change', renderWatchlist);
    });

    document.querySelectorAll('#watchlist-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (currentSortCol===col) currentSortDir *= -1;
            else { currentSortCol=col; currentSortDir=-1; }
            renderWatchlist();
        });
    });
}
